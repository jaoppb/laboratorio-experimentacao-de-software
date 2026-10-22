"""Final regeneration of the 330-repository dataset (Issue #56).

The sample is FROZEN: the selection is not re-run and `funil.csv` is untouched.
This command recomputes every METRIC column of exactly the repositories in
`dados/repositorios.csv`, in the same order, with the current code paths
(end-of-day window, recursive split of workflow runs, full commit messages,
null rules, CFR (b) over C1 and over C2, all C2/C3 columns), through the same
functions the pipeline uses (`compute_metric_columns`). The selection-time
metadata columns (stars, language, contributors, age, ...) are copied from the
committed dataset and never recomputed.

Execution (from `lab03/`, token in `GITHUB_TOKEN`/`GITHUB_TOKENS` or `.env`):
    uv run python -m pipeline.regenerar --config config.yaml [--limit N] [--resume] [--workers K]

Working state lives in `dados/.regenerar/` (git-ignored):
- `baseline.parquet|csv`: copy of the dataset before the regeneration (the
  "old" side of the comparison and the source of the repository list);
- `checkpoint.jsonl`: one line per finished repository (resume);
- `runs/`: regenerated workflow runs, copied to `dados/runs/` at the end.

Only when ALL repositories are collected (no `--limit`, no failure) and the
invariants hold, the run publishes the result: writes `repositorios.parquet|csv`
with the full schema, replaces `dados/runs/<repo>.parquet`, removes the orphan
files of `dados/runs/` (`git rm` when tracked) and writes the comparison report
`docs/regeneracao_final.md`. The command is idempotent and resumable; a token
is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

from metricas.cfr_b import DEFAULT_HEURISTIC, HEURISTICS
from metricas.schemas import _parse_datetime, parse_window_end, window_length
from pipeline.git_clone import CLONE_FILTER, temporary_git_clone
from pipeline.git_phase import (
    CHILD_TIMEOUT_SECONDS,
    GitPhaseError,
    GitPhaseSpec,
    run_git_phase,
    run_git_phase_in_child,
)
from pipeline.http_client import GitHubClient
from pipeline.orchestrator import (
    compose_metric_columns,
    compute_run_columns,
    load_repositories_dataset,
    save_repositories_dataset,
)
from pipeline.regeneracao_relatorio import (
    METADATA_COLUMNS,
    SCHEMA_COLUMNS,
    check_invariants,
    check_written_files,
    compare_datasets,
    render_report,
)
from pipeline.releases import fetch_releases, filter_window
from pipeline.workflow_runs import (
    collect_workflow_runs,
    _is_valid_run,
    load_runs_from_parquet,
    reconcile_workflow_runs,
    save_runs_to_parquet,
)
from metricas.stability import calculate_cfr_a, calculate_recovery_time

logger = logging.getLogger(__name__)

STATE_DIR_NAME = ".regenerar"
RUNS_MODE_FULL = "completo"
RUNS_MODE_RECONCILE = "reconciliar"
RUNS_MODES = (RUNS_MODE_FULL, RUNS_MODE_RECONCILE)
# A repository with this many previous runs / window releases is "heavy": at most one
# heavy repository is processed at a time, so the peak memory stays bounded.
HEAVY_RUNS = 20_000
HEAVY_RELEASES = 500
# Tags are deploy units too (C3): tag-heavy repositories (CI tags) have huge commit ranges.
HEAVY_TAGS = 1_000
# New repositories are not started while the system has less available RAM than this (MiB).
MIN_AVAILABLE_MB = 3072
MEMORY_POLL_SECONDS = 10
STATUS_EVERY = 25  # repositories between two status.json writes
HEARTBEAT_SECONDS = 120
DEFAULT_REPORT = "docs/regeneracao_final.md"

_TOKEN_RE = re.compile(
    r"(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._\-]{20,})"
)


def redact(text: str) -> str:
    """Remove anything that looks like a GitHub token from a message."""
    return _TOKEN_RE.sub("***", text)


@dataclass
class RegenSettings:
    """Everything the regeneration reads from `config.yaml` (plus run options)."""

    window_start: datetime
    window_end: datetime
    window_weeks: float
    heuristic: str
    dados_dir: Path
    cache_dir: Path
    git_cache_dir: Path
    expected_rows: int | None
    min_releases: int
    min_workflow_runs: int
    cleanup_clones: bool = False
    # repositories that, if they cannot be recollected (e.g. disabled upstream),
    # keep their previous metric values instead of blocking the regeneration
    keep_previous: frozenset[str] = frozenset()
    report_path: Path | None = Path(DEFAULT_REPORT)
    # How the workflow runs are obtained: "completo" (collector over the whole
    # window) or "reconciliar" (reuse the previous runs where the API agrees)
    runs_mode: str = RUNS_MODE_FULL
    previous_window_start: datetime | None = None
    previous_window_end: datetime | None = None
    status_path: Path | None = None
    bundle_dir: Path | None = None
    # Run the git/commit phase of each repository in a short-lived child process
    # (its memory goes back to the OS when it exits). The CLI turns it on by
    # default; `--sem-subprocesso` and the tests use the in-process phase.
    git_subprocess: bool = False
    child_timeout: float = CHILD_TIMEOUT_SECONDS

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        cleanup_clones: bool = False,
        report_path: Path | str | None = DEFAULT_REPORT,
        keep_previous: Sequence[str] = (),
        runs_mode: str = RUNS_MODE_FULL,
        status_path: Path | str | None = None,
        bundle_dir: Path | str | None = None,
        git_subprocess: bool = False,
    ) -> RegenSettings:
        janela = config.get("janela", {})
        dirs = config.get("diretorios", {})
        amostra = config.get("amostra", {})
        start = _parse_datetime(janela.get("inicio", "2025-10-01"))
        end = parse_window_end(janela.get("fim", "2026-09-30"))
        if start is None or end is None:
            raise ValueError("janela.inicio e janela.fim são obrigatórios")
        heuristic = config.get("cfr_b", {}).get("heuristica") or DEFAULT_HEURISTIC
        if heuristic not in HEURISTICS:
            raise ValueError(
                f"Unknown CFR (b) heuristic {heuristic!r}; available: {sorted(HEURISTICS)}"
            )
        if runs_mode not in RUNS_MODES:
            raise ValueError(f"runs_mode must be one of {RUNS_MODES}, got {runs_mode!r}")
        previous = config.get("regeneracao", {}).get("janela_anterior", {})
        previous_start = _parse_datetime(previous.get("inicio")) if previous else None
        # The previous upper bound is literal (a date-only value is 00:00:00Z)
        previous_end = _parse_datetime(previous.get("fim")) if previous else None
        return cls(
            window_start=start,
            window_end=end,
            window_weeks=window_length(start, end) / timedelta(weeks=1),
            heuristic=heuristic,
            dados_dir=Path(dirs.get("dados", "dados")),
            cache_dir=Path(dirs.get("cache", "cache")),
            git_cache_dir=Path(dirs.get("git_cache", "cache/git_repos")),
            expected_rows=amostra.get("tamanho_final"),
            min_releases=amostra.get("min_releases", 5),
            min_workflow_runs=amostra.get("min_workflow_runs", 50),
            cleanup_clones=cleanup_clones,
            keep_previous=frozenset(
                [*config.get("regeneracao", {}).get("manter_valores_anteriores", []), *keep_previous]
            ),
            report_path=Path(report_path) if report_path else None,
            runs_mode=runs_mode,
            previous_window_start=previous_start,
            previous_window_end=previous_end,
            status_path=Path(status_path) if status_path else None,
            bundle_dir=Path(bundle_dir) if bundle_dir else None,
            git_subprocess=git_subprocess,
        )

    @property
    def state_dir(self) -> Path:
        return self.dados_dir / STATE_DIR_NAME

    @property
    def baseline_parquet(self) -> Path:
        return self.state_dir / "baseline.parquet"

    @property
    def baseline_csv(self) -> Path:
        return self.state_dir / "baseline.csv"

    @property
    def checkpoint_path(self) -> Path:
        return self.state_dir / "checkpoint.jsonl"

    @property
    def baseline_runs_dir(self) -> Path:
        """Snapshot of `dados/runs/` before the regeneration (input of the reconciliation)."""
        return self.state_dir / "baseline_runs"

    @property
    def staged_runs_dir(self) -> Path:
        return self.state_dir / "runs"

    @property
    def runs_dir(self) -> Path:
        return self.dados_dir / "runs"

    @property
    def dataset_parquet(self) -> Path:
        return self.dados_dir / "repositorios.parquet"

    @property
    def dataset_csv(self) -> Path:
        return self.dados_dir / "repositorios.csv"

    def fingerprint(self) -> str:
        """Identity of the inputs of a collection; a checkpoint of another one is stale."""
        payload = {
            "window": [self.window_start.isoformat(), self.window_end.isoformat()],
            "heuristic": self.heuristic,
            "columns": list(SCHEMA_COLUMNS),
            "clone_filter": CLONE_FILTER,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]


def run_file_name(full_name: str) -> str:
    owner, repo = full_name.split("/", 1)
    return f"{owner}__{repo}.parquet"


# ---------------------------------------------------------------- checkpoint


def load_checkpoint(path: Path, fingerprint: str) -> dict[str, dict[str, Any]]:
    """Finished repositories of a previous run: `full_name -> {record, diagnostics}`.

    Lines of another fingerprint (different window/heuristic/schema) and a
    truncated last line (interrupted write) are ignored; later lines win.
    """
    done: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("fingerprint") != fingerprint:
                continue
            done[entry["record"]["full_name"]] = entry
    return done


def append_checkpoint(
    path: Path, fingerprint: str, record: dict[str, Any], diagnostics: dict[str, Any]
) -> None:
    """Append one finished repository (flushed so a crash loses at most the last line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "fingerprint": fingerprint,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "record": record,
        "diagnostics": diagnostics,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
        f.flush()


# ---------------------------------------------------------- per repository


async def acquire_runs(
    client: GitHubClient, old: dict[str, Any], settings: RegenSettings
) -> Any:
    """Workflow runs of the window, in the mode of the settings (same result type)."""
    full_name = old["full_name"]
    owner, repo = full_name.split("/", 1)
    if settings.runs_mode == RUNS_MODE_FULL:
        return await collect_workflow_runs(
            owner=owner,
            repo=repo,
            client=client,
            start_date=settings.window_start,
            end_date=settings.window_end,
            branch=old.get("default_branch"),
            save_to_parquet=False,
        )
    if settings.previous_window_end is None:
        raise ValueError("runs reconciliation needs regeneracao.janela_anterior.fim in the config")
    previous_file = settings.baseline_runs_dir / run_file_name(full_name)
    if not previous_file.is_file():
        raise FileNotFoundError(f"previous runs not found: {previous_file}")
    return await reconcile_workflow_runs(
        owner=owner,
        repo=repo,
        previous_runs=load_runs_from_parquet(previous_file),
        client=client,
        start_date=settings.window_start,
        previous_end_date=settings.previous_window_end,
        end_date=settings.window_end,
        branch=old.get("default_branch") or "main",
    )


async def regenerate_repository(
    client: GitHubClient,
    old: dict[str, Any],
    settings: RegenSettings,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute the metric columns of one frozen repository.

    Returns `(record, diagnostics)`. The metadata columns are copied from
    `old`; workflow runs go to the staging directory and the C1/C2/C3 units
    to the (git-ignored) `releases/`, `releases_c2/` and `tags/`.
    """
    full_name = old["full_name"]
    owner, repo = full_name.split("/", 1)

    releases = await fetch_releases(
        client=client,
        owner=owner,
        repo=repo,
        window_start=settings.window_start,
        use_graphql=True,
    )
    window_releases = filter_window(
        releases=releases,
        window_start=settings.window_start,
        window_end=settings.window_end,
    )

    runs_result = await acquire_runs(client, old, settings)

    # The clone stays in the parent (its 403/429 fallback uses the token pool); the
    # commit phase reads it from a child process (or in-process) and returns only
    # small figures. The child writes `releases/`, `releases_c2/`, `tags/`, `commits/`.
    spec_args = dict(
        owner=owner,
        repo=repo,
        dados_dir=settings.dados_dir,
        releases=releases,
        window_start=settings.window_start,
        window_end=settings.window_end,
        window_weeks=settings.window_weeks,
        heuristic=settings.heuristic,
    )
    async with temporary_git_clone(
        owner=owner,
        repo=repo,
        cache_dir=settings.git_cache_dir,
        auto_cleanup=settings.cleanup_clones,
        token_pool=client.token_pool,
    ) as git_dir:
        spec = GitPhaseSpec.build(git_dir=git_dir, **spec_args)  # type: ignore[arg-type]
        if settings.git_subprocess:
            git_result = await run_git_phase_in_child(spec, timeout=settings.child_timeout)
        else:
            git_result = await run_git_phase(spec)

    commit_columns = git_result["columns"]
    run_columns = compute_run_columns(
        releases=releases,
        window_releases=window_releases,
        runs=runs_result.runs,
        valid_runs_count=runs_result.valid_runs_count,
        lead_time_a_hours=commit_columns["lead_time_a_hours"],
        lead_time_b_hours=commit_columns["lead_time_b_hours"],
        window_start=settings.window_start,
        window_end=settings.window_end,
        window_weeks=settings.window_weeks,
    )
    metrics = compose_metric_columns(run_columns, commit_columns)
    record = {col: old.get(col) for col in METADATA_COLUMNS}
    record.update(metrics)

    # Stage the runs only after everything was computed
    save_runs_to_parquet(
        runs_result.runs,
        owner=owner,
        repo=repo,
        output_path=settings.staged_runs_dir / run_file_name(full_name),
    )

    diagnostics: dict[str, Any] = {
        "api_requests": runs_result.api_requests,
        "unsplittable_intervals": len(runs_result.unsplittable_intervals),
        "runs_mode": settings.runs_mode,
    }
    if settings.git_subprocess:
        # peak of the child that held the commits (the parent's own peak stays small)
        diagnostics["peak_rss_mb"] = git_result.get("peak_rss_mb")
    if settings.runs_mode == RUNS_MODE_RECONCILE:
        actions = Counter(e["action"] for e in runs_result.reconciliation)
        diagnostics["reconciled"] = dict(actions)
        diagnostics["refetched_intervals"] = [
            {k: e[k] for k in ("start", "end", "previous_count", "api_count", "fetched_count")}
            for e in runs_result.reconciliation
            if e["action"] == "refetched"
        ]
    return record, diagnostics


def keep_previous_values(
    settings: RegenSettings, old: dict[str, Any], reason: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Record of a repository that cannot be recollected: its previous values, unchanged.

    The previous `runs/` file is staged so the published `runs/` keeps one file
    per repository. Columns that did not exist before stay null.
    """
    previous_runs = settings.baseline_runs_dir / run_file_name(old["full_name"])
    if not previous_runs.is_file():
        previous_runs = settings.runs_dir / run_file_name(old["full_name"])
    if not previous_runs.is_file():
        raise FileNotFoundError(f"{previous_runs} not found; nothing to keep for {old['full_name']}")
    _copy_atomic(previous_runs, settings.staged_runs_dir / previous_runs.name)
    record = {col: old.get(col) for col in SCHEMA_COLUMNS}
    return record, {"kept_previous": reason, "unsplittable_intervals": 0, "api_requests": 0}


# ------------------------------------------------------------------ the run


@dataclass
class RegenSummary:
    """Outcome of one invocation."""

    total: int = 0
    scope: int = 0
    reused: int = 0
    collected: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    finalized: bool = False
    problems: list[str] = field(default_factory=list)
    removed_orphans: list[str] = field(default_factory=list)
    kept: dict[str, str] = field(default_factory=dict)
    bundle: Path | None = None

    @property
    def ok(self) -> bool:
        return not self.failed and not self.problems


class RegenerationError(Exception):
    """Unusable state (for example, a leftover checkpoint without --resume)."""


def prepare_baseline(settings: RegenSettings) -> list[dict[str, Any]]:
    """Snapshot the dataset before the regeneration (once) and return its records."""
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    if not settings.baseline_parquet.is_file():
        if not settings.dataset_parquet.is_file():
            raise FileNotFoundError(f"Dataset not found: {settings.dataset_parquet}")
        shutil.copy2(settings.dataset_parquet, settings.baseline_parquet)
        if settings.dataset_csv.is_file():
            shutil.copy2(settings.dataset_csv, settings.baseline_csv)
    if not settings.baseline_runs_dir.is_dir() and settings.runs_dir.is_dir():
        # Snapshot once, before anything is published (copy to a temp name, then rename)
        tmp = settings.baseline_runs_dir.with_name("baseline_runs.tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(settings.runs_dir, tmp)
        tmp.replace(settings.baseline_runs_dir)
    records = load_repositories_dataset(settings.baseline_parquet)
    if not records:
        raise FileNotFoundError(f"Baseline empty or unreadable: {settings.baseline_parquet}")
    return records


def reset_state(settings: RegenSettings) -> None:
    """Forget the progress of a previous run (checkpoint and staged runs); keep the baseline."""
    settings.checkpoint_path.unlink(missing_ok=True)
    if settings.staged_runs_dir.is_dir():
        shutil.rmtree(settings.staged_runs_dir)


def read_memory() -> dict[str, int | None]:
    """Memory figures in MiB from /proc (Linux); every value is None elsewhere.

    `rss`/`peak_rss` are this process's resident / peak resident set, `available` is the
    system's MemAvailable.
    """
    out: dict[str, int | None] = {"rss": None, "peak_rss": None, "available": None}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                out["rss"] = int(line.split()[1]) // 1024
            elif line.startswith("VmHWM:"):
                out["peak_rss"] = int(line.split()[1]) // 1024
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                out["available"] = int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return out


async def wait_for_memory(
    min_available_mb: int = MIN_AVAILABLE_MB,
    poll_seconds: float = MEMORY_POLL_SECONDS,
    reader: Any = read_memory,
) -> float:
    """Block while the system's available RAM is below `min_available_mb`.

    Other people use the machine: a new repository is not started while memory is short.
    Returns the seconds waited (0 when memory is fine or unknown).
    """
    waited = 0.0
    while True:
        available = reader()["available"]
        if available is None or available >= min_available_mb:
            return waited
        if waited == 0.0:
            logger.warning(
                "Only %d MiB of RAM available (< %d): pausing new repositories", available, min_available_mb
            )
        await asyncio.sleep(poll_seconds)
        waited += poll_seconds


def is_heavy(old: dict[str, Any]) -> bool:
    """Repositories with very many runs, releases or tags (they get a worker of their own)."""
    return (
        (old.get("total_workflow_runs") or 0) >= HEAVY_RUNS
        or (old.get("releases_count_window") or 0) >= HEAVY_RELEASES
        or (old.get("tags_count_window") or 0) >= HEAVY_TAGS
    )


@dataclass
class RunStatus:
    """Machine-readable state of the run (`status.json`), for anyone reconnecting later."""

    path: Path | None
    total: int
    done: int
    mode: str
    started_at: float = field(default_factory=time.time)
    started_done: int = 0
    requests: int = 0
    in_flight: set[str] = field(default_factory=set)
    last_error: str | None = None
    failed: int = 0
    state: str = "running"
    # process peak RSS (MiB) observed when each repository finished (the largest few)
    peak_rss_by_repo: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.started_done = self.done

    def snapshot(self, client: Any = None) -> dict[str, Any]:
        elapsed = time.time() - self.started_at
        finished = self.done - self.started_done
        remaining = max(0, self.total - self.done)
        eta_seconds = None
        if finished > 0 and remaining:
            eta_seconds = round(elapsed / finished * remaining)
        quota: list[dict[str, Any]] = []
        pool = getattr(client, "token_pool", None)
        for tok in getattr(pool, "tokens", []) or []:  # never includes the token itself
            quota.append(
                {
                    "remaining": tok.remaining,
                    "reset_at": (
                        datetime.fromtimestamp(tok.reset_ts, timezone.utc).isoformat()
                        if tok.reset_ts
                        else None
                    ),
                    "disabled": tok.cooldown_until == float("inf"),
                }
            )
        return {
            # counts only, never the values: usable = not disabled (e.g. by a 401)
            "tokens_total": len(quota),
            "tokens_usable": sum(1 for q in quota if not q["disabled"]),
            "state": self.state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "runs_mode": self.mode,
            "done": self.done,
            "total": self.total,
            "failed_this_run": self.failed,
            "requests_this_run": self.requests,
            "quota": quota,
            "current": sorted(self.in_flight),
            "elapsed_seconds": round(elapsed),
            "eta_seconds": eta_seconds,
            "eta_at": (
                datetime.fromtimestamp(time.time() + eta_seconds, timezone.utc).isoformat()
                if eta_seconds is not None
                else None
            ),
            "last_error": self.last_error,
            "memory_mb": read_memory(),
            "peak_rss_mb_per_repo": self.peak_rss_by_repo,
        }

    def write(self, client: Any = None) -> None:
        """Atomically write `status.json` (no-op without a path; never raises)."""
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(
                json.dumps(self.snapshot(client), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError as exc:  # a full disk must not kill the collection
            logger.warning("Could not write status file: %s", exc)


async def collect_all(
    settings: RegenSettings,
    scope: Sequence[dict[str, Any]],
    done: dict[str, dict[str, Any]],
    client: GitHubClient,
    num_workers: int,
    summary: RegenSummary,
    status: RunStatus | None = None,
    min_available_mb: int = MIN_AVAILABLE_MB,
) -> None:
    """Collect the repositories of `scope` that are not in the checkpoint yet.

    Memory is bounded: each worker holds one repository at a time, only one *heavy*
    repository (see `is_heavy`) runs at once, new repositories wait while the system is
    short of RAM and the data of a repository is released (`gc`) as soon as it is done.
    """
    fingerprint = settings.fingerprint()
    pending = [r for r in scope if r["full_name"] not in done]
    heavy_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    light_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    for rec in pending:
        (heavy_queue if is_heavy(rec) else light_queue).put_nowait(rec)
    progress = {"n": 0}

    async def process(old: dict[str, Any]) -> None:
        name = old["full_name"]
        await wait_for_memory(min_available_mb)
        if status:
            status.in_flight.add(name)
        try:
            record, diagnostics = await regenerate_repository(client, old, settings)
        except Exception as exc:
            reason = redact(f"{type(exc).__name__}: {exc}")
            if status:
                status.in_flight.discard(name)
                status.last_error = f"{name}: {reason}"[:500]
                status.failed += 1
                status.write(client)
            if name not in settings.keep_previous:
                summary.failed[name] = reason
                logger.warning("Failed to regenerate %s: %s", name, reason)
                return
            logger.warning("%s could not be recollected, keeping previous values: %s", name, reason)
            try:
                record, diagnostics = keep_previous_values(settings, old, reason)
            except Exception as keep_exc:
                summary.failed[name] = redact(f"{reason}; {type(keep_exc).__name__}: {keep_exc}")
                return
        memory = read_memory()
        diagnostics.setdefault("peak_rss_mb", memory["peak_rss"])
        append_checkpoint(settings.checkpoint_path, fingerprint, record, diagnostics)
        done[name] = {"record": record, "diagnostics": diagnostics}
        summary.collected.append(name)
        progress["n"] += 1
        logger.info(
            "[%d/%d] %s regenerated (rss %s MiB, peak %s MiB)",
            progress["n"], len(pending), name, memory["rss"], diagnostics.get("peak_rss_mb"),
        )
        if status:
            status.in_flight.discard(name)
            status.done += 1
            status.requests += diagnostics.get("api_requests", 0)
            if diagnostics.get("peak_rss_mb") is not None:
                status.peak_rss_by_repo[name] = diagnostics["peak_rss_mb"]
                # keep the file small: only the five highest
                top = sorted(status.peak_rss_by_repo.items(), key=lambda kv: -kv[1])[:5]
                status.peak_rss_by_repo = dict(top)
            if progress["n"] % STATUS_EVERY == 0 or status.done >= status.total:
                status.write(client)
        gc.collect()  # release this repository's runs/commits before the next one

    async def heavy_worker() -> None:
        # The only worker that takes heavy repositories; then helps with the light ones.
        while not heavy_queue.empty():
            await process(heavy_queue.get_nowait())
        await light_worker()

    async def light_worker() -> None:
        while not light_queue.empty():
            await process(light_queue.get_nowait())

    async def heartbeat() -> None:
        # Rewrites the status periodically so a stalled run is visible (old `updated_at`)
        # and the in-flight repositories are fresh even during long repositories.
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            if status:
                status.write(client)

    beat = asyncio.create_task(heartbeat())
    try:
        if status:
            status.write(client)
        workers = [heavy_worker()] + [light_worker() for _ in range(max(0, num_workers - 1))]
        await asyncio.gather(*workers)
    finally:
        beat.cancel()


def remove_orphan_runs(runs_dir: Path, expected: set[str]) -> list[str]:
    """Remove from `runs_dir` every Parquet file that is not a run of `expected`.

    Uses `git rm` for tracked files (so the removal is staged) and a plain
    delete for the others. Returns the removed file names.
    """
    removed: list[str] = []
    if not runs_dir.is_dir():
        return removed
    for path in sorted(runs_dir.glob("*.parquet")):
        if path.name in expected:
            continue
        tracked = (
            subprocess.run(
                ["git", "-C", str(runs_dir), "ls-files", "--error-unmatch", path.name],
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        if tracked:
            subprocess.run(
                ["git", "-C", str(runs_dir), "rm", "-q", "-f", "--", path.name], check=True
            )
        else:
            path.unlink()
        removed.append(path.name)
    return removed


def _copy_atomic(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dest)


def finalize(
    settings: RegenSettings,
    old_records: Sequence[dict[str, Any]],
    new_records: list[dict[str, Any]],
    unsplittable: dict[str, int],
    summary: RegenSummary,
    generated_on: str | None = None,
    kept: dict[str, str] | None = None,
    diagnostics: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Check the invariants and publish datasets, runs and report (all or nothing)."""
    problems = check_invariants(
        old_records, new_records, expected_rows=settings.expected_rows, kept=kept or ()
    )
    missing_runs = [
        r["full_name"]
        for r in new_records
        if not (settings.staged_runs_dir / run_file_name(r["full_name"])).is_file()
    ]
    problems += [f"{n}: runs regenerados ausentes" for n in missing_runs]
    if problems:
        summary.problems = problems
        return

    # Write to staging, verify, then replace
    out = settings.state_dir / "out"
    out.mkdir(parents=True, exist_ok=True)
    out_parquet, out_csv = out / "repositorios.parquet", out / "repositorios.csv"
    save_repositories_dataset(new_records, out_parquet, out_csv)
    baseline_csv = settings.baseline_csv if settings.baseline_csv.is_file() else None
    problems = check_written_files(baseline_csv, out_csv, out_parquet)
    if problems:
        summary.problems = problems
        return

    _copy_atomic(out_parquet, settings.dataset_parquet)
    _copy_atomic(out_csv, settings.dataset_csv)
    for rec in new_records:
        name = run_file_name(rec["full_name"])
        _copy_atomic(settings.staged_runs_dir / name, settings.runs_dir / name)
    summary.removed_orphans = remove_orphan_runs(
        settings.runs_dir, {run_file_name(r["full_name"]) for r in new_records}
    )

    if settings.report_path is not None:
        write_report(
            settings, old_records, new_records, unsplittable, problems, generated_on, kept,
            diagnostics,
        )
    summary.finalized = True
    if settings.bundle_dir is not None:
        summary.bundle = build_bundle(settings, new_records, summary)


def write_report(
    settings: RegenSettings,
    old_records: Sequence[dict[str, Any]],
    new_records: Sequence[dict[str, Any]],
    unsplittable: dict[str, int],
    problems: Sequence[str] = (),
    generated_on: str | None = None,
    kept: dict[str, str] | None = None,
    diagnostics: dict[str, dict[str, Any]] | None = None,
) -> Path:
    """Write the comparison report (old vs new) to `settings.report_path`."""
    assert settings.report_path is not None
    baseline_columns = (
        pq.read_schema(settings.baseline_parquet).names
        if settings.baseline_parquet.is_file()
        else None
    )
    comparison = compare_datasets(
        old_records,
        new_records,
        baseline_columns=baseline_columns,
        min_releases=settings.min_releases,
        min_workflow_runs=settings.min_workflow_runs,
        unsplittable=unsplittable,
        kept=kept,
        runs_diagnostics=diagnostics,
    )
    text = render_report(
        comparison,
        problems,
        generated_on=generated_on or datetime.now(timezone.utc).date().isoformat(),
        window=(settings.window_start.date().isoformat(), settings.window_end.date().isoformat()),
        heuristic=settings.heuristic,
        expected_rows=settings.expected_rows,
    )
    settings.report_path.parent.mkdir(parents=True, exist_ok=True)
    settings.report_path.write_text(text + "\n", encoding="utf-8")
    return settings.report_path


async def run_regeneration(
    settings: RegenSettings,
    client: GitHubClient | None = None,
    limit: int | None = None,
    resume: bool = False,
    fresh: bool = False,
    num_workers: int = 4,
    generated_on: str | None = None,
    only: Sequence[str] | None = None,
    min_available_mb: int = MIN_AVAILABLE_MB,
) -> RegenSummary:
    """Regenerate the metric columns of the frozen sample and publish the result.

    `limit` / `only` restrict the run to some repositories (tests); nothing is published then.
    """
    old_records = prepare_baseline(settings)
    summary = RegenSummary(total=len(old_records))
    fingerprint = settings.fingerprint()

    if fresh:
        reset_state(settings)
    elif not resume and load_checkpoint(settings.checkpoint_path, fingerprint):
        raise RegenerationError(
            "Há um checkpoint de uma execução anterior em "
            f"{settings.checkpoint_path}: use --resume para continuar ou --fresh para recomeçar."
        )

    scope = list(old_records if limit is None else old_records[:limit])
    if only:
        unknown = set(only) - {r["full_name"] for r in old_records}
        if unknown:
            raise RegenerationError(f"repositórios fora do dataset: {sorted(unknown)}")
        scope = [r for r in old_records if r["full_name"] in set(only)]
    summary.scope = len(scope)
    done = load_checkpoint(settings.checkpoint_path, fingerprint)
    summary.reused = len([r for r in scope if r["full_name"] in done])
    logger.info(
        "%d repositories in scope, %d already in the checkpoint", len(scope), summary.reused
    )

    owns_client = client is None
    if client is None:
        client = GitHubClient(cache_path=settings.cache_dir / "http_cache.sqlite")
    status = RunStatus(
        path=settings.status_path,
        total=len(scope),
        done=summary.reused,
        mode=settings.runs_mode,
    )
    try:
        await collect_all(
            settings, scope, done, client, num_workers, summary, status, min_available_mb
        )
    except BaseException:
        status.state = "interrupted"
        status.write(client)
        raise
    finally:
        if owns_client:
            await client.close()

    if summary.failed or limit is not None or only:
        status.state = "failed" if summary.failed else "partial"
        status.write(client)
        return summary

    by_name = {name: entry["record"] for name, entry in done.items()}
    new_records = [by_name[r["full_name"]] for r in old_records if r["full_name"] in by_name]
    unsplittable = {
        name: entry["diagnostics"]["unsplittable_intervals"]
        for name, entry in done.items()
        if entry.get("diagnostics", {}).get("unsplittable_intervals")
    }
    kept = kept_from_checkpoint(done)
    summary.kept = kept
    diagnostics = {name: entry.get("diagnostics", {}) for name, entry in done.items()}
    finalize(
        settings, old_records, new_records, unsplittable, summary, generated_on, kept, diagnostics
    )
    status.state = "finished" if summary.finalized else "invariants-failed"
    status.write(client)
    return summary


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_bundle(
    settings: RegenSettings,
    new_records: Sequence[dict[str, Any]],
    summary: RegenSummary,
    utc_date: str | None = None,
) -> Path:
    """Self-contained `outputs-<UTCdate>.tar.gz` of the published results.

    Holds `repositorios.csv|parquet`, `runs/`, the comparison report, the result of
    the invariants, a `git diff --stat` and `SHA256SUMS` of every member; the
    archive's own digest goes to `<archive>.sha256`. Safe to rebuild.
    """
    assert settings.bundle_dir is not None
    date = utc_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = settings.bundle_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"outputs-{date}.tar.gz"

    members: list[tuple[Path, str]] = [
        (settings.dataset_csv, "dados/repositorios.csv"),
        (settings.dataset_parquet, "dados/repositorios.parquet"),
    ]
    members += [
        (settings.runs_dir / run_file_name(r["full_name"]), f"dados/runs/{run_file_name(r['full_name'])}")
        for r in new_records
    ]
    if settings.report_path is not None and settings.report_path.is_file():
        members.append((settings.report_path, "docs/regeneracao_final.md"))

    staging = settings.state_dir / "bundle"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    invariants = staging / "INVARIANTES.txt"
    old = load_repositories_dataset(settings.baseline_parquet)
    problems = check_invariants(
        old, list(new_records), expected_rows=settings.expected_rows, kept=summary.kept
    )
    invariants.write_text(
        ("OK: todas as invariantes valem (%d linhas)\n" % len(new_records))
        if not problems
        else "VIOLADAS:\n" + "\n".join(f"- {p}" for p in problems) + "\n",
        encoding="utf-8",
    )
    members.append((invariants, "INVARIANTES.txt"))
    diff = staging / "DIFF_STAT.txt"
    try:
        out = subprocess.run(
            ["git", "-C", str(settings.dados_dir), "diff", "--stat", "--", "."],
            capture_output=True, text=True, check=False,
        )
        diff.write_text(out.stdout or out.stderr or "(sem diferenças ou git indisponível)\n", encoding="utf-8")
    except OSError:
        diff.write_text("(git indisponível)\n", encoding="utf-8")
    members.append((diff, "DIFF_STAT.txt"))

    sums = staging / "SHA256SUMS"
    sums.write_text(
        "".join(f"{_sha256(src)}  {arc}\n" for src, arc in members), encoding="utf-8"
    )
    members.append((sums, "SHA256SUMS"))

    tmp = archive.with_name(archive.name + ".tmp")
    with tarfile.open(tmp, "w:gz") as tar:
        for src, arc in members:
            tar.add(src, arcname=f"outputs/{arc}")
    tmp.replace(archive)
    archive.with_name(archive.name + ".sha256").write_text(
        f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8"
    )
    shutil.rmtree(staging, ignore_errors=True)
    return archive


def kept_from_checkpoint(done: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Repositories that kept their previous values, with the reason."""
    return {
        name: entry["diagnostics"]["kept_previous"]
        for name, entry in done.items()
        if entry.get("diagnostics", {}).get("kept_previous")
    }


def format_summary(summary: RegenSummary) -> str:
    """Human-readable summary of a run (no secrets)."""
    lines = [
        f"Repositórios no dataset anterior: {summary.total}",
        f"No escopo desta execução: {summary.scope}",
        f"Reaproveitados do checkpoint: {summary.reused}",
        f"Regenerados nesta execução: {len(summary.collected)}",
        f"Falhas: {len(summary.failed)}",
    ]
    lines += [f"  falha: {name}: {reason}" for name, reason in summary.failed.items()]
    lines += [f"  mantido com valores anteriores: {n}: {r[:120]}" for n, r in summary.kept.items()]
    if summary.problems:
        lines.append("Invariantes violadas (nada foi publicado):")
        lines += [f"  - {p}" for p in summary.problems[:50]]
    if summary.finalized:
        lines.append("Dataset, runs e relatório publicados.")
        if summary.removed_orphans:
            lines.append(f"Runs órfãos removidos: {', '.join(summary.removed_orphans)}")
        if summary.bundle:
            lines.append(f"Pacote de saídas: {summary.bundle}")
    elif not summary.failed and not summary.problems:
        lines.append("Coleta parcial (--limit): nada foi publicado.")
    return "\n".join(lines)


async def validate_reconciliation(
    settings: RegenSettings,
    client: GitHubClient,
    names: Sequence[str],
) -> list[dict[str, Any]]:
    """Check that reconciling the previous runs gives the same runs as a full collection.

    For each repository the runs are reconciled (`runs_mode="reconciliar"`) and compared
    with the full collection: the staged result of a finished repository when there is
    one, otherwise a fresh full collection (spends the quota of a full collection).
    Compares the run ids and the metrics derived from the runs (valid runs, CFR (a) and
    recovery time) and reports the requests each way took.
    """
    import dataclasses

    old_by_name = {r["full_name"]: r for r in load_repositories_dataset(settings.baseline_parquet)}
    done = load_checkpoint(settings.checkpoint_path, settings.fingerprint())
    reconcile_settings = dataclasses.replace(settings, runs_mode=RUNS_MODE_RECONCILE)
    full_settings = dataclasses.replace(settings, runs_mode=RUNS_MODE_FULL)
    results: list[dict[str, Any]] = []

    for name in names:
        old = old_by_name[name]
        reconciled = await acquire_runs(client, old, reconcile_settings)
        staged = settings.staged_runs_dir / run_file_name(name)
        if name in done and staged.is_file() and done[name].get("diagnostics", {}).get("runs_mode", RUNS_MODE_FULL) == RUNS_MODE_FULL:
            full_runs = load_runs_from_parquet(staged)
            full_requests = done[name].get("diagnostics", {}).get("api_requests")
            source = "checkpoint"
        else:
            full = await acquire_runs(client, old, full_settings)
            full_runs, full_requests, source = full.runs, full.api_requests, "coleta completa"

        def derived(runs: Sequence[Any]) -> dict[str, Any]:
            recovery = calculate_recovery_time(runs)
            return {
                "runs": len(runs),
                "cfr_a": calculate_cfr_a(runs),
                "recovery_hours": recovery.median_hours,
                "recovery_episodes": recovery.total_episodes,
                "censored_ratio": recovery.censored_ratio,
            }

        ids_full = {r.id for r in full_runs}
        ids_rec = {r.id for r in reconciled.runs}
        d_full, d_rec = derived(full_runs), derived(reconciled.runs)
        d_full["valid_runs"] = sum(1 for r in full_runs if _is_valid_run(r))
        d_rec["valid_runs"] = reconciled.valid_runs_count
        actions = Counter(e["action"] for e in reconciled.reconciliation)
        results.append(
            {
                "repo": name,
                "full_source": source,
                "same_ids": ids_full == ids_rec,
                "only_in_full": len(ids_full - ids_rec),
                "only_in_reconciled": len(ids_rec - ids_full),
                "same_metrics": {k: d_full[k] for k in d_full if k != "valid_runs"}
                == {k: d_rec[k] for k in d_rec if k != "valid_runs"},
                "full": d_full,
                "reconciled": d_rec,
                "requests_full": full_requests,
                "requests_reconciled": reconciled.api_requests,
                "intervals": dict(actions),
                "refetched": [
                    {k: e.get(k) for k in ("start", "end", "previous_count", "api_count")}
                    for e in reconciled.reconciliation
                    if e["action"] == "refetched"
                ],
            }
        )
        logger.info("validated %s: same_ids=%s", name, results[-1]["same_ids"])
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "validacao_reconciliacao.json").write_text(
        json.dumps(results, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return results


def format_validation(results: Sequence[dict[str, Any]]) -> str:
    """Table of `validate_reconciliation` (no secrets)."""
    lines = ["repo | origem completa | ids iguais | métricas iguais | runs | req. completo | req. reconciliado | intervalos"]
    for r in results:
        lines.append(
            f"{r['repo']} | {r['full_source']} | {r['same_ids']} (só completo {r['only_in_full']}, "
            f"só reconciliado {r['only_in_reconciled']}) | {r['same_metrics']} | {r['full']['runs']} | "
            f"{r['requests_full']} | {r['requests_reconciled']} | {r['intervals']}"
        )
    return "\n".join(lines)


def report_only(settings: RegenSettings, generated_on: str | None = None) -> Path:
    """Regenerate only the report from the baseline and the current dataset."""
    old = load_repositories_dataset(settings.baseline_parquet)
    new = load_repositories_dataset(settings.dataset_parquet)
    if not old or not new:
        raise FileNotFoundError("Baseline ou dataset atual ausente; execute a regeneração antes.")
    fp = settings.fingerprint()
    kept = kept_from_checkpoint(load_checkpoint(settings.checkpoint_path, fp))
    problems = check_invariants(old, new, expected_rows=settings.expected_rows, kept=kept)
    unsplittable = {
        n: e["diagnostics"]["unsplittable_intervals"]
        for n, e in load_checkpoint(settings.checkpoint_path, fp).items()
        if e.get("diagnostics", {}).get("unsplittable_intervals")
    }
    diagnostics = {
        n: e.get("diagnostics", {})
        for n, e in load_checkpoint(settings.checkpoint_path, fp).items()
    }
    return write_report(settings, old, new, unsplittable, problems, generated_on, kept, diagnostics)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regeneração final (Issue #56): recalcula as colunas de métricas dos "
            "repositórios congelados de dados/repositorios.csv"
        )
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Coleta só os N primeiros repositórios (teste); não publica nada",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--resume", action="store_true", help="Continua a partir do checkpoint existente"
    )
    parser.add_argument(
        "--fresh", action="store_true", help="Descarta o checkpoint e recomeça (mantém o baseline)"
    )
    parser.add_argument(
        "--limpar-clones",
        action="store_true",
        help="Apaga cada clone bare após o uso (padrão: mantém, para retomar sem reclonar)",
    )
    parser.add_argument(
        "--manter-antigo",
        action="append",
        default=[],
        metavar="OWNER/REPO",
        help=(
            "Se este repositório não puder ser recoletado (ex.: desabilitado no GitHub), "
            "mantém seus valores anteriores em vez de falhar (repetível; soma-se a "
            "regeneracao.manter_valores_anteriores do config)"
        ),
    )
    parser.add_argument(
        "--apenas",
        nargs="+",
        metavar="OWNER/REPO",
        help="Coleta só estes repositórios (teste de memória/tempo); não publica nada",
    )
    parser.add_argument(
        "--mem-min-disponivel-mb",
        type=int,
        default=MIN_AVAILABLE_MB,
        help="Não inicia novos repositórios enquanto a RAM disponível do sistema for menor (MiB)",
    )
    parser.add_argument(
        "--runs-modo",
        choices=RUNS_MODES,
        default=RUNS_MODE_FULL,
        help=(
            "completo: coleta os runs da janela inteira; reconciliar: reaproveita os runs "
            "anteriores onde a contagem da API (total_count) bate e recoleta o resto e o fim "
            "da janela (precisa de regeneracao.janela_anterior no config)"
        ),
    )
    parser.add_argument(
        "--sem-subprocesso",
        action="store_true",
        help=(
            "Executa a fase de git/commits dentro do próprio processo (comportamento anterior). "
            "Padrão: um processo filho por repositório, que devolve a memória ao sistema ao terminar"
        ),
    )
    parser.add_argument("--status", default=None, help="Arquivo status.json (estado legível por máquina)")
    parser.add_argument(
        "--bundle-dir",
        default=None,
        help="Ao concluir, grava outputs-<data UTC>.tar.gz (+ .sha256) neste diretório",
    )
    parser.add_argument(
        "--validar-reconciliacao",
        nargs="+",
        metavar="OWNER/REPO",
        help="Compara runs reconciliados × coleta completa para estes repositórios e sai",
    )
    parser.add_argument("--relatorio", default=DEFAULT_REPORT, help="Caminho do relatório Markdown")
    parser.add_argument(
        "--somente-relatorio",
        action="store_true",
        help="Só gera o relatório (baseline × dataset atual), sem coletar",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    settings = RegenSettings.from_config(
        config,
        cleanup_clones=args.limpar_clones,
        report_path=args.relatorio,
        keep_previous=args.manter_antigo,
        runs_mode=args.runs_modo,
        status_path=args.status,
        bundle_dir=args.bundle_dir,
        git_subprocess=not args.sem_subprocesso,
    )

    if args.somente_relatorio:
        print(f"Relatório escrito em {report_only(settings)}")
        return 0

    from pipeline.http_client import resolve_tokens

    if args.validar_reconciliacao:
        prepare_baseline(settings)

        async def _validate() -> list[dict[str, Any]]:
            client = GitHubClient(cache_path=settings.cache_dir / "http_cache.sqlite")
            try:
                return await validate_reconciliation(settings, client, args.validar_reconciliacao)
            finally:
                await client.close()

        print(format_validation(asyncio.run(_validate())))
        return 0

    print(f"[*] Tokens configurados: {len(resolve_tokens())}")  # only the count, never the value
    try:
        summary = asyncio.run(
            run_regeneration(
                settings,
                limit=args.limit,
                resume=args.resume,
                fresh=args.fresh,
                num_workers=args.workers,
                only=args.apenas,
                min_available_mb=args.mem_min_disponivel_mb,
            )
        )
    except RegenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(format_summary(summary))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())

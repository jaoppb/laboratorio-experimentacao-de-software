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
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
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
from pipeline.http_client import GitHubClient
from pipeline.orchestrator import (
    collect_c2_c3_units,
    compute_metric_columns,
    load_repositories_dataset,
    save_repositories_dataset,
)
from pipeline.commits import collect_release_commits
from pipeline.regeneracao_relatorio import (
    METADATA_COLUMNS,
    SCHEMA_COLUMNS,
    check_invariants,
    check_written_files,
    compare_datasets,
    render_report,
)
from pipeline.releases import (
    fetch_releases,
    filter_window,
    save_releases_to_parquet,
    save_tags_to_parquet,
)
from pipeline.workflow_runs import collect_workflow_runs, save_runs_to_parquet

logger = logging.getLogger(__name__)

STATE_DIR_NAME = ".regenerar"
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
    report_path: Path | None = Path(DEFAULT_REPORT)

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        cleanup_clones: bool = False,
        report_path: Path | str | None = DEFAULT_REPORT,
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
            report_path=Path(report_path) if report_path else None,
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

    runs_result = await collect_workflow_runs(
        owner=owner,
        repo=repo,
        client=client,
        start_date=settings.window_start,
        end_date=settings.window_end,
        branch=old.get("default_branch"),
        save_to_parquet=False,
    )

    async with temporary_git_clone(
        owner=owner,
        repo=repo,
        cache_dir=settings.git_cache_dir,
        auto_cleanup=settings.cleanup_clones,
        token_pool=client.token_pool,
    ) as git_dir:
        release_commits_c1 = await collect_release_commits(
            client=client,
            owner=owner,
            repo=repo,
            window=window_releases,
            git_dir=git_dir,
        )
        units = await collect_c2_c3_units(
            git_dir=git_dir,
            releases=releases,
            window_start=settings.window_start,
            window_end=settings.window_end,
        )

    metrics = compute_metric_columns(
        releases=releases,
        window_releases=window_releases,
        runs=runs_result.runs,
        valid_runs_count=runs_result.valid_runs_count,
        release_commits_c1=release_commits_c1,
        units=units,
        window_start=settings.window_start,
        window_end=settings.window_end,
        window_weeks=settings.window_weeks,
        cfr_b_heuristic=settings.heuristic,
    )
    record = {col: old.get(col) for col in METADATA_COLUMNS}
    record.update(metrics)

    # Persist artifacts only after everything was computed
    save_runs_to_parquet(
        runs_result.runs,
        owner=owner,
        repo=repo,
        output_path=settings.staged_runs_dir / run_file_name(full_name),
    )
    dados = settings.dados_dir
    save_releases_to_parquet(
        release_commits_c1, owner, repo, dados / "releases" / run_file_name(full_name)
    )
    save_releases_to_parquet(
        units.release_commits_c2, owner, repo, dados / "releases_c2" / run_file_name(full_name)
    )
    save_tags_to_parquet(
        units.tag_commits_c3, owner, repo, dados / "tags" / run_file_name(full_name)
    )

    diagnostics = {
        "api_requests": runs_result.api_requests,
        "unsplittable_intervals": len(runs_result.unsplittable_intervals),
    }
    return record, diagnostics


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
    records = load_repositories_dataset(settings.baseline_parquet)
    if not records:
        raise FileNotFoundError(f"Baseline empty or unreadable: {settings.baseline_parquet}")
    return records


def reset_state(settings: RegenSettings) -> None:
    """Forget the progress of a previous run (checkpoint and staged runs); keep the baseline."""
    settings.checkpoint_path.unlink(missing_ok=True)
    if settings.staged_runs_dir.is_dir():
        shutil.rmtree(settings.staged_runs_dir)


async def collect_all(
    settings: RegenSettings,
    scope: Sequence[dict[str, Any]],
    done: dict[str, dict[str, Any]],
    client: GitHubClient,
    num_workers: int,
    summary: RegenSummary,
) -> None:
    """Collect the repositories of `scope` that are not in the checkpoint yet."""
    fingerprint = settings.fingerprint()
    pending = [r for r in scope if r["full_name"] not in done]
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    for rec in pending:
        queue.put_nowait(rec)
    progress = {"n": 0}

    async def worker() -> None:
        while True:
            try:
                old = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            name = old["full_name"]
            try:
                record, diagnostics = await regenerate_repository(client, old, settings)
            except Exception as exc:
                summary.failed[name] = redact(f"{type(exc).__name__}: {exc}")
                logger.warning("Failed to regenerate %s: %s", name, summary.failed[name])
                continue
            append_checkpoint(settings.checkpoint_path, fingerprint, record, diagnostics)
            done[name] = {"record": record, "diagnostics": diagnostics}
            summary.collected.append(name)
            progress["n"] += 1
            logger.info("[%d/%d] %s regenerated", progress["n"], len(pending), name)

    await asyncio.gather(*(worker() for _ in range(max(1, num_workers))))


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
) -> None:
    """Check the invariants and publish datasets, runs and report (all or nothing)."""
    problems = check_invariants(old_records, new_records, expected_rows=settings.expected_rows)
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
        write_report(settings, old_records, new_records, unsplittable, problems, generated_on)
    summary.finalized = True


def write_report(
    settings: RegenSettings,
    old_records: Sequence[dict[str, Any]],
    new_records: Sequence[dict[str, Any]],
    unsplittable: dict[str, int],
    problems: Sequence[str] = (),
    generated_on: str | None = None,
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
) -> RegenSummary:
    """Regenerate the metric columns of the frozen sample and publish the result."""
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
    summary.scope = len(scope)
    done = load_checkpoint(settings.checkpoint_path, fingerprint)
    summary.reused = len([r for r in scope if r["full_name"] in done])
    logger.info(
        "%d repositories in scope, %d already in the checkpoint", len(scope), summary.reused
    )

    owns_client = client is None
    if client is None:
        client = GitHubClient(cache_path=settings.cache_dir / "http_cache.sqlite")
    try:
        await collect_all(settings, scope, done, client, num_workers, summary)
    finally:
        if owns_client:
            await client.close()

    if summary.failed or limit is not None:
        return summary

    by_name = {name: entry["record"] for name, entry in done.items()}
    new_records = [by_name[r["full_name"]] for r in old_records if r["full_name"] in by_name]
    unsplittable = {
        name: entry["diagnostics"]["unsplittable_intervals"]
        for name, entry in done.items()
        if entry.get("diagnostics", {}).get("unsplittable_intervals")
    }
    finalize(settings, old_records, new_records, unsplittable, summary, generated_on)
    return summary


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
    if summary.problems:
        lines.append("Invariantes violadas (nada foi publicado):")
        lines += [f"  - {p}" for p in summary.problems[:50]]
    if summary.finalized:
        lines.append("Dataset, runs e relatório publicados.")
        if summary.removed_orphans:
            lines.append(f"Runs órfãos removidos: {', '.join(summary.removed_orphans)}")
    elif not summary.failed and not summary.problems:
        lines.append("Coleta parcial (--limit): nada foi publicado.")
    return "\n".join(lines)


def report_only(settings: RegenSettings, generated_on: str | None = None) -> Path:
    """Regenerate only the report from the baseline and the current dataset."""
    old = load_repositories_dataset(settings.baseline_parquet)
    new = load_repositories_dataset(settings.dataset_parquet)
    if not old or not new:
        raise FileNotFoundError("Baseline ou dataset atual ausente; execute a regeneração antes.")
    problems = check_invariants(old, new, expected_rows=settings.expected_rows)
    fp = settings.fingerprint()
    unsplittable = {
        n: e["diagnostics"]["unsplittable_intervals"]
        for n, e in load_checkpoint(settings.checkpoint_path, fp).items()
        if e.get("diagnostics", {}).get("unsplittable_intervals")
    }
    return write_report(settings, old, new, unsplittable, problems, generated_on)


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
        config, cleanup_clones=args.limpar_clones, report_path=args.relatorio
    )

    if args.somente_relatorio:
        print(f"Relatório escrito em {report_only(settings)}")
        return 0

    from pipeline.http_client import resolve_tokens

    print(f"[*] Tokens configurados: {len(resolve_tokens())}")  # only the count, never the value
    try:
        summary = asyncio.run(
            run_regeneration(
                settings,
                limit=args.limit,
                resume=args.resume,
                fresh=args.fresh,
                num_workers=args.workers,
            )
        )
    except RegenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(format_summary(summary))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())

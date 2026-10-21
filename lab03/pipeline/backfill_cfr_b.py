"""Backfill of the CFR (b) columns in the committed repository dataset (Issue #56).

`repositorios.parquet`/`repositorios.csv` were generated before the CFR (b)
columns existed, and the 60-repository gold-standard sample was drawn from
those exact 330 repositories. Re-running the pipeline would redo the candidate
search (the stars rank drifts), so this command keeps the repository set and
fills only the `cfr_b*` columns:

1. for every repository of the dataset, in file order, it reads
   `dados/releases/{owner}__{repo}.parquet`, collecting it first (releases via
   GraphQL, commits via blobless clone, same path as `pipeline.persist_releases`)
   when the file does not exist yet;
2. it computes the CFR (b) columns with the heuristic of `cfr_b.heuristica`
   (`compute_cfr_b_columns`, the same function the orchestrator uses);
3. it rewrites `repositorios.parquet` and `repositorios.csv` with the full
   schema, preserving every other column and the row order.

Execution (from `lab03/`, token in `GITHUB_TOKEN`):
    uv run python -m pipeline.backfill_cfr_b --config config.yaml

The command is idempotent (same inputs, same output) and resumable: collected
`releases/` files are reused, so an interrupted run only collects what is
missing. `--offline` skips the network and fails for repositories without a
`releases/` file.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

from metricas.cfr_b import DEFAULT_HEURISTIC, HEURISTICS
from metricas.schemas import Commit, Release, _parse_datetime
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.http_client import GitHubClient
from pipeline.orchestrator import (
    compute_cfr_b_columns,
    load_repositories_dataset,
    save_repositories_dataset,
)
from pipeline.persist_releases import persist_repository_releases

logger = logging.getLogger(__name__)

CFR_B_COLUMNS = (
    "cfr_b",
    "cfr_b_tier",
    "cfr_b_failed_releases",
    "cfr_b_evaluated_releases",
    "cfr_b_censored_releases",
    "cfr_b_skipped_releases",
)


def releases_path(releases_dir: Path, full_name: str) -> Path:
    """Path of the persisted C1 releases of `full_name`."""
    return releases_dir / f"{full_name.replace('/', '__')}.parquet"


def load_release_commits(path: str | Path) -> list[ReleaseCommits]:
    """Rebuild the `ReleaseCommits` of a repository from its `releases/` Parquet.

    Only what CFR (b) needs is faithful: the release (tag and publication date)
    and the status/commits. `previous` stays None because the file keeps only
    the previous tag name, not its date, and the metric does not use it.
    """
    rows = pq.read_table(path).to_pylist()
    result: list[ReleaseCommits] = []
    for row in rows:
        release = Release(
            tag_name=row["tag_name"],
            published_at=row["published_at"],
            prerelease=bool(row["prerelease"]),
        )
        status = ComparisonStatus(row["status"])
        commits = []
        if status == ComparisonStatus.OK:
            commits = [
                Commit.from_record(c)
                for c in row["commits"] or []
            ]
        result.append(ReleaseCommits(release, None, status, commits))
    return result


@dataclass
class BackfillReport:
    """Outcome of one backfill run."""

    total: int = 0
    collected: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    count_mismatch: list[str] = field(default_factory=list)
    with_cfr_b: int = 0
    without_cfr_b: int = 0
    tiers: Counter = field(default_factory=Counter)
    censored_repos: int = 0
    skipped_repos: int = 0

    @property
    def ok(self) -> bool:
        return not self.failed


def apply_cfr_b(
    record: dict[str, Any], release_commits: list[ReleaseCommits], window_end, heuristic: str
) -> bool:
    """Fill the CFR (b) columns of `record` in place.

    Returns False when the counters do not add up to `releases_count_window`
    (the dataset and `releases/` disagree, e.g. a release changed since the
    original collection).
    """
    columns = compute_cfr_b_columns(release_commits, window_end, heuristic)
    record.update(columns)
    total = (
        columns["cfr_b_evaluated_releases"]
        + columns["cfr_b_censored_releases"]
        + columns["cfr_b_skipped_releases"]
    )
    return record.get("releases_count_window") in (None, total)


def _resolve_heuristic(config: dict[str, Any]) -> str:
    heuristic = (config.get("cfr_b") or {}).get("heuristica") or DEFAULT_HEURISTIC
    if heuristic not in HEURISTICS:
        raise ValueError(
            f"Unknown CFR (b) heuristic {heuristic!r}; available: {sorted(HEURISTICS)}"
        )
    return heuristic


async def backfill_cfr_b(
    config: dict[str, Any],
    client: GitHubClient | None = None,
    num_workers: int = 4,
    limit: int | None = None,
    offline: bool = False,
) -> BackfillReport:
    """Fill the CFR (b) columns of the committed dataset, keeping the repository set."""
    janela = config.get("janela", {})
    dirs = config.get("diretorios", {})
    window_start = _parse_datetime(janela.get("inicio", "2025-10-01"))
    window_end = _parse_datetime(janela.get("fim", "2026-09-30"))
    heuristic = _resolve_heuristic(config)

    dados_dir = Path(dirs.get("dados", "dados"))
    releases_dir = dados_dir / "releases"
    git_cache_dir = Path(dirs.get("git_cache", "cache/git_repos"))
    auto_cleanup = config.get("limpeza_git_cache", True)
    parquet_path = dados_dir / "repositorios.parquet"
    csv_path = dados_dir / "repositorios.csv"

    records = load_repositories_dataset(parquet_path)
    if not records:
        raise FileNotFoundError(f"Dataset not found or empty: {parquet_path}")
    scope = records if limit is None else records[:limit]

    report = BackfillReport(total=len(scope))
    pending = [
        r["full_name"]
        for r in scope
        if not releases_path(releases_dir, r["full_name"]).is_file()
    ]
    logger.info(
        "%d repositories, %d without releases file, heuristic %s",
        len(scope),
        len(pending),
        heuristic,
    )

    if pending and offline:
        for name in pending:
            report.failed[name] = "releases file missing (offline)"
    elif pending:
        owns_client = client is None
        if client is None:
            client = GitHubClient(
                cache_path=Path(dirs.get("cache", "cache")) / "http_cache.sqlite"
            )
        queue: asyncio.Queue[str] = asyncio.Queue()
        for name in pending:
            queue.put_nowait(name)

        async def worker() -> None:
            while not queue.empty():
                name = queue.get_nowait()
                try:
                    await persist_repository_releases(
                        client,  # type: ignore[arg-type]
                        name,
                        window_start=window_start,  # type: ignore[arg-type]
                        window_end=window_end,  # type: ignore[arg-type]
                        releases_dir=releases_dir,
                        git_cache_dir=git_cache_dir,
                        auto_cleanup=auto_cleanup,
                    )
                    report.collected.append(name)
                    logger.info(
                        "[%d/%d] %s collected",
                        len(report.collected) + len(report.failed),
                        len(pending),
                        name,
                    )
                except Exception as exc:
                    report.failed[name] = f"{type(exc).__name__}: {exc}"
                    logger.warning("Could not collect releases of %s: %s", name, exc)

        try:
            await asyncio.gather(*(worker() for _ in range(num_workers)))
        finally:
            if owns_client:
                await client.close()  # type: ignore[union-attr]

    for record in scope:
        name = record["full_name"]
        if name in report.failed:
            report.without_cfr_b += 1
            continue
        consistent = apply_cfr_b(
            record,
            load_release_commits(releases_path(releases_dir, name)),
            window_end,
            heuristic,
        )
        if not consistent:
            report.count_mismatch.append(name)
        if record["cfr_b"] is None:
            report.without_cfr_b += 1
        else:
            report.with_cfr_b += 1
            report.tiers[record["cfr_b_tier"]] += 1
        if record["cfr_b_censored_releases"]:
            report.censored_repos += 1
        if record["cfr_b_skipped_releases"]:
            report.skipped_repos += 1

    # Repositories that failed keep their previous (null) CFR (b) values; the
    # repository set and order are untouched.
    save_repositories_dataset(records, parquet_path, csv_path)
    return report


def format_report(report: BackfillReport) -> str:
    """Human-readable summary of a run (no secrets)."""
    lines = [
        f"Repositórios: {report.total}",
        f"Releases coletadas nesta execução: {len(report.collected)}",
        f"Com CFR (b) calculado: {report.with_cfr_b}",
        f"Sem release avaliável (cfr_b nulo): {report.without_cfr_b}",
        f"Com releases censuradas: {report.censored_repos}",
        f"Com releases ignoradas: {report.skipped_repos}",
        "Faixas de cfr_b_tier: "
        + ", ".join(f"{tier}={n}" for tier, n in sorted(report.tiers.items())),
        f"Inconsistências com releases_count_window: {len(report.count_mismatch)}",
    ]
    lines += [f"  divergente: {name}" for name in report.count_mismatch]
    lines += [f"  falha: {name}: {reason}" for name, reason in report.failed.items()]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preenche as colunas cfr_b* do dataset sem alterar o conjunto de repositórios"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Não acessa a rede: usa apenas os arquivos de dados/releases/ existentes",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    report = asyncio.run(
        backfill_cfr_b(
            config, num_workers=args.workers, limit=args.limit, offline=args.offline
        )
    )
    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

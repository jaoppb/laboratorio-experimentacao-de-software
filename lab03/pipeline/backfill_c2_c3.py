"""Backfill of the pre-release, tag, C2 and C3 columns of the committed dataset (Issue #56).

After `pipeline.backfill_cfr_b` the 330-repository dataset still has eight null
columns: `prereleases_count_window`, `total_prereleases`, `tags_count_window`,
`total_tags`, `c2_deployment_frequency`, `c2_lead_time_b_hours`,
`c3_deployment_frequency` and `c3_lead_time_b_hours`. They only existed for
repositories processed by the current orchestrator. As with the CFR (b)
backfill, re-running the pipeline would redo the candidate search, so this
command keeps the repository set and fills only those columns:

1. for every repository, in file order, it collects (when missing) the C2
   units (releases + pre-releases, via GraphQL) and the C3 units (every Git
   tag of a blobless clone) with the same functions as the orchestrator
   (`collect_c2_c3_units`), and persists them to `releases_c2/` and `tags/`
   plus a small `c2_c3_meta/` JSON with the totals that the window files do
   not carry (`total_prereleases`, `total_tags`);
2. it computes the columns from those persisted files with
   `compute_c2_c3_columns`, the function the orchestrator uses;
3. it rewrites `repositorios.parquet` and `repositorios.csv` with the full
   schema, preserving every other column and the row order.

Execution (from `lab03/`, token in `GITHUB_TOKEN`):
    uv run python -m pipeline.backfill_c2_c3 --config config.yaml

The command is idempotent (same inputs, same output) and resumable: a
repository whose three files exist is not collected again. `--offline` skips
the network and fails for repositories without them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

from metricas.schemas import (
    Commit,
    Release,
    _parse_datetime,
    parse_window_end,
    window_length,
)
from pipeline.backfill_cfr_b import load_release_commits, releases_path
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.git_clone import temporary_git_clone
from pipeline.http_client import GitHubClient
from pipeline.orchestrator import (
    collect_c2_c3_units,
    compute_c2_c3_columns,
    load_repositories_dataset,
    save_repositories_dataset,
)
from pipeline.releases import (
    fetch_releases,
    filter_window,
    save_releases_to_parquet,
    save_tags_to_parquet,
)

logger = logging.getLogger(__name__)

C2_C3_COLUMNS = (
    "prereleases_count_window",
    "total_prereleases",
    "tags_count_window",
    "total_tags",
    "c2_deployment_frequency",
    "c2_lead_time_b_hours",
    "c3_deployment_frequency",
    "c3_lead_time_b_hours",
)


@dataclass
class RepoPaths:
    """Files persisted for one repository by this backfill."""

    releases_c2: Path
    tags: Path
    meta: Path

    def complete(self, window: tuple[datetime, datetime] | None = None) -> bool:
        """The meta file is written last, so its presence marks a finished collection.

        With `window`, the collection must also have been made for that exact
        observation window (the C2/C3 units depend on it); files collected for
        another window are stale and collected again.
        """
        if not (self.releases_c2.is_file() and self.tags.is_file() and self.meta.is_file()):
            return False
        if window is None:
            return True
        return read_meta(self.meta).get("window") == window_key(*window)


def repo_paths(dados_dir: Path, full_name: str) -> RepoPaths:
    """Locations of the C2, C3 and totals files of `full_name`."""
    return RepoPaths(
        releases_c2=releases_path(dados_dir / "releases_c2", full_name),
        tags=releases_path(dados_dir / "tags", full_name),
        meta=releases_path(dados_dir / "c2_c3_meta", full_name).with_suffix(".json"),
    )


def window_key(window_start: datetime, window_end: datetime) -> list[str]:
    """Window identity stored in the meta file."""
    return [window_start.isoformat(), window_end.isoformat()]


def load_tag_commits(path: str | Path) -> list[ReleaseCommits]:
    """Rebuild the `ReleaseCommits` of the C3 tags of a repository from its `tags/` Parquet.

    The file does not keep the comparison status: a tag with a previous tag is
    loaded as `OK` (even when the original comparison was `NOT_FOUND`, which is
    saved with no commits) and one without as `FIRST_RELEASE`. The columns of
    this backfill only use the window count and the commit lead times, which
    are the same either way (no commits contribute to the median).
    """
    result: list[ReleaseCommits] = []
    for row in pq.read_table(path).to_pylist():
        tag = Release(
            tag_name=row["tag_name"],
            published_at=row["published_at"],
            commit_sha=row["commit_sha"],
        )
        if row["previous_tag"] is None:
            result.append(ReleaseCommits(tag, None, ComparisonStatus.FIRST_RELEASE))
            continue
        commits = [Commit.from_record(c) for c in row["commits"] or []]
        result.append(ReleaseCommits(tag, None, ComparisonStatus.OK, commits))
    return result


def write_meta(path: Path, meta: dict[str, Any]) -> None:
    """Atomically write the totals JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_meta(path: Path) -> dict[str, Any]:
    """Totals saved at collection time."""
    return json.loads(path.read_text(encoding="utf-8"))


async def collect_repository_c2_c3(
    client: GitHubClient,
    full_name: str,
    window_start,
    window_end,
    dados_dir: Path,
    git_cache_dir: Path,
    auto_cleanup: bool = True,
) -> RepoPaths:
    """Collect and persist the C2/C3 units of one repository (same path as the orchestrator)."""
    owner, repo = full_name.split("/", 1)
    paths = repo_paths(dados_dir, full_name)
    releases = await fetch_releases(
        client=client, owner=owner, repo=repo, window_start=window_start, use_graphql=True
    )

    async with temporary_git_clone(
        owner=owner,
        repo=repo,
        cache_dir=git_cache_dir,
        auto_cleanup=auto_cleanup,
        token_pool=client.token_pool,
    ) as git_dir:
        units = await collect_c2_c3_units(
            git_dir=git_dir,
            releases=releases,
            window_start=window_start,
            window_end=window_end,
        )

    save_releases_to_parquet(units.release_commits_c2, owner, repo, paths.releases_c2)
    save_tags_to_parquet(units.tag_commits_c3, owner, repo, paths.tags)
    write_meta(
        paths.meta,
        {
            # C1 figures of the fresh collection, to detect drift from the dataset
            "releases_count_window": filter_window(releases, window_start, window_end).count,
            "total_releases": len(releases),
            "total_prereleases": len([r for r in releases if r.prerelease]),
            "total_tags": len(units.all_tags),
            # window the units were collected for (C2/C3 depend on it)
            "window": window_key(window_start, window_end),
        },
    )
    return paths


@dataclass
class BackfillC2C3Report:
    """Outcome of one backfill run."""

    total: int = 0
    collected: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    # Repositories whose fresh in-window C1 count differs from `releases_count_window`
    count_mismatch: list[str] = field(default_factory=list)
    # Repositories whose fresh `total_releases` differs (releases published or
    # removed since the original collection; the dataset value is kept)
    total_drift: list[str] = field(default_factory=list)
    filled: int = 0
    with_prereleases: int = 0
    without_c2_lead_time: int = 0
    without_c3_lead_time: int = 0
    without_tags: int = 0

    @property
    def ok(self) -> bool:
        return not self.failed


def apply_c2_c3(
    record: dict[str, Any], paths: RepoPaths, window_weeks: float
) -> tuple[bool, bool]:
    """Fill the eight C2/C3 columns of `record` in place from the persisted files.

    Returns `(window_consistent, total_consistent)`: whether the C1 figures
    saved at collection time match `releases_count_window` and `total_releases`
    of the dataset record. `total_releases` drifts whenever releases are
    published after the original collection (the fetch is newest first), which
    also moves `total_prereleases`; the window count only changes if releases
    inside the (closed) window were removed or re-dated.
    """
    meta = read_meta(paths.meta)
    record.update(
        compute_c2_c3_columns(
            load_release_commits(paths.releases_c2),
            load_tag_commits(paths.tags),
            total_prereleases=meta["total_prereleases"],
            total_tags=meta["total_tags"],
            window_weeks=window_weeks,
        )
    )
    return (
        record.get("releases_count_window") in (None, meta["releases_count_window"]),
        record.get("total_releases") in (None, meta["total_releases"]),
    )


async def backfill_c2_c3(
    config: dict[str, Any],
    client: GitHubClient | None = None,
    num_workers: int = 4,
    limit: int | None = None,
    offline: bool = False,
) -> BackfillC2C3Report:
    """Fill the pre-release/tag/C2/C3 columns of the committed dataset, keeping the repository set."""
    janela = config.get("janela", {})
    dirs = config.get("diretorios", {})
    window_start = _parse_datetime(janela.get("inicio", "2025-10-01"))
    # `fim` date-only = end of that day (same interpretation as the orchestrator)
    window_end = parse_window_end(janela.get("fim", "2026-09-30"))
    window_weeks = window_length(window_start, window_end) / timedelta(weeks=1)  # type: ignore[arg-type]

    dados_dir = Path(dirs.get("dados", "dados"))
    git_cache_dir = Path(dirs.get("git_cache", "cache/git_repos"))
    auto_cleanup = config.get("limpeza_git_cache", True)
    parquet_path = dados_dir / "repositorios.parquet"
    csv_path = dados_dir / "repositorios.csv"

    records = load_repositories_dataset(parquet_path)
    if not records:
        raise FileNotFoundError(f"Dataset not found or empty: {parquet_path}")
    scope = records if limit is None else records[:limit]

    report = BackfillC2C3Report(total=len(scope))
    window = (window_start, window_end)
    pending = [
        r["full_name"]
        for r in scope
        if not repo_paths(dados_dir, r["full_name"]).complete(window)  # type: ignore[arg-type]
    ]
    logger.info("%d repositories, %d without C2/C3 files", len(scope), len(pending))

    if pending and offline:
        for name in pending:
            report.failed[name] = "C2/C3 files missing (offline)"
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
                    await collect_repository_c2_c3(
                        client,  # type: ignore[arg-type]
                        name,
                        window_start=window_start,
                        window_end=window_end,
                        dados_dir=dados_dir,
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
                    logger.warning("Could not collect C2/C3 units of %s: %s", name, exc)

        try:
            await asyncio.gather(*(worker() for _ in range(num_workers)))
        finally:
            if owns_client:
                await client.close()  # type: ignore[union-attr]

    for record in scope:
        name = record["full_name"]
        if name in report.failed:
            continue
        paths = repo_paths(dados_dir, name)
        if not paths.complete(window):  # type: ignore[arg-type]
            # e.g. files removed while the run was in progress
            report.failed[name] = "C2/C3 files missing"
            continue
        window_ok, total_ok = apply_c2_c3(record, paths, window_weeks)
        if not window_ok:
            report.count_mismatch.append(name)
        if not total_ok:
            report.total_drift.append(name)
        report.filled += 1
        if record["total_prereleases"]:
            report.with_prereleases += 1
        if record["total_tags"] == 0:
            report.without_tags += 1
        if record["c2_lead_time_b_hours"] is None:
            report.without_c2_lead_time += 1
        if record["c3_lead_time_b_hours"] is None:
            report.without_c3_lead_time += 1

    # Repositories that failed keep their previous (null) values; the
    # repository set and order are untouched.
    save_repositories_dataset(records, parquet_path, csv_path)
    return report


def format_report(report: BackfillC2C3Report) -> str:
    """Human-readable summary of a run (no secrets)."""
    lines = [
        f"Repositórios: {report.total}",
        f"Coletados nesta execução: {len(report.collected)}",
        f"Colunas C2/C3 preenchidas: {report.filled}",
        f"Com pré-releases coletadas (total_prereleases > 0): {report.with_prereleases}",
        f"Sem nenhuma tag (total_tags = 0): {report.without_tags}",
        f"Sem lead time C2 (c2_lead_time_b_hours nulo): {report.without_c2_lead_time}",
        f"Sem lead time C3 (c3_lead_time_b_hours nulo): {report.without_c3_lead_time}",
        f"Divergências com releases_count_window: {len(report.count_mismatch)}",
        f"Deriva de total_releases desde a coleta original: {len(report.total_drift)}",
    ]
    lines += [f"  divergente: {name}" for name in report.count_mismatch]
    lines += [f"  falha: {name}: {reason}" for name, reason in report.failed.items()]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preenche as colunas de pré-releases, tags, C2 e C3 do dataset "
            "sem alterar o conjunto de repositórios"
        )
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Não acessa a rede: usa apenas os arquivos já coletados de releases_c2/, tags/ e c2_c3_meta/",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    report = asyncio.run(
        backfill_c2_c3(config, num_workers=args.workers, limit=args.limit, offline=args.offline)
    )
    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

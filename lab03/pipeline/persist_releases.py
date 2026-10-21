"""Persist releases and commits per release for repositories already accepted.

The orchestrator only writes `dados/releases/` for repositories it accepts in
the current run, so the sample collected before this file existed has no
release data on disk. This command backfills it, reusing the same collection
functions (releases via GraphQL, commits via local blobless clone).

Execution (from `lab03/`):
    uv run python -m pipeline.persist_releases --config config.yaml

Repositories whose Parquet file already exists are skipped, so an interrupted
run resumes where it stopped.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

from metricas.schemas import _parse_datetime, parse_window_end
from pipeline.commits import collect_release_commits
from pipeline.git_clone import temporary_git_clone
from pipeline.http_client import GitHubClient
from pipeline.releases import fetch_releases, filter_window, save_releases_to_parquet

logger = logging.getLogger(__name__)


def accepted_repositories(dataset_path: str | Path) -> list[str]:
    """`full_name` of every repository in the accepted dataset, in file order."""
    path = Path(dataset_path)
    if not path.is_file():
        return []
    return [str(n) for n in pq.read_table(path, columns=["full_name"]).column(0).to_pylist()]


async def persist_repository_releases(
    client: GitHubClient,
    full_name: str,
    window_start: datetime,
    window_end: datetime,
    releases_dir: Path,
    git_cache_dir: Path,
    auto_cleanup: bool = True,
) -> Path:
    """Collect the in-window releases (+ anchor) of one repository and save them."""
    owner, repo = full_name.split("/", 1)
    releases = await fetch_releases(
        client=client, owner=owner, repo=repo, window_start=window_start, use_graphql=True
    )
    window = filter_window(releases, window_start=window_start, window_end=window_end)

    async with temporary_git_clone(
        owner=owner,
        repo=repo,
        cache_dir=git_cache_dir,
        auto_cleanup=auto_cleanup,
        token_pool=client.token_pool,
    ) as git_dir:
        release_commits = await collect_release_commits(
            client=client, owner=owner, repo=repo, window=window, git_dir=git_dir
        )

    return save_releases_to_parquet(
        release_commits=release_commits,
        owner=owner,
        repo=repo,
        output_path=releases_dir / f"{owner}__{repo}.parquet",
    )


async def persist_all(
    config: dict[str, Any],
    client: GitHubClient | None = None,
    num_workers: int = 4,
    limit: int | None = None,
) -> dict[str, list[str]]:
    """Backfill `dados/releases/` for every accepted repository missing it."""
    janela = config.get("janela", {})
    dirs = config.get("diretorios", {})
    window_start = _parse_datetime(janela.get("inicio", "2025-10-01"))
    window_end = parse_window_end(janela.get("fim", "2026-09-30"))
    dados_dir = Path(dirs.get("dados", "dados"))
    releases_dir = dados_dir / "releases"
    git_cache_dir = Path(dirs.get("git_cache", "cache/git_repos"))
    auto_cleanup = config.get("limpeza_git_cache", True)

    names = accepted_repositories(dados_dir / "repositorios.parquet")
    if limit is not None:
        names = names[:limit]
    pending = [
        n for n in names if not (releases_dir / f"{n.replace('/', '__')}.parquet").is_file()
    ]
    logger.info("%d accepted repositories, %d pending", len(names), len(pending))

    owns_client = client is None
    if client is None:
        client = GitHubClient(cache_path=Path(dirs.get("cache", "cache")) / "http_cache.sqlite")

    done: list[str] = []
    failed: list[str] = []
    queue: asyncio.Queue[str] = asyncio.Queue()
    for name in pending:
        queue.put_nowait(name)

    async def worker() -> None:
        while not queue.empty():
            name = queue.get_nowait()
            try:
                await persist_repository_releases(
                    client,
                    name,
                    window_start=window_start,  # type: ignore[arg-type]
                    window_end=window_end,  # type: ignore[arg-type]
                    releases_dir=releases_dir,
                    git_cache_dir=git_cache_dir,
                    auto_cleanup=auto_cleanup,
                )
                done.append(name)
                logger.info("[%d/%d] %s saved", len(done) + len(failed), len(pending), name)
            except Exception as exc:
                failed.append(name)
                logger.warning("Could not persist releases of %s: %s", name, exc)

    try:
        await asyncio.gather(*(worker() for _ in range(num_workers)))
    finally:
        if owns_client:
            await client.close()

    return {"done": done, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Persiste releases e commits por release dos repositórios aceitos"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    result = asyncio.run(persist_all(config, num_workers=args.workers, limit=args.limit))
    print(f"Salvos: {len(result['done'])} | Falhas: {len(result['failed'])}")
    for name in result["failed"]:
        print(f"  falha: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

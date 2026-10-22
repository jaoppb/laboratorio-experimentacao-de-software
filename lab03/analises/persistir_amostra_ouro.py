"""Persiste as releases apenas dos repositórios da amostra-ouro (Issue #63).

Evita rodar o backfill dos 330 repositórios: só os 60 sorteados precisam de
`dados/releases/`. Reutiliza `persist_repository_releases`.

Execução (a partir de `lab03/`):
    uv run python -m analises.persistir_amostra_ouro
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from analises.amostra_ouro import DEFAULT_NUM_REPOS, DEFAULT_SEED, sortear_repositorios
from metricas.schemas import _parse_datetime, parse_window_end
from pipeline.http_client import GitHubClient
from pipeline.persist_releases import is_persisted, persist_repository_releases

logger = logging.getLogger(__name__)


async def persistir(
    dataset: Path = Path("dados/repositorios.parquet"),
    releases_dir: Path = Path("dados/releases"),
    git_cache: Path = Path("cache/git_repos"),
    workers: int = 4,
) -> dict[str, list[str]]:
    sample = sortear_repositorios(dataset, n=DEFAULT_NUM_REPOS, seed=DEFAULT_SEED)
    pending = [n for n in sample["full_name"].tolist() if not is_persisted(releases_dir, n)]
    logger.info("%d repositórios sorteados, %d pendentes", len(sample), len(pending))

    start = _parse_datetime("2025-10-01")
    end = parse_window_end("2026-09-30")
    client = GitHubClient(cache_path=Path("cache") / "http_cache.sqlite")
    queue: asyncio.Queue[str] = asyncio.Queue()
    for n in pending:
        queue.put_nowait(n)
    done: list[str] = []
    failed: list[str] = []

    async def worker() -> None:
        while not queue.empty():
            name = queue.get_nowait()
            try:
                await persist_repository_releases(
                    client, name, start, end, releases_dir, git_cache
                )
                done.append(name)
                logger.info("[%d/%d] %s", len(done) + len(failed), len(pending), name)
            except Exception as exc:
                failed.append(name)
                logger.warning("Falha em %s: %s", name, exc)

    try:
        await asyncio.gather(*(worker() for _ in range(workers)))
    finally:
        await client.close()
    return {"done": done, "failed": failed}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    res = asyncio.run(persistir())
    print(f"[*] salvos: {len(res['done'])}, falhas: {len(res['failed'])}")
    for f in res["failed"]:
        print("   falhou:", f)
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())

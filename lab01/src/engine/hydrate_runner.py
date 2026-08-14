from typing import Dict, List

import structlog

from src.core.concurrency_controller import QueryWeight
from src.core.github_client import GitHubClient
from src.core.resilience import execute_with_adaptive_halving
from src.graphql.query import Query

logger = structlog.get_logger(__name__)


class HydrateRunner:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def run_hydrate_all(
        self,
        hydrate_graphql: str,
        query_obj: Query,
        all_ids: List[str],
        concurrency_controller,
    ) -> List[Dict]:
        """
        Orchestrates the massive parallel scatter-gather hydration process.
        Chunks IDs and manages dynamic concurrency via the token-aware controller.
        """
        import asyncio

        CHUNK_SIZE = 20
        id_chunks = [
            all_ids[i : i + CHUNK_SIZE] for i in range(0, len(all_ids), CHUNK_SIZE)
        ]

        async def hydrate_chunk(chunk: List[str], chunk_idx: int):
            async with concurrency_controller.acquire(weight=QueryWeight.HEAVY):
                logger.debug(
                    "hydrating_chunk",
                    chunk_index=chunk_idx + 1,
                    total_chunks=len(id_chunks),
                    chunk_size=len(chunk),
                )
                return await execute_with_adaptive_halving(
                    self._run_hydrate, chunk, hydrate_graphql, query_obj
                )

        tasks = [hydrate_chunk(chunk, i) for i, chunk in enumerate(id_chunks)]
        chunk_results = await asyncio.gather(*tasks)

        # Gather and flatten
        return [repo for chunk in chunk_results for repo in chunk]

    async def _run_hydrate(
        self, ids: List[str], hydrate_graphql: str, query_obj: Query
    ) -> List[Dict]:
        """
        Executes the AST Hydration query sequentially.
        It has NO error handling. If a 504 occurs, `execute_with_adaptive_halving`
        will intercept it, split the `ids` array in half, and run both halves independently.
        """
        if not ids:
            return []

        variables = {"ids": ids}
        data = await self.client.run_query(hydrate_graphql, variables)
        nodes = data.get("data", {}).get("nodes", [])

        # The nodes array returns in the EXACT same order as the IDs we requested!
        # This is what guarantees mathematical correctness of the sort.
        results = []
        for i, node in enumerate(nodes):
            if not node:
                continue

            parsed_repo = {}
            for field, eval_str in query_obj.metadata.extractors.items():
                try:
                    from datetime import datetime, timezone

                    parsed_repo[field] = eval(
                        eval_str,
                        {"repo": node, "datetime": datetime, "timezone": timezone},
                    )
                except Exception as e:
                    logger.error(f"Error parsing field {field}: {e}")
                    parsed_repo[field] = None

            parsed_repo["id"] = ids[i]  # Re-attach ID just in case
            results.append(parsed_repo)

        return results

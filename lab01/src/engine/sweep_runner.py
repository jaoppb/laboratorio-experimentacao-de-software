import asyncio
from typing import List

import structlog

from src.core.concurrency_controller import QueryWeight
from src.core.github_client import GitHubClient
from src.core.resilience import execute_with_adaptive_halving

logger = structlog.get_logger(__name__)


class SweepRunner:
    def __init__(self, client: GitHubClient):
        self.client = client
        self.max_batch_size = (
            100  # Sweep queries are lightweight, so we can maximize the batch
        )

    async def run_sweep_all(
        self,
        sweep_graphql: str,
        search_query: str,
        sample_size: int,
        brackets: List[tuple],
        concurrency_controller,
    ) -> List[str]:
        """
        Orchestrates the massively parallel sweeping of all mathematically resolved star brackets.
        """
        remaining = sample_size

        parts = search_query.split()
        clean_parts = [
            p for p in parts if not p.startswith("stars:") and not p.startswith("sort:")
        ]
        base_clean = " ".join(clean_parts)
        sort_token = "sort:stars-desc"

        tasks = []

        async def sweep_bracket(bracket_query: str, target: int):
            async with concurrency_controller.acquire(weight=QueryWeight.LIGHT):
                logger.debug(
                    "sweeping_bracket", bracket=bracket_query, target_fetch=target
                )
                # Wrap the call inside the adaptive halver, passing the initial batch size
                return await execute_with_adaptive_halving(
                    self._run_sweep,
                    self.max_batch_size,
                    sweep_graphql,
                    bracket_query,
                    target,
                )

        for min_s, max_s, count in brackets:
            if remaining <= 0:
                break

            bracket_query = f"{base_clean} stars:{min_s}..{max_s} {sort_token}".strip()
            target = min(remaining, count)

            tasks.append(sweep_bracket(bracket_query, target))
            remaining -= target

        # Execute all sweeps simultaneously
        chunk_results = await asyncio.gather(*tasks)

        # Flatten the sequentially ordered results
        return [repo_id for chunk in chunk_results for repo_id in chunk]

    async def _run_sweep(
        self, batch_size: int, sweep_graphql: str, search_query: str, target_count: int
    ) -> List[str]:
        """
        Executes the AST Sweep query sequentially using cursor pagination.
        It has NO error handling. If a 504 occurs, `execute_with_adaptive_halving`
        will intercept it and restart this function with a smaller `batch_size`.
        """
        ids = []
        cursor = None

        while len(ids) < target_count:
            fetch_count = min(batch_size, target_count - len(ids))
            variables = {
                "searchQuery": search_query,
                "first": fetch_count,
                "after": cursor,
            }

            data = await self.client.run_query(sweep_graphql, variables)

            search_data = data.get("data", {}).get("search", {})
            nodes = search_data.get("nodes", [])
            page_info = search_data.get("pageInfo", {})

            for node in nodes:
                if node and "id" in node:
                    ids.append(node["id"])

            if not page_info.get("hasNextPage") or not nodes:
                break

            cursor = page_info.get("endCursor")

        return ids[:target_count]

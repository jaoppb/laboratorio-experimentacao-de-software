import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

import structlog

from src.base_query_runner import BaseQueryRunner
from src.core.github_client import GitHubClient
from src.graphql.query import Query
from src.query_runner import SequentialQueryRunner

logger = structlog.get_logger(__name__)


class ShardedQueryRunner(BaseQueryRunner):
    def __init__(self, client: GitHubClient, max_concurrent: int = 5):
        self.client = client
        self.max_concurrent = max_concurrent

    def _generate_sharded_search_queries(
        self, num_shards: int, base_query: str
    ) -> List[str]:
        # Start exactly when GitHub launched to today
        start_date = datetime(2008, 1, 1)
        end_date = datetime.now()

        total_days = (end_date - start_date).days
        days_per_shard = total_days // num_shards

        queries = []
        current_start = start_date

        # Clean up the base query (we will re-append the sort at the end)
        sort_token = "sort:stars-desc"
        base_clean = base_query.replace(sort_token, "").strip()

        for i in range(num_shards):
            if i == num_shards - 1:
                current_end = end_date
            else:
                current_end = current_start + timedelta(days=days_per_shard)

            start_str = current_start.strftime("%Y-%m-%d")
            end_str = current_end.strftime("%Y-%m-%d")
            date_filter = f"created:{start_str}..{end_str}"

            # Reconstruct the query string carefully
            sharded_query = f"{base_clean} {date_filter} {sort_token}".strip()
            queries.append(sharded_query)

            # Start the next shard the day after the current end
            current_start = current_end + timedelta(days=1)

        return queries

    async def run_query(
        self,
        query_obj: Query,
        sample_size: int,
        search_query: str = "stars:>1 sort:stars-desc",
    ) -> List[Dict]:
        # If the sample size is huge, we want many shards to prevent hitting the 1000 limit per shard.
        # Ensure we have enough shards so no shard is expected to fetch > 1000 repos
        min_required_shards = (sample_size // 1000) + 1

        # We always want at least enough shards to fully utilize concurrency (5)
        num_shards = max(self.max_concurrent, min_required_shards)

        # Distribute the total sample size across the shards
        shard_sample_size = (sample_size // num_shards) + 1

        logger.info(
            f"[Sharding Engine] Slicing {sample_size} records into {num_shards} concurrent date chunks..."
        )
        sharded_search_queries = self._generate_sharded_search_queries(
            num_shards, search_query
        )

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_shard(shard_search: str, shard_index: int):
            async with semaphore:
                logger.info(
                    f"  -> Starting Shard {shard_index + 1}/{num_shards}: {shard_search}"
                )
                runner = SequentialQueryRunner(self.client)
                return await runner.run_query(
                    query_obj, shard_sample_size, shard_search
                )

        # Run all shards concurrently
        tasks = [run_shard(q, i) for i, q in enumerate(sharded_search_queries)]
        results = await asyncio.gather(*tasks)

        # Flatten results list of lists
        flattened = [item for sublist in results for item in sublist]

        # Truncate to exact requested sample size in case shards over-delivered
        final_results = flattened[:sample_size]
        logger.info(
            f"[Sharding Engine] Extraction complete! Reassembled {len(final_results)} records from {num_shards} shards."
        )
        return final_results

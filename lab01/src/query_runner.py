import time
from datetime import datetime, timezone
from typing import Dict, List

import structlog

from src.base_query_runner import BaseQueryRunner
from src.core.github_client import GitHubClient
from src.graphql.query import Query

logger = structlog.get_logger(__name__)


class SequentialQueryRunner(BaseQueryRunner):
    def __init__(self, client: GitHubClient):
        self.client = client

    async def run_query(
        self,
        query_obj: Query,
        sample_size: int,
        search_query: str = "stars:>1 sort:stars-desc",
    ) -> List[Dict]:
        results = []
        cursor = None

        # Dynamically load the absolute max batch size from the JSON config
        initial_max = query_obj.metadata.config.optimal_batch_size

        batch_size = initial_max
        logger.info(
            f"  [Optimizer] Starting latency-based engine with max batch size {initial_max}"
        )

        while len(results) < sample_size:
            fetch_count = min(batch_size, sample_size - len(results))
            variables = {
                "searchQuery": search_query,
                "first": fetch_count,
                "after": cursor,
            }

            # Print the calculated metadata points before querying
            theoretical_cost = query_obj.calculate_theoretical_cost(fetch_count)
            query_obj.metadata.last_theoretical_cost = theoretical_cost
            logger.info(
                f"  [Calculated Metadata] Expected Cost: {theoretical_cost} points"
            )

            try:
                start_time = time.time()
                data = await self.client.run_query(query_obj.content, variables)
                latency = time.time() - start_time

                # --- LATENCY CONTROLLER ---
                if latency < 4.0:
                    new_batch_size = min(initial_max, batch_size + 5)
                    if new_batch_size > batch_size:
                        logger.info(
                            f"  [Optimizer] Fast response ({latency:.2f}s). Scaling up: {batch_size} -> {new_batch_size}"
                        )
                        batch_size = new_batch_size
                elif latency > 7.0:
                    new_batch_size = max(1, batch_size - 5)
                    if new_batch_size < batch_size:
                        logger.warning(
                            f"  [Optimizer] Slow response ({latency:.2f}s). Scaling down to avoid timeout: {batch_size} -> {new_batch_size}"
                        )
                        batch_size = new_batch_size

            except Exception as e:
                # --- FALLBACK: 502/504 TIMEOUT ---
                if batch_size > 1:
                    new_batch_size = max(1, batch_size // 2)
                    logger.warning(
                        f"  [Optimizer] Server error/Timeout. Halving capacity: {batch_size} -> {new_batch_size}"
                    )
                    batch_size = new_batch_size
                    continue
                else:
                    logger.error(
                        "  [Optimizer] Query failed even with batch_size=1. Aborting."
                    )
                    raise e

            if "rateLimit" in data["data"]:
                rl = data["data"]["rateLimit"]
                query_obj.metadata.last_actual_cost = rl["cost"]
                logger.info(
                    f"  [RateLimit] Actual Cost: {rl['cost']} points | Remaining: {rl['remaining']} points"
                )

            search_data = data["data"]["search"]
            nodes = search_data["nodes"]

            for repo in nodes:
                # Add check in case nodes is smaller than fetch_count somehow (e.g. at end of list)
                if not repo:
                    continue

                parsed_row = {}
                env = {"repo": repo, "datetime": datetime, "timezone": timezone}

                for target_col, python_expr in query_obj.metadata.extractors.items():
                    try:
                        parsed_row[target_col] = eval(python_expr, env)
                    except Exception as e:
                        logger.error(
                            f"Error evaluating '{python_expr}' for {target_col}: {e}"
                        )
                        parsed_row[target_col] = None

                results.append(parsed_row)

            page_info = search_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break

            cursor = page_info["endCursor"]

        return results

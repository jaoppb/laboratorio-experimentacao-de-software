from typing import List, Tuple

import structlog

from src.core.github_client import GitHubClient

logger = structlog.get_logger(__name__)


class StarRangeResolver:
    def __init__(self, client: GitHubClient):
        self.client = client
        self.max_stars = 1000000  # 1 million stars is well above the highest repo
        self.threshold = 950  # Leave a small buffer below 1000 for safety

    async def _get_count(self, base_query: str, min_stars: int, max_stars: int) -> int:
        query_str = """
        query($searchQuery: String!) {
          search(query: $searchQuery, type: REPOSITORY, first: 1) {
            repositoryCount
          }
        }
        """
        # The search_query is a GitHub Search Syntax string (e.g., "language:python stars:>1").
        # It is NOT a GraphQL AST, so we tokenize it by spaces to safely filter out existing qualifiers.
        parts = base_query.split()
        clean_parts = [
            p for p in parts if not p.startswith("stars:") and not p.startswith("sort:")
        ]
        clean_base = " ".join(clean_parts)

        search_query = f"{clean_base} stars:{min_stars}..{max_stars}"

        variables = {"searchQuery": search_query}
        try:
            data = await self.client.run_query(query_str, variables)
            return data["data"]["search"]["repositoryCount"]
        except Exception as e:
            logger.error(
                f"Error fetching count for stars:{min_stars}..{max_stars}: {e}"
            )
            raise

    async def resolve_ranges(
        self, base_query: str, sample_size: int
    ) -> List[Tuple[int, int, int]]:
        """
        Recursively resolves star brackets starting from max_stars down to 0.
        Returns a list of (min_stars, max_stars, count) ordered highest to lowest.
        """
        resolved_brackets = []
        cumulative_count = 0

        # We will use an explicit stack to traverse from highest stars down to lowest,
        # so we can stop exactly when we hit the sample_size!
        # Stack items: (min_stars, max_stars)
        stack = [(0, self.max_stars)]

        log = logger.bind(base_query=base_query, target_count=sample_size)
        log.debug("resolver_mapping_started")

        while stack and cumulative_count < sample_size:
            min_s, max_s = stack.pop()
            count = await self._get_count(base_query, min_s, max_s)

            if count == 0:
                continue

            if count <= self.threshold or min_s == max_s:
                # Bracket is safe!
                resolved_brackets.append((min_s, max_s, count))
                cumulative_count += count
                logger.debug(
                    "bracket_resolved",
                    bracket=f"stars:{min_s}..{max_s}",
                    count=count,
                    cumulative_total=f"{cumulative_count}/{sample_size}",
                )
            else:
                # Intelligent Bisection:
                # If we have a massive range like 0..1000000 with 5000 repos.
                # A blind midpoint is 500000. But we know most repos are near 0.
                # To aggressively prevent tiny fragments at the high end, we use a predictive log-weighted midpoint,
                # but fallback to binary search if the range is small.
                if max_s - min_s > 10000:
                    mid = (
                        min_s + (max_s - min_s) // 10
                    )  # Skewed bisection for power law
                else:
                    mid = (min_s + max_s) // 2

                # We want to process the HIGHEST stars first, so we push the lower half to the stack first!
                stack.append((min_s, mid))
                stack.append((mid + 1, max_s))

        return self._dp_consolidate(resolved_brackets)

    def _dp_consolidate(
        self, brackets: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int]]:
        """
        Dynamic Programming Consolidator.
        Given a strictly contiguous list of brackets (ordered high to low),
        finds the absolute mathematically optimal partitioning to minimize the number of bins,
        where each bin's total count <= threshold.
        """
        n = len(brackets)
        if n == 0:
            return []

        # dp[i] = minimum bins to pack brackets[i:]
        dp = [float("inf")] * (n + 1)
        dp[n] = 0

        # next_split[i] = the index j where the optimal bin starting at i ends
        next_split = [n] * n

        for i in range(n - 1, -1, -1):
            current_sum = 0
            for j in range(i, n):
                current_sum += brackets[j][2]
                if current_sum > self.threshold:
                    break
                if 1 + dp[j + 1] < dp[i]:
                    dp[i] = 1 + dp[j + 1]
                    next_split[i] = j + 1

        # Reconstruct the optimal bins
        consolidated = []
        i = 0
        while i < n:
            j = next_split[i]
            # Merge brackets from i to j-1
            # Since they are ordered high to low, max_stars is at i, min_stars is at j-1
            max_s = brackets[i][1]
            min_s = brackets[j - 1][0]
            total_count = sum(b[2] for b in brackets[i:j])
            consolidated.append((min_s, max_s, total_count))
            i = j

        logger.debug(
            "consolidation_completed",
            original_brackets=n,
            compressed_brackets=len(consolidated),
            compression_ratio=f"{(1 - len(consolidated) / n) * 100:.1f}%"
            if n > 0
            else "0%",
        )
        return consolidated

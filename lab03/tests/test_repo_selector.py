from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pipeline.funnel import FunnelTracker
from pipeline.http_client import GitHubClient
from pipeline.repo_selector import (
    filter_repositories_with_actions,
    search_candidates_by_stars,
)


class TestRepoSelector:
    async def test_search_candidates_by_stars_and_deduplication(self):
        client = MagicMock(spec=GitHubClient)

        async def mock_get(url: str, params: dict | None = None):
            query = params.get("q", "") if params else ""
            if "1000..1500" in query:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"full_name": "owner/repo1", "stargazers_count": 1200},
                            {"full_name": "owner/repo2", "stargazers_count": 1100},
                        ]
                    },
                    request=httpx.Request("GET", "https://api.github.com/search"),
                )
            # Second range overlaps repo2 and adds repo3
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"full_name": "owner/repo2", "stargazers_count": 1100},
                        {"full_name": "owner/repo3", "stargazers_count": 2000},
                    ]
                },
                request=httpx.Request("GET", "https://api.github.com/search"),
            )

        client.get = AsyncMock(side_effect=mock_get)

        results = await search_candidates_by_stars(
            client=client,
            star_ranges=["1000..1500", "1501..2500"],
            max_pages_per_range=1,
        )

        assert len(results) == 3
        names = [r["full_name"] for r in results]
        assert names == ["owner/repo1", "owner/repo2", "owner/repo3"]

    async def test_filter_repositories_with_actions(self):
        client = MagicMock(spec=GitHubClient)

        async def mock_get(url: str, params: dict | None = None):
            if "has-ci" in url:
                return httpx.Response(
                    200,
                    json={"total_count": 3},
                    request=httpx.Request("GET", "https://api.github.com" + url),
                )
            if "no-ci" in url:
                return httpx.Response(
                    200,
                    json={"total_count": 0},
                    request=httpx.Request("GET", "https://api.github.com" + url),
                )
            raise httpx.RequestError("404 error", request=httpx.Request("GET", url))

        client.get = AsyncMock(side_effect=mock_get)
        funnel = FunnelTracker()

        repos = [
            {"full_name": "owner/has-ci"},
            {"full_name": "owner/no-ci"},
            {"full_name": "owner/error-repo"},
        ]

        accepted = await filter_repositories_with_actions(client, repos, funnel=funnel)
        assert len(accepted) == 1
        assert accepted[0]["full_name"] == "owner/has-ci"
        assert len(funnel.stages) == 2

    async def test_search_candidates_with_qualifiers(self):
        client = MagicMock(spec=GitHubClient)
        recorded_queries = []

        async def mock_get(url: str, params: dict | None = None):
            query = params.get("q", "") if params else ""
            recorded_queries.append(query)
            return httpx.Response(
                200,
                json={"items": []},
                request=httpx.Request("GET", "https://api.github.com/search"),
            )

        client.get = AsyncMock(side_effect=mock_get)

        await search_candidates_by_stars(
            client=client,
            star_ranges=[">10000"],
            qualifiers=["archived:false", "mirror:false", "size:>1000"],
            max_pages_per_range=1,
        )

        assert len(recorded_queries) == 1
        assert recorded_queries[0] == "stars:>10000 archived:false mirror:false size:>1000"


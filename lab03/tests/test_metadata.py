from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from metricas.schemas import Repo
from pipeline.http_client import GitHubClient
from pipeline.metadata import (
    count_contributors,
    extract_last_page_number,
    fetch_repository_metadata,
)


class TestMetadataAndContributors:
    def test_extract_last_page_number_from_dict(self):
        links_dict = {
            "next": {"url": "https://api.github.com/repos/o/r/contributors?page=2", "rel": "next"},
            "last": {"url": "https://api.github.com/repos/o/r/contributors?page=87", "rel": "last"},
        }
        assert extract_last_page_number(links_dict) == 87

    def test_extract_last_page_number_from_string(self):
        raw_header = '<https://api.github.com/repos/o/r/contributors?page=125>; rel="last"'
        assert extract_last_page_number(raw_header) == 125

    def test_extract_last_page_number_invalid(self):
        assert extract_last_page_number(None) is None
        assert extract_last_page_number({}) is None
        assert extract_last_page_number("invalid string") is None

    async def test_count_contributors_with_link_header(self):
        client = MagicMock(spec=GitHubClient)
        resp = httpx.Response(
            200,
            headers={
                "Link": '<https://api.github.com/repos/o/r/contributors?per_page=1&anon=true&page=45>; rel="last"'
            },
            json=[{"id": 1}],
            request=httpx.Request("GET", "https://api.github.com/repos/o/r/contributors"),
        )
        client.get = AsyncMock(return_value=resp)

        count = await count_contributors(client, "owner", "repo")
        assert count == 45

    async def test_count_contributors_without_pagination(self):
        client = MagicMock(spec=GitHubClient)
        resp = httpx.Response(
            200,
            json=[{"id": 1}],
            request=httpx.Request("GET", "https://api.github.com/repos/o/r/contributors"),
        )
        client.get = AsyncMock(return_value=resp)

        count = await count_contributors(client, "owner", "repo")
        assert count == 1

    async def test_fetch_repository_metadata(self):
        client = MagicMock(spec=GitHubClient)
        # count_contributors mock response
        client.get = AsyncMock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                request=httpx.Request(
                    "GET", "https://api.github.com/repos/owner/repo/contributors"
                ),
            )
        )

        cached_info = {
            "stargazers_count": 5000,
            "language": "Python",
            "default_branch": "main",
            "created_at": "2020-01-01T00:00:00Z",
        }

        repo = await fetch_repository_metadata(
            client, "owner", "repo", cached_info=cached_info
        )
        assert isinstance(repo, Repo)
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.stars == 5000
        assert repo.language == "Python"
        assert repo.contributors_count == 1

    async def test_fetch_repository_details_graphql(self):
        from pipeline.metadata import fetch_repository_details_graphql

        client = MagicMock(spec=GitHubClient)
        # Mock contributor count GET
        client.get = AsyncMock(
            return_value=httpx.Response(
                200,
                headers={"Link": '<https://api.github.com/repos/pallets/flask/contributors?page=120>; rel="last"'},
                json=[{"id": 1}],
                request=httpx.Request("GET", "https://api.github.com/repos/pallets/flask/contributors"),
            )
        )
        # Mock GraphQL response
        client.graphql = AsyncMock(
            return_value={
                "data": {
                    "repository": {
                        "name": "flask",
                        "stargazerCount": 75000,
                        "createdAt": "2010-04-06T11:11:59Z",
                        "primaryLanguage": {"name": "Python"},
                        "defaultBranchRef": {"name": "main"},
                        "releases": {
                            "totalCount": 1,
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "tagName": "3.1.3",
                                    "publishedAt": "2026-02-19T05:01:30Z",
                                    "isPrerelease": False,
                                    "isDraft": False,
                                }
                            ],
                        },
                    }
                }
            }
        )

        repo, rels = await fetch_repository_details_graphql(client, "pallets", "flask")
        assert repo.name == "flask"
        assert repo.stars == 75000
        assert repo.language == "Python"
        assert repo.default_branch == "main"
        assert repo.contributors_count == 120
        assert len(rels) == 1
        assert rels[0].tag_name == "3.1.3"


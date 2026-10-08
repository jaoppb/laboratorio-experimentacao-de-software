"""Unit tests for metadata collection and contributor counting (Issue #30)."""

from unittest.mock import MagicMock

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

    def test_count_contributors_with_link_header(self):
        client = MagicMock(spec=GitHubClient)
        resp = httpx.Response(
            200,
            headers={
                "Link": '<https://api.github.com/repos/o/r/contributors?per_page=1&anon=true&page=45>; rel="last"'
            },
            json=[{"id": 1}],
            request=httpx.Request("GET", "https://api.github.com/repos/o/r/contributors"),
        )
        client.get.return_value = resp

        count = count_contributors(client, "owner", "repo")
        assert count == 45

    def test_count_contributors_without_pagination(self):
        client = MagicMock(spec=GitHubClient)
        resp = httpx.Response(
            200,
            json=[{"id": 1}],
            request=httpx.Request("GET", "https://api.github.com/repos/o/r/contributors"),
        )
        client.get.return_value = resp

        count = count_contributors(client, "owner", "repo")
        assert count == 1

    def test_fetch_repository_metadata(self):
        client = MagicMock(spec=GitHubClient)
        # count_contributors mock response
        client.get.return_value = httpx.Response(
            200,
            json=[{"id": 1}],
            request=httpx.Request("GET", "https://api.github.com/repos/owner/repo/contributors"),
        )

        cached_info = {
            "stargazers_count": 5000,
            "language": "Python",
            "default_branch": "main",
            "created_at": "2020-01-01T00:00:00Z",
        }

        repo = fetch_repository_metadata(client, "owner", "repo", cached_info=cached_info)
        assert isinstance(repo, Repo)
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.stars == 5000
        assert repo.language == "Python"
        assert repo.contributors_count == 1

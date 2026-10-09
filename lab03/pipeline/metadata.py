"""Repository metadata and contributor collection (Async)."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from metricas.schemas import Repo

if TYPE_CHECKING:
    from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)


def extract_last_page_number(link_header_or_dict: Any) -> int | None:
    """Extract the last page number from RFC 5988 Link header or parsed links dictionary."""
    if not link_header_or_dict:
        return None

    if isinstance(link_header_or_dict, dict):
        last_info = link_header_or_dict.get("last")
        if isinstance(last_info, dict) and "url" in last_info:
            parsed = urlparse(last_info["url"])
            qs = parse_qs(parsed.query)
            if "page" in qs and qs["page"]:
                try:
                    return int(qs["page"][0])
                except ValueError:
                    pass

    if isinstance(link_header_or_dict, str):
        match = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel=["\']last["\']', link_header_or_dict)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

    return None


async def count_contributors(client: GitHubClient, owner: str, repo: str) -> int:
    """Count repository contributors asynchronously using per_page=1&anon=true and Link header."""
    endpoint = f"/repos/{owner}/{repo}/contributors"
    params = {"per_page": 1, "anon": "true"}

    try:
        response = await client.get(endpoint, params=params)
    except Exception as exc:
        logger.warning("Could not fetch contributors for %s/%s: %s", owner, repo, exc)
        return 0

    if response.links:
        last_page = extract_last_page_number(response.links)
        if last_page is not None:
            return last_page

    raw_link = response.headers.get("Link")
    if raw_link:
        last_page = extract_last_page_number(raw_link)
        if last_page is not None:
            return last_page

    try:
        items = response.json()
        if isinstance(items, list):
            return len(items)
    except Exception:
        pass

    return 0


async def fetch_repository_metadata(
    client: GitHubClient,
    owner: str,
    repo: str,
    cached_info: dict[str, Any] | None = None,
) -> Repo:
    """Fetch all required metadata for a repository asynchronously."""
    info = cached_info
    if not info:
        endpoint = f"/repos/{owner}/{repo}"
        resp = await client.get(endpoint)
        info = resp.json()

    stars = info.get("stargazers_count", 0)
    language = info.get("language")
    default_branch = info.get("default_branch", "main")
    created_at = info.get("created_at")

    contributors = await count_contributors(client, owner, repo)

    return Repo(
        owner=owner,
        name=repo,
        default_branch=default_branch,
        stars=stars,
        language=language,
        created_at=created_at,
        contributors_count=contributors,
        metadata={"raw_info": info},
    )

"""Repository metadata and contributor collection.

Fulfills requirements of Issue #30 and guialab03.md:
- Collects stars, language, default_branch and repository age (created_at)
- Counts contributors using GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true
  extracting the total count from the last page number in the RFC 5988 Link header
"""

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

    # If it is httpx parsed links dict: {'last': {'url': '...page=42...', 'rel': 'last'}}
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

    # If it is raw string header: '<https://...?page=42>; rel="last"'
    if isinstance(link_header_or_dict, str):
        match = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel=["\']last["\']', link_header_or_dict)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

    return None


def count_contributors(client: GitHubClient, owner: str, repo: str) -> int:
    """Count repository contributors using per_page=1&anon=true and the Link header.

    Avoids downloading all contributor records by inspecting the 'last' page in the Link header.
    """
    endpoint = f"/repos/{owner}/{repo}/contributors"
    params = {"per_page": 1, "anon": "true"}

    try:
        response = client.get(endpoint, params=params)
    except Exception as exc:
        logger.warning("Could not fetch contributors for %s/%s: %s", owner, repo, exc)
        return 0

    # Check parsed links from response
    if response.links:
        last_page = extract_last_page_number(response.links)
        if last_page is not None:
            return last_page

    # Fallback: check raw Link header
    raw_link = response.headers.get("Link")
    if raw_link:
        last_page = extract_last_page_number(raw_link)
        if last_page is not None:
            return last_page

    # If no pagination link exists, check if any items were returned
    try:
        items = response.json()
        if isinstance(items, list):
            return len(items)
    except Exception:
        pass

    return 0


def fetch_repository_metadata(
    client: GitHubClient,
    owner: str,
    repo: str,
    cached_info: dict[str, Any] | None = None,
) -> Repo:
    """Fetch all required metadata for a repository.

    Collects: stars, language, default_branch, created_at, and contributors_count.
    """
    info = cached_info
    if not info:
        endpoint = f"/repos/{owner}/{repo}"
        resp = client.get(endpoint)
        info = resp.json()

    stars = info.get("stargazers_count", 0)
    language = info.get("language")
    default_branch = info.get("default_branch", "main")
    created_at = info.get("created_at")

    contributors = count_contributors(client, owner, repo)

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

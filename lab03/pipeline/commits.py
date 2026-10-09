"""Collection of the commits included in each release (Async compare between releases)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from metricas.schemas import Commit, Release

if TYPE_CHECKING:
    from pipeline.http_client import GitHubClient
    from pipeline.releases import WindowReleases

logger = logging.getLogger(__name__)

PER_PAGE = 100


class ComparisonStatus(str, Enum):
    """Outcome of collecting the commits of one release."""

    OK = "ok"
    FIRST_RELEASE = "first_release"
    NOT_FOUND = "not_found"


@dataclass
class ReleaseCommits:
    """Commits included in a release, compared against the previous release."""

    release: Release
    previous: Release | None
    status: ComparisonStatus
    commits: list[Commit] = field(default_factory=list)

    @property
    def commits_or_none(self) -> list[Commit] | None:
        """Commits for the lead time functions; None when the release was skipped."""
        return self.commits if self.status == ComparisonStatus.OK else None


def parse_commit(payload: dict[str, Any]) -> Commit:
    """Convert a commit JSON object into a `Commit`, dated by `commit.author.date`."""
    return Commit(
        sha=payload["sha"],
        committed_at=payload["commit"]["author"]["date"],
        message=payload["commit"].get("message", ""),
    )


def _ref(tag_name: str) -> str:
    """URL-encode a tag name for use in the compare path."""
    return quote(tag_name, safe="/")


async def fetch_compare_commits(
    client: GitHubClient, owner: str, repo: str, base: str, head: str
) -> list[Commit]:
    """Fetch all commits in `compare/{base}...{head}`, paginating past 250 commits."""
    url = f"/repos/{owner}/{repo}/compare/{_ref(base)}...{_ref(head)}"
    commits: list[Commit] = []
    total: int | None = None
    page = 1

    while True:
        resp = await client.get(url, params={"per_page": PER_PAGE, "page": page})
        data = resp.json()
        total = data.get("total_commits", total)
        batch = data.get("commits", [])
        commits.extend(parse_commit(c) for c in batch)
        if (
            not batch
            or len(batch) < PER_PAGE
            or (total is not None and len(commits) >= total)
        ):
            break
        page += 1

    if total is not None and len(commits) < total:
        logger.warning(
            "%s/%s compare %s...%s returned %d of %d commits",
            owner,
            repo,
            base,
            head,
            len(commits),
            total,
        )
    return commits


async def _compare_one(
    client: GitHubClient,
    owner: str,
    repo: str,
    previous: Release | None,
    release: Release,
) -> ReleaseCommits:
    if previous is None:
        return ReleaseCommits(release, None, ComparisonStatus.FIRST_RELEASE)
    try:
        commits = await fetch_compare_commits(
            client, owner, repo, previous.tag_name, release.tag_name
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
        logger.warning(
            "%s/%s compare %s...%s returned 404; release skipped",
            owner,
            repo,
            previous.tag_name,
            release.tag_name,
        )
        return ReleaseCommits(release, previous, ComparisonStatus.NOT_FOUND)
    return ReleaseCommits(release, previous, ComparisonStatus.OK, commits)


async def collect_release_commits(
    client: GitHubClient,
    owner: str,
    repo: str,
    window: WindowReleases,
) -> list[ReleaseCommits]:
    """Collect commits of in-window releases against their predecessor in parallel."""
    ordered = window.with_anchor()
    offset = 1 if window.anchor is not None else 0

    tasks = [
        _compare_one(
            client,
            owner,
            repo,
            ordered[i - 1] if i > 0 else None,
            ordered[i],
        )
        for i in range(offset, len(ordered))
    ]

    if not tasks:
        return []

    return await asyncio.gather(*tasks)


def count_by_status(results: Sequence[ReleaseCommits]) -> dict[ComparisonStatus, int]:
    """Count releases per comparison status."""
    counts = dict.fromkeys(ComparisonStatus, 0)
    for result in results:
        counts[result.status] += 1
    return counts

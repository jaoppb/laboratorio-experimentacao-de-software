"""Collection of releases and tags (deploy units) from the GitHub REST API (Async)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from metricas.schemas import Release, _parse_datetime

if TYPE_CHECKING:
    from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)

PER_PAGE = 100


def parse_release(payload: dict[str, Any]) -> Release | None:
    """Convert a release JSON object from the API into a `Release`."""
    if payload.get("draft") or not payload.get("published_at"):
        return None
    return Release(
        tag_name=payload["tag_name"],
        published_at=payload["published_at"],
        draft=False,
        prerelease=bool(payload.get("prerelease", False)),
    )


async def fetch_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    window_start: datetime | str | None = None,
) -> list[Release]:
    """Fetch the published (non-draft) releases of a repository, oldest first."""
    start = _parse_datetime(window_start)
    releases: list[Release] = []

    async for response in client.get_paginated(
        f"/repos/{owner}/{repo}/releases", params={"per_page": PER_PAGE}
    ):
        reached_anchor = False
        for item in response.json():
            release = parse_release(item)
            if release is None:
                continue
            releases.append(release)
            if (
                start is not None
                and not release.prerelease
                and release.published_at < start
            ):
                reached_anchor = True
        if reached_anchor:
            break

    return sorted(releases, key=lambda r: r.published_at)


async def fetch_tags(
    client: GitHubClient,
    owner: str,
    repo: str,
    max_tags: int | None = None,
) -> list[Release]:
    """Fetch the tags of a repository as deploy units (RQ 07 variant), oldest first."""
    tags: list[tuple[str, str]] = []
    async for response in client.get_paginated(
        f"/repos/{owner}/{repo}/tags", params={"per_page": PER_PAGE}
    ):
        for item in response.json():
            tags.append((item["name"], item["commit"]["sha"]))
            if max_tags is not None and len(tags) >= max_tags:
                break
        if max_tags is not None and len(tags) >= max_tags:
            break

    dates_by_sha: dict[str, datetime] = {}
    result: list[Release] = []
    for name, sha in tags:
        if sha not in dates_by_sha:
            resp = await client.get(f"/repos/{owner}/{repo}/commits/{sha}")
            commit = resp.json()
            dates_by_sha[sha] = _parse_datetime(commit["commit"]["author"]["date"])  # type: ignore
        result.append(Release(tag_name=name, published_at=dates_by_sha[sha]))

    return sorted(result, key=lambda r: r.published_at)


def deploy_units(
    releases: Sequence[Release], include_prerelease: bool = False
) -> list[Release]:
    """Filter releases by the deploy unit definition, oldest first."""
    return sorted(
        (
            r
            for r in releases
            if not r.draft and (include_prerelease or not r.prerelease)
        ),
        key=lambda r: r.published_at,
    )


@dataclass
class WindowReleases:
    """Deploy units inside the observation window and the one right before it."""

    in_window: list[Release] = field(default_factory=list)
    anchor: Release | None = None

    @property
    def count(self) -> int:
        """Number of valid deploys in the window."""
        return len(self.in_window)

    def with_anchor(self) -> list[Release]:
        """Anchor (if any) followed by the in-window releases, oldest first."""
        return ([self.anchor] if self.anchor else []) + self.in_window


def filter_window(
    releases: Sequence[Release],
    window_start: datetime | str,
    window_end: datetime | str,
    include_prerelease: bool = False,
) -> WindowReleases:
    """Select the deploy units inside [window_start, window_end]."""
    start = _parse_datetime(window_start)
    end = _parse_datetime(window_end)
    units = deploy_units(releases, include_prerelease=include_prerelease)

    before = [r for r in units if r.published_at < start]  # type: ignore
    in_window = [r for r in units if start <= r.published_at <= end]  # type: ignore
    return WindowReleases(in_window=in_window, anchor=before[-1] if before else None)


def count_valid_releases(
    releases: Sequence[Release],
    window_start: datetime | str,
    window_end: datetime | str,
) -> int:
    """Count published, non-prerelease releases inside the window (>= 5 criterion)."""
    return filter_window(releases, window_start, window_end).count

"""Collection of releases and tags (deploy units) from the GitHub REST API."""

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
    """Convert a release JSON object from the API into a `Release`.

    Drafts are discarded (they are not deploys and have no `published_at`).
    """
    if payload.get("draft") or not payload.get("published_at"):
        return None
    return Release(
        tag_name=payload["tag_name"],
        published_at=payload["published_at"],
        draft=False,
        prerelease=bool(payload.get("prerelease", False)),
    )


def fetch_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    window_start: datetime | str | None = None,
) -> list[Release]:
    """Fetch the published (non-draft) releases of a repository, oldest first.

    The API lists releases newest first. When `window_start` is given, pagination
    stops after the page that contains the first stable release published before
    the window: it is the anchor needed to compute the lead time of the first
    release of the window, and every older release is irrelevant. Without
    `window_start`, the whole history is fetched.
    """
    start = _parse_datetime(window_start)
    releases: list[Release] = []

    for response in client.get_paginated(
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


def fetch_tags(
    client: GitHubClient,
    owner: str,
    repo: str,
    max_tags: int | None = None,
) -> list[Release]:
    """Fetch the tags of a repository as deploy units (RQ 07 variant), oldest first.

    Tags carry no date, so each tag is dated by `commit.author.date` of the commit
    it points to (one extra request per distinct commit, cached on disk). Tags are
    returned as `Release` objects so the same metric functions apply to them.
    """
    tags: list[tuple[str, str]] = []
    for response in client.get_paginated(
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
            commit = client.get(f"/repos/{owner}/{repo}/commits/{sha}").json()
            dates_by_sha[sha] = _parse_datetime(commit["commit"]["author"]["date"])
        result.append(Release(tag_name=name, published_at=dates_by_sha[sha]))

    return sorted(result, key=lambda r: r.published_at)


def deploy_units(
    releases: Sequence[Release], include_prerelease: bool = False
) -> list[Release]:
    """Filter releases by the deploy unit definition, oldest first.

    Main definition: published releases only. Variant (RQ 07): releases and
    pre-releases.
    """
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
        """Number of valid deploys in the window (used by the selection funnel)."""
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
    """Select the deploy units inside [window_start, window_end].

    The latest deploy unit published before the window is kept as `anchor`,
    because the lead time of the first release of the window is measured
    against it. If there is no anchor, the first release of the window is the
    first release in the repository history.
    """
    start = _parse_datetime(window_start)
    end = _parse_datetime(window_end)
    units = deploy_units(releases, include_prerelease=include_prerelease)

    before = [r for r in units if r.published_at < start]
    in_window = [r for r in units if start <= r.published_at <= end]
    return WindowReleases(in_window=in_window, anchor=before[-1] if before else None)


def count_valid_releases(
    releases: Sequence[Release],
    window_start: datetime | str,
    window_end: datetime | str,
) -> int:
    """Count published, non-prerelease releases inside the window (≥ 5 criterion)."""
    return filter_window(releases, window_start, window_end).count

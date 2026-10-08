"""Calculation of DORA lead time for changes, variants (a) per release and (b) per commit."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metricas.schemas import Commit, Release

SECONDS_PER_HOUR = 3600.0


@dataclass
class LeadTimeResult:
    """Lead time of a repository in both mandatory variants, in hours."""

    median_a_hours: float | None
    median_b_hours: float | None
    release_lead_times_hours: list[float] = field(default_factory=list)
    commit_lead_times_hours: list[float] = field(default_factory=list)
    evaluated_releases: int = 0
    releases_without_commits: int = 0
    skipped_releases: int = 0


def _hours_between(release: Release, commit: Commit) -> float:
    """`release date − commit date` in hours, floored at 0 (author dates may be skewed)."""
    seconds = (release.published_at - commit.committed_at).total_seconds()
    return max(0.0, seconds / SECONDS_PER_HOUR)


def release_lead_time(release: Release, commits: Sequence[Commit]) -> float | None:
    """Variant (a): `date of R − date of the oldest commit included in R`, in hours.

    Returns None when the release has no new commits.
    """
    if not commits:
        return None
    oldest = min(commits, key=lambda c: c.committed_at)
    return _hours_between(release, oldest)


def commit_lead_times(release: Release, commits: Sequence[Commit]) -> list[float]:
    """Variant (b): `date of R − date of each commit included in R`, in hours."""
    return [_hours_between(release, c) for c in commits]


def calculate_lead_time(
    releases: Sequence[tuple[Release, Sequence[Commit] | None]],
) -> LeadTimeResult:
    """Calculate lead time (a) and (b) for a repository.

    Each item pairs a release with the commits included in it (compare against
    the previous release). `None` commits mean the release could not be
    evaluated (first release in history, or compare returned 404) and it is
    counted as skipped. A release with an empty commit list has no new commits:
    it contributes to neither variant.

    - (a) median, across releases, of the per-release lead time.
    - (b) median of the lead times of all commits of all releases.
    """
    release_values: list[float] = []
    commit_values: list[float] = []
    without_commits = 0
    skipped = 0

    for release, commits in releases:
        if commits is None:
            skipped += 1
            continue
        value = release_lead_time(release, commits)
        if value is None:
            without_commits += 1
            continue
        release_values.append(value)
        commit_values.extend(commit_lead_times(release, commits))

    return LeadTimeResult(
        median_a_hours=float(statistics.median(release_values))
        if release_values
        else None,
        median_b_hours=float(statistics.median(commit_values))
        if commit_values
        else None,
        release_lead_times_hours=release_values,
        commit_lead_times_hours=commit_values,
        evaluated_releases=len(release_values),
        releases_without_commits=without_commits,
        skipped_releases=skipped,
    )

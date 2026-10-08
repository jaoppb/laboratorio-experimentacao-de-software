"""Tests for lead time (a) and (b) calculation (metricas.lead_time)."""

import pytest
from metricas.lead_time import (
    calculate_lead_time,
    commit_lead_times,
    release_lead_time,
)
from metricas.schemas import Commit, Release

DAY = 24.0


@pytest.fixture
def release_v1_1():
    """Example from the guide: v1.1 published on 15/03 with commits of 02/03, 10/03 and 14/03."""
    release = Release(tag_name="v1.1", published_at="2024-03-15T00:00:00Z")
    commits = [
        Commit(sha="c3", committed_at="2024-03-14T00:00:00Z", message="fix: typo"),
        Commit(sha="c1", committed_at="2024-03-02T00:00:00Z", message="feat: a"),
        Commit(sha="c2", committed_at="2024-03-10T00:00:00Z", message="feat: b"),
    ]
    return release, commits


@pytest.fixture
def release_v1_2():
    """Second release: v1.2 published on 20/03 with commits of 18/03 and 19/03."""
    release = Release(tag_name="v1.2", published_at="2024-03-20T00:00:00Z")
    commits = [
        Commit(sha="d1", committed_at="2024-03-18T00:00:00Z"),
        Commit(sha="d2", committed_at="2024-03-19T00:00:00Z"),
    ]
    return release, commits


def test_guide_example_variant_a(release_v1_1):
    """(a) lead time of v1.1 = 15/03 − 02/03 = 13 days, regardless of commit order."""
    release, commits = release_v1_1
    assert release_lead_time(release, commits) == pytest.approx(13 * DAY)


def test_guide_example_variant_b(release_v1_1):
    """(b) v1.1 contributes 13, 5 and 1 days."""
    release, commits = release_v1_1
    values = sorted(commit_lead_times(release, commits), reverse=True)
    assert values == pytest.approx([13 * DAY, 5 * DAY, 1 * DAY])


def test_repository_medians_across_releases(release_v1_1, release_v1_2):
    """(a) is the median per release; (b) pools the commits of all releases."""
    result = calculate_lead_time([release_v1_1, release_v1_2])

    # (a): v1.1 = 13 days, v1.2 = 2 days → median 7.5 days
    assert result.release_lead_times_hours == pytest.approx([13 * DAY, 2 * DAY])
    assert result.median_a_hours == pytest.approx(7.5 * DAY)
    # (b): [13, 5, 1, 2, 1] days → median 2 days
    assert sorted(result.commit_lead_times_hours) == pytest.approx(
        [1 * DAY, 1 * DAY, 2 * DAY, 5 * DAY, 13 * DAY]
    )
    assert result.median_b_hours == pytest.approx(2 * DAY)
    assert result.evaluated_releases == 2
    assert result.releases_without_commits == 0
    assert result.skipped_releases == 0


def test_forgotten_old_commit_inflates_a_but_not_b():
    """One old commit makes (a) explode but barely moves (b)."""
    release = Release(tag_name="v2.0", published_at="2024-06-01T00:00:00Z")
    commits = [Commit(sha="old", committed_at="2024-01-01T00:00:00Z")] + [
        Commit(sha=f"n{i}", committed_at="2024-05-31T00:00:00Z") for i in range(9)
    ]
    result = calculate_lead_time([(release, commits)])
    assert result.median_a_hours == pytest.approx(152 * DAY)
    assert result.median_b_hours == pytest.approx(1 * DAY)


def test_release_without_new_commits_is_not_evaluated(release_v1_1):
    """A release with an empty compare contributes to neither variant."""
    empty = Release(tag_name="v1.1.1", published_at="2024-03-16T00:00:00Z")
    assert release_lead_time(empty, []) is None
    assert commit_lead_times(empty, []) == []

    result = calculate_lead_time([release_v1_1, (empty, [])])
    assert result.median_a_hours == pytest.approx(13 * DAY)
    assert result.evaluated_releases == 1
    assert result.releases_without_commits == 1
    assert len(result.commit_lead_times_hours) == 3


def test_single_release_has_no_lead_time():
    """A repository with a single release has no previous release to compare against."""
    only = Release(tag_name="v1.0", published_at="2024-03-01T00:00:00Z")
    result = calculate_lead_time([(only, None)])
    assert result.median_a_hours is None
    assert result.median_b_hours is None
    assert result.evaluated_releases == 0
    assert result.skipped_releases == 1


def test_release_skipped_by_404_is_counted(release_v1_1):
    """A release whose compare returned 404 is ignored and counted as skipped."""
    missing = Release(tag_name="v1.2-deleted", published_at="2024-03-20T00:00:00Z")
    result = calculate_lead_time([release_v1_1, (missing, None)])
    assert result.median_a_hours == pytest.approx(13 * DAY)
    assert result.median_b_hours == pytest.approx(5 * DAY)
    assert result.skipped_releases == 1
    assert result.evaluated_releases == 1


def test_no_releases():
    result = calculate_lead_time([])
    assert result.median_a_hours is None
    assert result.median_b_hours is None
    assert result.evaluated_releases == 0


def test_commit_dated_after_release_is_floored_at_zero():
    """Author dates can be skewed (rebase, wrong clock); negative values become 0."""
    release = Release(tag_name="v1", published_at="2024-03-15T00:00:00Z")
    commits = [Commit(sha="x", committed_at="2024-03-15T06:00:00Z")]
    assert release_lead_time(release, commits) == 0.0
    assert commit_lead_times(release, commits) == [0.0]


def test_timezone_offsets_are_respected():
    """Dates in different offsets are compared as absolute instants."""
    release = Release(tag_name="v1", published_at="2024-03-15T12:00:00Z")
    commits = [Commit(sha="x", committed_at="2024-03-15T09:00:00-03:00")]
    assert release_lead_time(release, commits) == pytest.approx(0.0)
    commits = [Commit(sha="y", committed_at="2024-03-15T09:00:00+00:00")]
    assert release_lead_time(release, commits) == pytest.approx(3.0)

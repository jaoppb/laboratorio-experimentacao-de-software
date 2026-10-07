"""Tests for CFR (a) and Recovery Time calculation (metricas.stability and schemas)."""

from datetime import datetime

import pytest
from metricas.schemas import Commit, Release, Repo, WorkflowRun
from metricas.stability import (
    ConclusionCategory,
    calculate_cfr_a,
    calculate_recovery_time,
    classify_conclusion,
)


def test_schemas_dataclasses_and_datetime_parsing():
    """Verify that schemas parse ISO 8601 strings and maintain timezone awareness."""
    run = WorkflowRun(
        workflow_id="ci-test",
        conclusion="success",
        run_started_at="2024-03-01T10:00:00Z",
        updated_at="2024-03-01T10:05:00+00:00",
    )
    assert isinstance(run.run_started_at, datetime)
    assert run.run_started_at.tzinfo is not None
    assert isinstance(run.updated_at, datetime)
    assert run.updated_at.tzinfo is not None

    repo = Repo(owner="octocat", name="hello-world", stars=42)
    assert repo.owner == "octocat"
    assert repo.default_branch == "main"

    rel = Release(tag_name="v1.0.0", published_at="2024-03-01T12:00:00Z")
    assert isinstance(rel.published_at, datetime)

    commit = Commit(
        sha="abc1234", committed_at="2024-03-01T09:00:00Z", message="feat: initial"
    )
    assert isinstance(commit.committed_at, datetime)

    # Test already aware and naive datetime objects
    dt_naive = datetime(2024, 1, 1, 12, 0)  # noqa: DTZ001
    run_dt = WorkflowRun(
        workflow_id=1,
        conclusion="success",
        run_started_at=dt_naive,
        updated_at=run.updated_at,
    )
    assert run_dt.run_started_at.tzinfo is not None

    # Test error cases
    with pytest.raises(TypeError):
        WorkflowRun(
            workflow_id=1,
            conclusion="success",
            run_started_at=12345,  # type: ignore
            updated_at=run.updated_at,
        )

    with pytest.raises(ValueError):
        Release(tag_name="v1", published_at=None)  # type: ignore

    with pytest.raises(ValueError):
        Commit(sha="abc", committed_at=None)  # type: ignore

    with pytest.raises(ValueError):
        WorkflowRun(
            workflow_id=1,
            conclusion="success",
            run_started_at=None,  # type: ignore
            updated_at=None,  # type: ignore
        )


def test_classify_conclusion():
    """Verify classification matches the specification table in guialab03."""
    # Successes
    assert classify_conclusion("success") == ConclusionCategory.SUCCESS
    assert classify_conclusion("SUCCESS") == ConclusionCategory.SUCCESS

    # Failures
    assert classify_conclusion("failure") == ConclusionCategory.FAILURE
    assert classify_conclusion("timed_out") == ConclusionCategory.FAILURE
    assert classify_conclusion("startup_failure") == ConclusionCategory.FAILURE

    # Ignored
    assert classify_conclusion("cancelled") == ConclusionCategory.IGNORED
    assert classify_conclusion("skipped") == ConclusionCategory.IGNORED
    assert classify_conclusion("neutral") == ConclusionCategory.IGNORED
    assert classify_conclusion("action_required") == ConclusionCategory.IGNORED
    assert classify_conclusion("stale") == ConclusionCategory.IGNORED
    assert classify_conclusion("") == ConclusionCategory.IGNORED
    assert classify_conclusion(None) == ConclusionCategory.IGNORED
    assert classify_conclusion("in_progress") == ConclusionCategory.IGNORED


def test_cfr_a_standard_ratio():
    """Verify CFR (a) = failures / (failures + successes)."""
    runs = [
        WorkflowRun(
            workflow_id=1,
            conclusion="success",
            run_started_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:05:00Z",
        ),
        WorkflowRun(
            workflow_id=1,
            conclusion="success",
            run_started_at="2024-01-01T01:00:00Z",
            updated_at="2024-01-01T01:05:00Z",
        ),
        WorkflowRun(
            workflow_id=1,
            conclusion="failure",
            run_started_at="2024-01-01T02:00:00Z",
            updated_at="2024-01-01T02:05:00Z",
        ),
        WorkflowRun(
            workflow_id=1,
            conclusion="timed_out",
            run_started_at="2024-01-01T03:00:00Z",
            updated_at="2024-01-01T03:05:00Z",
        ),
    ]
    # 2 failures, 2 successes -> 2 / 4 = 0.5
    assert calculate_cfr_a(runs) == pytest.approx(0.5)


def test_cfr_a_zero_valid_runs():
    """Verify CFR (a) returns None when there are no valid runs."""
    assert calculate_cfr_a([]) is None

    ignored_only = [
        WorkflowRun(
            workflow_id=1,
            conclusion="cancelled",
            run_started_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:05:00Z",
        ),
        WorkflowRun(
            workflow_id=1,
            conclusion="skipped",
            run_started_at="2024-01-01T01:00:00Z",
            updated_at="2024-01-01T01:05:00Z",
        ),
    ]
    assert calculate_cfr_a(ignored_only) is None


def test_cfr_a_edge_cases():
    """Verify 0.0 for 100% successes and 1.0 for 100% failures."""
    all_success = [
        WorkflowRun(
            workflow_id=1,
            conclusion="success",
            run_started_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:05:00Z",
        ),
    ]
    assert calculate_cfr_a(all_success) == 0.0

    all_failure = [
        WorkflowRun(
            workflow_id=1,
            conclusion="startup_failure",
            run_started_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:05:00Z",
        ),
    ]
    assert calculate_cfr_a(all_failure) == 1.0


def test_recovery_time_course_example():
    """Verify reproduction of exact 1h20 example from guialab03 section 5 (RQ 04).

    Workflow `CI`, branch `main`:
    09:00: success
    10:00: failure <- episode start
    10:30: failure (same episode)
    11:15: success <- end of episode (ended at 11:20)
    Duration: 11:20 - 10:00 = 1h20 = 80 min = 1.3333 hours.
    """
    runs = [
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T09:00:00Z",
            updated_at="2024-03-01T09:10:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:08:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:30:00Z",
            updated_at="2024-03-01T10:35:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T11:15:00Z",
            updated_at="2024-03-01T11:20:00Z",
        ),
    ]

    result = calculate_recovery_time(runs)

    assert result.total_episodes == 1
    assert result.resolved_episodes == 1
    assert result.censored_episodes == 0
    assert result.censored_ratio == 0.0
    # 1h20 = 80 / 60 = 1.3333...
    assert result.median_hours is not None
    assert result.median_hours == pytest.approx(80.0 / 60.0, rel=1e-3)
    assert result.durations_hours == [pytest.approx(80.0 / 60.0, rel=1e-3)]


def test_recovery_time_ignores_cancelled_and_skipped():
    """Verify cancelled and skipped runs inside an active episode do not break the episode."""
    runs = [
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="cancelled",
            run_started_at="2024-03-01T10:15:00Z",
            updated_at="2024-03-01T10:20:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="skipped",
            run_started_at="2024-03-01T10:30:00Z",
            updated_at="2024-03-01T10:35:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T11:00:00Z",
            updated_at="2024-03-01T11:00:00Z",
        ),
    ]

    result = calculate_recovery_time(runs)
    assert result.resolved_episodes == 1
    assert result.censored_episodes == 0
    # 11:00 - 10:00 = 1.0 hour
    assert result.median_hours == pytest.approx(1.0)


def test_recovery_time_censored_episode():
    """Verify an episode that is never recovered within the window is counted as censored."""
    runs = [
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T09:00:00Z",
            updated_at="2024-03-01T09:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:30:00Z",
            updated_at="2024-03-01T10:35:00Z",
        ),
    ]

    result = calculate_recovery_time(runs)
    assert result.total_episodes == 1
    assert result.resolved_episodes == 0
    assert result.censored_episodes == 1
    assert result.censored_ratio == 1.0
    assert result.median_hours is None


def test_recovery_time_multiple_episodes_and_median():
    """Verify median calculation across multiple episodes in a single workflow."""
    runs = [
        # Episode 1: 10:00 to 11:00 = 1.0 hour
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T10:55:00Z",
            updated_at="2024-03-01T11:00:00Z",
        ),
        # Episode 2: 12:00 to 15:00 = 3.0 hours
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T12:00:00Z",
            updated_at="2024-03-01T12:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T14:55:00Z",
            updated_at="2024-03-01T15:00:00Z",
        ),
        # Episode 3: 16:00 to 18:00 = 2.0 hours
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T16:00:00Z",
            updated_at="2024-03-01T16:05:00Z",
        ),
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T17:55:00Z",
            updated_at="2024-03-01T18:00:00Z",
        ),
        # Episode 4 (censored)
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T20:00:00Z",
            updated_at="2024-03-01T20:05:00Z",
        ),
    ]

    result = calculate_recovery_time(runs)
    # 3 resolved episodes: [1.0, 3.0, 2.0] -> sorted [1.0, 2.0, 3.0] -> median 2.0
    assert result.resolved_episodes == 3
    assert result.censored_episodes == 1
    assert result.total_episodes == 4
    assert result.censored_ratio == 0.25
    assert result.median_hours == pytest.approx(2.0)


def test_recovery_time_multiple_workflows_isolation():
    """Verify episodes are tracked independently per workflow and aggregated for repository median."""
    runs = [
        # Workflow CI: failure at 10:00, success at 11:00 -> 1.0 hour
        WorkflowRun(
            workflow_id="CI",
            conclusion="failure",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:05:00Z",
        ),
        # Workflow Deploy: failure at 10:15, success at 12:15 -> 2.0 hours
        WorkflowRun(
            workflow_id="Deploy",
            conclusion="failure",
            run_started_at="2024-03-01T10:15:00Z",
            updated_at="2024-03-01T10:20:00Z",
        ),
        # CI succeeds (must NOT close Deploy's failure)
        WorkflowRun(
            workflow_id="CI",
            conclusion="success",
            run_started_at="2024-03-01T10:55:00Z",
            updated_at="2024-03-01T11:00:00Z",
        ),
        # Deploy succeeds
        WorkflowRun(
            workflow_id="Deploy",
            conclusion="success",
            run_started_at="2024-03-01T12:10:00Z",
            updated_at="2024-03-01T12:15:00Z",
        ),
    ]

    result = calculate_recovery_time(runs)
    assert result.resolved_episodes == 2
    assert result.censored_episodes == 0
    # Durations are [1.0, 2.0], median = 1.5
    assert result.median_hours == pytest.approx(1.5)


def test_recovery_time_empty_or_all_successes():
    """Verify behavior when repository has 0 runs or only successes."""
    res_empty = calculate_recovery_time([])
    assert res_empty.total_episodes == 0
    assert res_empty.censored_ratio == 0.0
    assert res_empty.median_hours is None

    res_successes = calculate_recovery_time(
        [
            WorkflowRun(
                workflow_id="CI",
                conclusion="success",
                run_started_at="2024-03-01T10:00:00Z",
                updated_at="2024-03-01T10:05:00Z",
            ),
            WorkflowRun(
                workflow_id="CI",
                conclusion="success",
                run_started_at="2024-03-01T11:00:00Z",
                updated_at="2024-03-01T11:05:00Z",
            ),
        ]
    )
    assert res_successes.total_episodes == 0
    assert res_successes.censored_ratio == 0.0
    assert res_successes.median_hours is None

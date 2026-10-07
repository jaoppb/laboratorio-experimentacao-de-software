"""Calculation of DORA stability metrics: Change Failure Rate (CFR a) and Recovery Time."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metricas.schemas import WorkflowRun


class ConclusionCategory(str, Enum):
    """Categorized status of a workflow run according to Lab03 specifications."""

    SUCCESS = "success"
    FAILURE = "failure"
    IGNORED = "ignored"


def classify_conclusion(conclusion: str | None) -> ConclusionCategory:
    """Classify workflow run conclusion according to the Lab03 specification table.

    - SUCCESS: 'success'
    - FAILURE: 'failure', 'timed_out', 'startup_failure'
    - IGNORED: 'cancelled', 'skipped', 'neutral', 'action_required', 'stale', empty/None (in-progress)
    """
    if conclusion is None:
        return ConclusionCategory.IGNORED

    normalized = conclusion.strip().lower()
    if normalized == "success":
        return ConclusionCategory.SUCCESS
    if normalized in {"failure", "timed_out", "startup_failure"}:
        return ConclusionCategory.FAILURE
    return ConclusionCategory.IGNORED


def calculate_cfr_a(runs: Sequence[WorkflowRun]) -> float | None:
    """Calculate Change Failure Rate variant (a) - CI Proxy.

    Formula: falhas / (falhas + sucessos)
    Runs with ignored conclusions (e.g. cancelled, skipped) are excluded.
    Returns None if there are 0 valid (success or failure) runs.
    """
    failures = 0
    successes = 0

    for run in runs:
        cat = classify_conclusion(run.conclusion)
        if cat == ConclusionCategory.FAILURE:
            failures += 1
        elif cat == ConclusionCategory.SUCCESS:
            successes += 1

    total = failures + successes
    if total == 0:
        return None
    return failures / total


@dataclass
class RecoveryResult:
    """Detailed result of Recovery Time calculation for a repository."""

    median_hours: float | None
    censored_ratio: float
    total_episodes: int
    resolved_episodes: int
    censored_episodes: int
    durations_hours: list[float]


def calculate_recovery_time(runs: Sequence[WorkflowRun]) -> RecoveryResult:
    """Calculate recovery time and proportion of censored failure episodes.

    Per-workflow logic:
    - Runs of the same workflow are sorted chronologically by `run_started_at`.
    - Ignored runs (e.g. cancelled, skipped) are bypassed without altering episode state.
    - A failure episode starts at the first failure.
    - Subsequent consecutive failures belong to the same episode.
    - An episode ends at the next successful run of that workflow.
    - Episode duration = success.updated_at - first_failure.run_started_at (in hours).
    - If a failure episode is never resolved before the history ends, it is counted as censored.

    Repository aggregation:
    - Median of all resolved episode durations across all workflows.
    - Proportion of censored episodes = censored_episodes / total_episodes.
    """
    if not runs:
        return RecoveryResult(
            median_hours=None,
            censored_ratio=0.0,
            total_episodes=0,
            resolved_episodes=0,
            censored_episodes=0,
            durations_hours=[],
        )

    # Group runs by workflow_id
    grouped_by_workflow: dict[int | str, list[WorkflowRun]] = defaultdict(list)
    for run in runs:
        grouped_by_workflow[run.workflow_id].append(run)

    all_durations: list[float] = []
    censored_count = 0

    for wf_runs in grouped_by_workflow.values():
        # Sort chronologically by run_started_at
        sorted_runs = sorted(wf_runs, key=lambda r: r.run_started_at)

        first_failure_started_at = None

        for run in sorted_runs:
            status = classify_conclusion(run.conclusion)
            if status == ConclusionCategory.IGNORED:
                continue

            if status == ConclusionCategory.FAILURE:
                if first_failure_started_at is None:
                    first_failure_started_at = run.run_started_at
            elif (
                status == ConclusionCategory.SUCCESS
                and first_failure_started_at is not None
            ):
                duration_seconds = (
                    run.updated_at - first_failure_started_at
                ).total_seconds()
                duration_hours = max(0.0, duration_seconds / 3600.0)
                all_durations.append(duration_hours)
                first_failure_started_at = None

        if first_failure_started_at is not None:
            censored_count += 1

    total_episodes = len(all_durations) + censored_count
    censored_ratio = (censored_count / total_episodes) if total_episodes > 0 else 0.0
    median_hours = float(statistics.median(all_durations)) if all_durations else None

    return RecoveryResult(
        median_hours=median_hours,
        censored_ratio=censored_ratio,
        total_episodes=total_episodes,
        resolved_episodes=len(all_durations),
        censored_episodes=censored_count,
        durations_hours=all_durations,
    )

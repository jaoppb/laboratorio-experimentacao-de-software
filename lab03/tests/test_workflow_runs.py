"""Tests for workflow runs collection, temporal bisection, T4 filter, and Parquet persistence."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from metricas.schemas import WorkflowRun
from pipeline.http_client import GitHubClient
from pipeline.workflow_runs import (
    WorkflowRunsCollectionResult,
    _format_iso,
    _resolve_default_branch,
    _to_utc_datetime,
    collect_workflow_runs,
    load_runs_from_parquet,
    save_runs_to_parquet,
    split_window_into_months,
)


def test_to_utc_datetime_and_format_iso():
    """Verify UTC datetime conversion and ISO 8601 string formatting."""
    dt_str = "2024-03-15T12:00:00Z"
    dt = _to_utc_datetime(dt_str)
    assert dt.tzinfo == timezone.utc
    assert _format_iso(dt) == "2024-03-15T12:00:00Z"

    with pytest.raises(ValueError):
        _to_utc_datetime(None)  # type: ignore


def test_split_window_into_months_full_year():
    """Verify monthly splitting generates expected calendar intervals across 12 months."""
    start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    intervals = split_window_into_months(start, end)
    assert len(intervals) == 12

    assert intervals[0][0] == start
    assert intervals[0][1].month == 1
    assert intervals[0][1].day == 31

    assert intervals[-1][0].month == 12
    assert intervals[-1][0].day == 1
    assert intervals[-1][1] == end


def test_split_window_into_months_leap_year_and_errors():
    """Verify leap year handling in February and error when start > end."""
    # 2024 is a leap year (Feb 29)
    start = datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 2, 29, 23, 59, 59, tzinfo=timezone.utc)
    intervals = split_window_into_months(start, end)
    assert len(intervals) == 1
    assert intervals[0][0].day == 1
    assert intervals[0][1].day == 29

    # Partial mid-month to mid-month
    p_start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2024, 3, 10, 18, 0, 0, tzinfo=timezone.utc)
    p_intervals = split_window_into_months(p_start, p_end)
    assert len(p_intervals) == 3
    assert p_intervals[0][0] == p_start
    assert p_intervals[-1][1] == p_end

    # Error case: start > end
    with pytest.raises(ValueError, match="cannot be after"):
        split_window_into_months(end, start)


def test_parquet_roundtrip(tmp_path: Path):
    """Verify workflow runs can be saved to Parquet and loaded back with full fidelity."""
    dest = tmp_path / "runs" / "test_owner__test_repo.parquet"

    runs = [
        WorkflowRun(
            id=101,
            workflow_id=5001,
            conclusion="success",
            run_started_at="2024-03-01T10:00:00Z",
            updated_at="2024-03-01T10:15:00Z",
            name="CI",
            event="push",
            branch="main",
        ),
        WorkflowRun(
            id=102,
            workflow_id=5001,
            conclusion="failure",
            run_started_at="2024-03-01T11:00:00Z",
            updated_at="2024-03-01T11:20:00Z",
            name="CI",
            event="push",
            branch="main",
        ),
        WorkflowRun(
            id=103,
            workflow_id=5002,
            conclusion="cancelled",
            run_started_at="2024-03-01T12:00:00Z",
            updated_at="2024-03-01T12:05:00Z",
            name="Lint",
            event="push",
            branch="main",
        ),
    ]

    saved_path = save_runs_to_parquet(
        runs=runs, owner="test_owner", repo="test_repo", output_path=dest
    )
    assert saved_path == dest
    assert dest.exists()

    loaded_runs = load_runs_from_parquet(dest)
    assert len(loaded_runs) == 3

    assert loaded_runs[0].id == 101
    assert str(loaded_runs[0].workflow_id) == "5001"
    assert loaded_runs[0].conclusion == "success"
    assert loaded_runs[0].name == "CI"
    assert loaded_runs[0].event == "push"
    assert loaded_runs[0].branch == "main"
    assert loaded_runs[0].run_started_at == datetime(
        2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc
    )

    assert loaded_runs[1].conclusion == "failure"
    assert loaded_runs[2].conclusion == "cancelled"


def test_resolve_default_branch_custom_and_fallback():
    """Verify default branch resolution directly or via API."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/octocat/hello-world":
            return httpx.Response(
                200,
                json={"default_branch": "master"},
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    with GitHubClient(client=httpx.Client(transport=transport), cache=None) as client:
        # Explicit branch provided
        assert (
            _resolve_default_branch(client, "octocat", "hello-world", branch="dev")
            == "dev"
        )
        # Queried from API
        assert (
            _resolve_default_branch(client, "octocat", "hello-world", branch=None)
            == "master"
        )


def test_resolve_default_branch_missing_field_fallback():
    """Verify default branch falls back to 'main' if API returns no default_branch."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={}, request=request)

    transport = httpx.MockTransport(handler)
    with GitHubClient(client=httpx.Client(transport=transport), cache=None) as client:
        assert (
            _resolve_default_branch(client, "octocat", "empty-repo", branch=None)
            == "main"
        )


def test_collect_workflow_runs_paginated_and_t4_pass(tmp_path: Path):
    """Verify collection of paginated runs and passing the T4 criterion (>= 50 valid runs)."""
    # Create 60 mock runs (55 success, 5 cancelled)
    mock_runs = []
    for i in range(1, 61):
        mock_runs.append(
            {
                "id": i,
                "workflow_id": 100,
                "name": "Build",
                "head_branch": "main",
                "event": "push",
                "conclusion": "success" if i <= 55 else "cancelled",
                "run_started_at": f"2024-01-{i:02d}T10:00:00Z"
                if i <= 31
                else "2024-01-31T20:00:00Z",
                "updated_at": f"2024-01-{i:02d}T10:05:00Z"
                if i <= 31
                else "2024-01-31T20:05:00Z",
            }
        )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/myorg/myrepo":
            return httpx.Response(200, json={"default_branch": "main"}, request=request)

        if request.url.path == "/repos/myorg/myrepo/actions/runs":
            page = int(request.url.params.get("page", "1"))
            per_page = int(request.url.params.get("per_page", "100"))
            # Paginated response
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_items = mock_runs[start_idx:end_idx]
            return httpx.Response(
                200,
                json={
                    "total_count": len(mock_runs),
                    "workflow_runs": page_items,
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), cache=None)

    out_dir = tmp_path / "parquet_out"
    result = collect_workflow_runs(
        owner="myorg",
        repo="myrepo",
        client=client,
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-01-31T23:59:59Z",
        save_to_parquet=True,
        output_dir=out_dir,
    )

    assert result.owner == "myorg"
    assert result.repo == "myrepo"
    assert result.branch == "main"
    assert result.total_runs == 60
    assert result.valid_runs_count == 55
    assert result.passed_t4 is True
    assert result.parquet_path is not None
    assert result.parquet_path.exists()
    assert len(result.bisection_events) == 0


def test_collect_workflow_runs_t4_fail():
    """Verify that fewer than 50 valid runs fails T4."""
    mock_runs = [
        {
            "id": i,
            "workflow_id": 100,
            "head_branch": "main",
            "event": "push",
            "conclusion": "success",
            "run_started_at": "2024-02-01T10:00:00Z",
            "updated_at": "2024-02-01T10:05:00Z",
        }
        for i in range(1, 40)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/test/repo/actions/runs":
            return httpx.Response(
                200,
                json={"total_count": len(mock_runs), "workflow_runs": mock_runs},
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), cache=None)

    result = collect_workflow_runs(
        owner="test",
        repo="repo",
        branch="main",
        client=client,
        start_date="2024-02-01T00:00:00Z",
        end_date="2024-02-28T23:59:59Z",
        save_to_parquet=False,
    )

    assert result.total_runs == 39
    assert result.valid_runs_count == 39
    assert result.passed_t4 is False


def test_collect_workflow_runs_bisection_on_ceiling_1000():
    """Verify recursive bisection triggers when a month hits the 1,000 ceiling."""
    # A single month January 2024 hits total_count = 1200.
    # When split into [Jan 1, Jan 16] and [Jan 16, Jan 31],
    # the sub-intervals return total_count 600 and 600 respectively.

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/big/repo/actions/runs":
            created = request.url.params.get("created", "")
            # Initial whole month interval
            if "2024-01-01T00:00:00Z..2024-01-31T23:59:59Z" in created:
                return httpx.Response(
                    200,
                    json={
                        "total_count": 1200,
                        "workflow_runs": [
                            {"id": i, "workflow_id": 1, "conclusion": "success"}
                            for i in range(1, 101)
                        ],
                    },
                    request=request,
                )

            # Left sub-interval
            if "2024-01-01T00:00:00Z" in created:
                left_runs = [
                    {
                        "id": i,
                        "workflow_id": 1,
                        "conclusion": "success",
                        "run_started_at": "2024-01-05T10:00:00Z",
                        "updated_at": "2024-01-05T10:05:00Z",
                    }
                    for i in range(1, 601)
                ]
                return httpx.Response(
                    200,
                    json={
                        "total_count": 600,
                        "workflow_runs": left_runs[:100],  # first page
                    },
                    request=request,
                )

            # Right sub-interval (includes ID 600 to test boundary deduplication)
            right_runs = [
                {
                    "id": i,
                    "workflow_id": 1,
                    "conclusion": "failure",
                    "run_started_at": "2024-01-20T10:00:00Z",
                    "updated_at": "2024-01-20T10:05:00Z",
                }
                for i in range(600, 1201)
            ]
            return httpx.Response(
                200,
                json={
                    "total_count": 601,
                    "workflow_runs": right_runs[:100],
                },
                request=request,
            )

        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), cache=None)

    result = collect_workflow_runs(
        owner="big",
        repo="repo",
        branch="main",
        client=client,
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-01-31T23:59:59Z",
        threshold_ceiling=1000,
        save_to_parquet=False,
    )

    # 1 bisection occurred for the initial interval
    assert len(result.bisection_events) == 1
    assert result.bisection_events[0]["total_count"] == 1200

    # Boundary ID 600 was in both left and right, but should be deduplicated
    ids = [r.id for r in result.runs]
    assert len(ids) == len(set(ids))
    assert 600 in ids


def test_bisection_guard_min_interval_seconds():
    """Verify that an interval below min_interval_seconds does not recursively split infinitely."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 1500,
                "workflow_runs": [
                    {
                        "id": 1,
                        "workflow_id": 1,
                        "conclusion": "success",
                        "run_started_at": "2024-01-01T10:00:00Z",
                        "updated_at": "2024-01-01T10:05:00Z",
                    }
                ],
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), cache=None)

    # Window of only 30 minutes, below min_interval_seconds=3600
    result = collect_workflow_runs(
        owner="fast",
        repo="repo",
        branch="main",
        client=client,
        start_date="2024-01-01T10:00:00Z",
        end_date="2024-01-01T10:30:00Z",
        threshold_ceiling=1000,
        min_interval_seconds=3600.0,
        save_to_parquet=False,
    )

    # Did not bisect because interval is smaller than min_interval_seconds
    assert len(result.bisection_events) == 0
    assert result.total_runs == 1


def test_collect_workflow_runs_empty_repo():
    """Verify collection handles an empty repository with 0 workflow runs."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"total_count": 0, "workflow_runs": []},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), cache=None)

    result = collect_workflow_runs(
        owner="empty",
        repo="repo",
        branch="main",
        client=client,
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-01-31T23:59:59Z",
        save_to_parquet=False,
    )

    assert result.total_runs == 0
    assert result.valid_runs_count == 0
    assert result.passed_t4 is False
    assert len(result.runs) == 0

"""Tests for workflow runs collection, temporal bisection, T4 filter, and Parquet persistence."""

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest

from metricas.schemas import WorkflowRun
from pipeline.http_client import GitHubClient
from pipeline.workflow_runs import (
    WorkflowRunsCollectionResult,
    _fetch_runs_for_interval,
    _FetchStats,
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


async def test_resolve_default_branch_custom_and_fallback():
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
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        # Explicit branch provided
        assert (
            await _resolve_default_branch(client, "octocat", "hello-world", branch="dev")
            == "dev"
        )
        # Queried from API
        assert (
            await _resolve_default_branch(client, "octocat", "hello-world", branch=None)
            == "master"
        )


async def test_resolve_default_branch_missing_field_fallback():
    """Verify default branch falls back to 'main' if API returns no default_branch."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={}, request=request)

    transport = httpx.MockTransport(handler)
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        assert (
            await _resolve_default_branch(client, "octocat", "empty-repo", branch=None)
            == "main"
        )


async def test_collect_workflow_runs_paginated_and_t4_pass(tmp_path: Path):
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
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        out_dir = tmp_path / "parquet_out"
        result = await collect_workflow_runs(
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


async def test_collect_workflow_runs_t4_fail():
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
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        result = await collect_workflow_runs(
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


async def test_collect_workflow_runs_bisection_on_ceiling_1000():
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
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        result = await collect_workflow_runs(
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


async def test_collect_workflow_runs_empty_repo():
    """Verify collection handles an empty repository with 0 workflow runs."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"total_count": 0, "workflow_runs": []},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        result = await collect_workflow_runs(
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


# ---------------------------------------------------------------------------
# Recursive splitting without depth/day floor (synthetic GitHub Actions API)
# ---------------------------------------------------------------------------

_PARSE = "%Y-%m-%dT%H:%M:%SZ"
_API_RUNS_CAP = 1000  # GitHub serves at most 10 pages x 100 per query


def _ts(value: str) -> datetime:
    return datetime.strptime(value, _PARSE).replace(tzinfo=timezone.utc)


class FakeRunsApi:
    """In-memory ``/actions/runs`` honouring ``created=a..b`` (inclusive, 1 s), paging and the 1,000 cap."""

    def __init__(self, created_times: list[datetime]) -> None:
        self.runs = [
            {
                "id": i + 1,
                "workflow_id": 1,
                "head_branch": "main",
                "event": "push",
                "conclusion": "success" if i % 2 else "failure",
                "created_at": t.strftime(_PARSE),
                "run_started_at": t.strftime(_PARSE),
                "updated_at": (t + timedelta(minutes=5)).strftime(_PARSE),
            }
            for i, t in enumerate(sorted(created_times))
        ]
        self._created = [_ts(r["created_at"]) for r in self.runs]
        self.calls: list[tuple[datetime, datetime, int]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path != "/repos/o/r/actions/runs":
            return httpx.Response(404, request=request)
        lo_s, hi_s = request.url.params["created"].split("..")
        lo, hi = _ts(lo_s), _ts(hi_s)
        page = int(request.url.params.get("page", "1"))
        per_page = int(request.url.params.get("per_page", "100"))
        self.calls.append((lo, hi, page))
        matching = [r for r, t in zip(self.runs, self._created) if lo <= t <= hi]
        readable = matching[:_API_RUNS_CAP]
        start = (page - 1) * per_page
        return httpx.Response(
            200,
            json={
                "total_count": len(matching),
                "workflow_runs": readable[start : start + per_page],
            },
            request=request,
        )

    @property
    def request_count(self) -> int:
        return len(self.calls)


async def _collect(api: FakeRunsApi, start: str, end: str, **kwargs: Any):
    transport = httpx.MockTransport(api.handler)
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        return await collect_workflow_runs(
            owner="o",
            repo="r",
            branch="main",
            client=client,
            start_date=start,
            end_date=end,
            save_to_parquet=False,
            **kwargs,
        )


def _spread(day: str, n: int, step_seconds: int = 1) -> list[datetime]:
    base = _ts(f"{day}T00:00:00Z")
    return [base + timedelta(seconds=i * step_seconds) for i in range(n)]


async def test_recursive_split_more_than_1000_runs_in_a_single_day():
    """2,500 runs inside one day: far below the old 2-day floor, must still be fully read."""
    api = FakeRunsApi(_spread("2024-01-10", 2500, step_seconds=20))
    result = await _collect(api, "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")

    assert result.total_runs == 2500
    assert {r.id for r in result.runs} == {r["id"] for r in api.runs}
    assert result.unsplittable_intervals == []
    # more than 3 levels of bisection were needed (old max_depth) -> no depth limit
    sizes = [
        (_ts(e["end"]) - _ts(e["start"])).total_seconds() + 1
        for e in result.bisection_events
    ]
    assert min(sizes) < 2 * 86400
    assert min(sizes) <= 86400 / 2


async def test_recursive_split_dense_bursts_are_all_collected():
    """Several 1,500-run bursts a few minutes long, in different months."""
    times = (
        _spread("2024-01-05", 1500, step_seconds=1)
        + [t + timedelta(hours=7) for t in _spread("2024-02-20", 1500, step_seconds=1)]
        + _spread("2024-03-03", 400, step_seconds=60)  # sparse month part
    )
    api = FakeRunsApi(times)
    result = await _collect(api, "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z")

    assert result.total_runs == 3400
    assert result.unsplittable_intervals == []
    assert len(result.bisection_events) >= 2
    # leaves are disjoint: nothing is requested twice at the same page/range
    assert len(set(api.calls)) == len(api.calls)


async def test_recursive_split_empty_intervals_cost_one_request_each():
    api = FakeRunsApi([])
    result = await _collect(api, "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z")

    assert result.total_runs == 0
    assert result.bisection_events == []
    assert result.api_requests == 3 == api.request_count  # one probe per month


async def test_boundary_999_is_not_split_and_1000_is_split():
    """The ceiling is ``total_count >= 1000``: 999 is read directly, 1000 is halved."""
    api_999 = FakeRunsApi(_spread("2024-01-10", 999, step_seconds=60))
    res_999 = await _collect(api_999, "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")
    assert res_999.total_runs == 999
    assert res_999.bisection_events == []
    assert res_999.api_requests == 10  # 1 probe (page 1) + 9 pages

    api_1000 = FakeRunsApi(_spread("2024-01-10", 1000, step_seconds=60))
    res_1000 = await _collect(api_1000, "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")
    assert res_1000.total_runs == 1000
    assert len(res_1000.bisection_events) >= 1
    assert res_1000.bisection_events[0]["total_count"] == 1000
    assert res_1000.unsplittable_intervals == []
    assert res_1000.api_requests == api_1000.request_count > 10


async def test_unsplittable_second_reads_what_is_readable_and_warns_once(caplog):
    """1,200 runs created in the very same second cannot be separated by any filter."""
    same_second = [_ts("2024-01-10T12:00:00Z")] * 1200
    other = _spread("2024-01-20", 30, step_seconds=3600)
    api = FakeRunsApi(same_second + other)

    with caplog.at_level(logging.WARNING, logger="pipeline.workflow_runs"):
        result = await _collect(api, "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")

    assert len(result.unsplittable_intervals) == 1
    event = result.unsplittable_intervals[0]
    assert event["start"] == event["end"] == "2024-01-10T12:00:00Z"
    assert event["total_count"] == 1200
    assert event["runs_read"] == 1000
    # 1,000 readable + the 30 isolated runs; the extra 200 are unreachable
    assert result.total_runs == 1030
    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "cannot be split further" in r.getMessage()
    ]
    assert len(warnings) == 1  # once per repository, with counts
    assert "1200" in warnings[0].getMessage()


async def test_unsplittable_warning_is_aggregated_per_repo(caplog):
    """Two different saturated seconds still produce a single warning."""
    times = [_ts("2024-01-10T12:00:00Z")] * 1100 + [_ts("2024-02-10T08:00:00Z")] * 1050
    api = FakeRunsApi(times)
    with caplog.at_level(logging.WARNING, logger="pipeline.workflow_runs"):
        result = await _collect(api, "2024-01-01T00:00:00Z", "2024-02-29T23:59:59Z")

    assert len(result.unsplittable_intervals) == 2
    warnings = [r for r in caplog.records if "cannot be split further" in r.getMessage()]
    assert len(warnings) == 1
    assert "2 one-second" in warnings[0].getMessage()


async def test_fetch_interval_directly_single_second_never_recurses():
    api = FakeRunsApi([_ts("2024-01-10T12:00:00Z")] * 1001)
    stats = _FetchStats()
    transport = httpx.MockTransport(api.handler)
    events: list[dict[str, Any]] = []
    async with GitHubClient(
        client=httpx.AsyncClient(transport=transport), cache=None
    ) as client:
        runs = await _fetch_runs_for_interval(
            client,
            "o",
            "r",
            "main",
            _ts("2024-01-10T12:00:00Z"),
            _ts("2024-01-10T12:00:00Z"),
            1000,
            events,
            stats,
        )
    assert len(runs) == 1000
    assert events == []
    assert stats.api_requests == 10
    assert len(stats.unsplittable_intervals) == 1


async def test_split_halves_are_disjoint_and_cover_the_interval():
    """Leaf ranges queried for a saturated month tile it exactly (no overlap, no gap)."""
    api = FakeRunsApi(_spread("2024-01-10", 1300, step_seconds=30))
    await _collect(api, "2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")

    first_pages = sorted({(lo, hi) for lo, hi, page in api.calls if page == 1})
    # keep only intervals that were NOT split further (no strictly contained child)
    leaves = [
        (lo, hi)
        for lo, hi in first_pages
        if not any((l2, h2) != (lo, hi) and lo <= l2 and h2 <= hi for l2, h2 in first_pages)
    ]
    leaves.sort()
    assert leaves[0][0] == _ts("2024-01-01T00:00:00Z")
    assert leaves[-1][1] == _ts("2024-01-31T23:59:59Z")
    for (_, prev_hi), (next_lo, _) in zip(leaves, leaves[1:]):
        assert next_lo == prev_hi + timedelta(seconds=1)


async def test_resume_with_http_cache_makes_no_new_api_calls(tmp_path: Path):
    """After an interrupted/complete run, the disk cache serves every split query again."""
    from pipeline.cache import HttpCache

    api = FakeRunsApi(_spread("2024-01-10", 1800, step_seconds=40))
    cache_db = tmp_path / "cache.sqlite"

    async def run_once():
        transport = httpx.MockTransport(api.handler)
        async with GitHubClient(
            client=httpx.AsyncClient(transport=transport),
            cache=HttpCache(cache_db),
        ) as client:
            return await collect_workflow_runs(
                owner="o",
                repo="r",
                branch="main",
                client=client,
                start_date="2024-01-01T00:00:00Z",
                end_date="2024-01-31T23:59:59Z",
                save_to_parquet=False,
            )

    first = await run_once()
    network_calls = api.request_count
    assert network_calls > 0 and first.total_runs == 1800

    second = await run_once()
    assert api.request_count == network_calls  # fully served from cache
    assert {r.id for r in second.runs} == {r.id for r in first.runs}
    assert second.api_requests == first.api_requests

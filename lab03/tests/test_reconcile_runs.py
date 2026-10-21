"""Tests for the reconciliation of previous workflow runs with the API (Issue #56)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from metricas.schemas import WorkflowRun
from pipeline.workflow_runs import (
    collect_workflow_runs,
    count_runs_in_interval,
    reconcile_workflow_runs,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
PREV_END = datetime(2026, 3, 31, 0, 0, 0, tzinfo=timezone.utc)  # old window: date-only, 00:00Z
NEW_END = "2026-03-31"  # new window: whole last day


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def raw_run(i: int, created: str, conclusion: str = "success") -> dict[str, Any]:
    return {
        "id": i,
        "workflow_id": 1,
        "conclusion": conclusion,
        "created_at": created,
        "run_started_at": created,
        "updated_at": created,
        "name": "ci",
        "event": "push",
        "head_branch": "main",
    }


class FakeRunsApi:
    """Answers the runs endpoint from a list of raw runs, honouring `created`/`page`/`per_page`."""

    def __init__(self, runs: list[dict[str, Any]]) -> None:
        self.runs = runs
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, params: dict[str, Any] | None = None) -> FakeResponse:
        params = params or {}
        assert params["event"] == "push" and params["branch"] == "main"
        self.calls.append(dict(params))
        lo, hi = params["created"].split("..")
        lo_dt = datetime.fromisoformat(lo.replace("Z", "+00:00"))
        hi_dt = datetime.fromisoformat(hi.replace("Z", "+00:00"))
        hits = sorted(
            (
                r
                for r in self.runs
                if lo_dt <= datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) <= hi_dt
            ),
            key=lambda r: r["created_at"],
        )
        per_page, page = params["per_page"], params["page"]
        return FakeResponse(
            {
                "total_count": len(hits),
                "workflow_runs": hits[(page - 1) * per_page : page * per_page],
            }
        )

    @property
    def count_calls(self) -> int:
        return sum(1 for c in self.calls if c["per_page"] == 1)


def to_previous(runs: list[dict[str, Any]], until: datetime = PREV_END) -> list[WorkflowRun]:
    """The runs a previous collection would have stored (everything up to its window end)."""
    from pipeline.workflow_runs import _workflow_run_from_raw

    return [
        _workflow_run_from_raw(r)
        for r in runs
        if datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) <= until
    ]


BASE_RUNS = (
    [raw_run(i, f"2026-01-{10 + i:02d}T10:00:00Z") for i in range(5)]  # January
    + [raw_run(10 + i, f"2026-02-{10 + i:02d}T10:00:00Z", "failure") for i in range(4)]  # February
    + [raw_run(20 + i, f"2026-03-{10 + i:02d}T10:00:00Z") for i in range(3)]  # March
    # last day of the window: only the new (end-of-day) window sees them
    + [raw_run(30, "2026-03-31T09:00:00Z"), raw_run(31, "2026-03-31T22:30:00Z", "failure")]
)


def reconcile(api: FakeRunsApi, previous: list[WorkflowRun], **kw):
    return asyncio.run(
        reconcile_workflow_runs(
            "o", "r", previous, api, START, PREV_END, NEW_END, "main", **kw  # type: ignore[arg-type]
        )
    )


def test_equal_counts_keep_previous_runs_and_fetch_only_the_tail():
    api = FakeRunsApi(BASE_RUNS)
    result = reconcile(api, to_previous(BASE_RUNS))

    assert {r.id for r in result.runs} == {r["id"] for r in BASE_RUNS}
    actions = [e["action"] for e in result.reconciliation]
    assert sorted(actions) == ["kept", "kept", "kept", "tail"]
    # 3 months x 1 count request + the tail (1 page)
    assert api.count_calls == 3
    assert len(api.calls) == 4
    tail = [e for e in result.reconciliation if e["action"] == "tail"][0]
    assert (tail["start"], tail["end"]) == ("2026-03-31T00:00:01Z", "2026-03-31T23:59:59Z")
    assert result.api_requests == 4
    assert result.valid_runs_count == len(BASE_RUNS)
    assert result.total_runs == len(BASE_RUNS)


def test_count_mismatch_refetches_only_that_interval():
    api_runs = BASE_RUNS + [raw_run(99, "2026-02-20T10:00:00Z")]  # one run the previous data lacks
    api = FakeRunsApi(api_runs)
    result = reconcile(api, to_previous(BASE_RUNS))

    by_start = {e["start"]: e for e in result.reconciliation}
    assert by_start["2026-02-01T00:00:00Z"]["action"] == "refetched"
    assert by_start["2026-02-01T00:00:00Z"]["previous_count"] == 4
    assert by_start["2026-02-01T00:00:00Z"]["api_count"] == 5
    assert by_start["2026-01-01T00:00:00Z"]["action"] == "kept"
    assert 99 in {r.id for r in result.runs}
    assert len(result.runs) == len(api_runs)


def test_deleted_runs_disappear():
    api_runs = [r for r in BASE_RUNS if r["id"] not in (11, 12)]
    result = reconcile(FakeRunsApi(api_runs), to_previous(BASE_RUNS))

    ids = {r.id for r in result.runs}
    assert 11 not in ids and 12 not in ids
    assert ids == {r["id"] for r in api_runs}
    refetched = [e for e in result.reconciliation if e["action"] == "refetched"]
    assert [(e["previous_count"], e["api_count"]) for e in refetched] == [(4, 2)]


def test_truncated_interval_is_refetched_with_recursive_splitting():
    many = [raw_run(100 + i, f"2026-01-{1 + i // 3:02d}T{i % 3 * 6:02d}:00:00Z") for i in range(30)]
    api_runs = [*many, raw_run(500, "2026-02-05T10:00:00Z")]
    # the previous collection stopped at 10 runs of January (old per-interval cap)
    previous = to_previous(many[:10] + [api_runs[-1]])
    api = FakeRunsApi(api_runs)

    result = reconcile(api, previous, threshold_ceiling=10)

    assert {r.id for r in result.runs} == {r["id"] for r in api_runs}
    jan = [e for e in result.reconciliation if e["start"] == "2026-01-01T00:00:00Z"][0]
    assert (jan["action"], jan["previous_count"], jan["api_count"]) == ("refetched", 10, 30)
    assert result.bisection_events  # the collector's recursive splitting was used


def test_reconciled_result_equals_a_full_collection():
    api_runs = [r for r in BASE_RUNS if r["id"] != 21] + [raw_run(77, "2026-01-02T01:00:00Z")]
    previous = to_previous([r for r in BASE_RUNS if r["id"] != 77])
    full = asyncio.run(
        collect_workflow_runs(
            "o", "r", FakeRunsApi(api_runs), START, NEW_END, "main", save_to_parquet=False  # type: ignore[arg-type]
        )
    )
    recon = reconcile(FakeRunsApi(api_runs), previous)

    assert {r.id for r in recon.runs} == {r.id for r in full.runs}
    assert recon.valid_runs_count == full.valid_runs_count
    assert recon.total_runs == full.total_runs


def test_previous_runs_outside_the_window_are_dropped():
    stray = to_previous([raw_run(900, "2025-12-31T23:00:00Z")], until=PREV_END)
    result = reconcile(FakeRunsApi(BASE_RUNS), to_previous(BASE_RUNS) + stray)
    assert 900 not in {r.id for r in result.runs}


def test_no_tail_when_the_window_did_not_grow():
    api = FakeRunsApi([r for r in BASE_RUNS if r["created_at"] < "2026-03-31T00:00:01Z"])
    result = asyncio.run(
        reconcile_workflow_runs(
            "o", "r", to_previous(BASE_RUNS), api, START, PREV_END,  # type: ignore[arg-type]
            PREV_END, "main",
        )
    )
    assert [e["action"] for e in result.reconciliation] == ["kept"] * 3
    assert len(api.calls) == 3


def test_count_runs_in_interval_asks_for_one_run_with_the_collector_filters():
    api = FakeRunsApi(BASE_RUNS)
    n = asyncio.run(
        count_runs_in_interval(
            api, "o", "r", "main", START, START + timedelta(days=31, microseconds=-1)  # type: ignore[arg-type]
        )
    )
    assert n == 5
    call = api.calls[0]
    assert (call["per_page"], call["page"], call["event"], call["branch"]) == (1, 1, "push", "main")
    assert call["created"] == "2026-01-01T00:00:00Z..2026-01-31T23:59:59Z"


@pytest.mark.parametrize(
    ("previous", "api", "needle"),
    [(1000, 1200, "truncado"), (3, 5, "mais runs"), (5, 3, "menos runs")],
)
def test_refetch_reason(previous, api, needle):
    from pipeline.regeneracao_relatorio import refetch_reason

    assert needle in refetch_reason(previous, api)

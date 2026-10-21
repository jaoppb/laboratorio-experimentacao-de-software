"""Tests for the end-of-day upper bound of the observation window (issue #56, Q3).

A date-only `janela.fim` ("2026-09-30") means the END of that day; `janela.inicio`
("2025-10-01") stays 00:00:00Z. Explicit datetimes keep working as-is.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from metricas.cfr_b import ReleaseOutcome, calculate_cfr_b
from metricas.dora import (
    DEFAULT_WINDOW_WEEKS,
    MONTHLY_FREQ_THRESHOLD,
    calculate_deployment_frequency,
)
from metricas.schemas import (
    Commit,
    Release,
    _parse_datetime,
    parse_window_end,
    window_length,
)
from pipeline.http_client import GitHubClient
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.releases import count_valid_releases, filter_window
from pipeline.workflow_runs import collect_workflow_runs

START = "2025-10-01"
END = "2026-09-30"
UTC = timezone.utc
LAST_INSTANT = datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=UTC)


# --------------------------------------------------------------------------- helper


def test_parse_window_end_date_only_is_end_of_day():
    assert parse_window_end("2026-09-30") == LAST_INSTANT
    assert parse_window_end(" 2026-09-30 ") == LAST_INSTANT
    assert parse_window_end(date(2026, 9, 30)) == LAST_INSTANT


def test_parse_window_end_handles_month_and_year_rollover():
    assert parse_window_end("2026-12-31") == datetime(2026, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)
    assert parse_window_end("2024-02-29") == datetime(2024, 2, 29, 23, 59, 59, 999999, tzinfo=UTC)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-09-30T00:00:00Z", datetime(2026, 9, 30, tzinfo=UTC)),
        ("2026-09-30T23:59:59Z", datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC)),
        ("2026-09-30T12:00:00+00:00", datetime(2026, 9, 30, 12, tzinfo=UTC)),
        (datetime(2026, 9, 30), datetime(2026, 9, 30, tzinfo=UTC)),
        (datetime(2026, 9, 30, 8, tzinfo=UTC), datetime(2026, 9, 30, 8, tzinfo=UTC)),
    ],
)
def test_parse_window_end_explicit_time_is_kept(value, expected):
    assert parse_window_end(value) == expected


def test_parse_window_end_none_and_start_unchanged():
    assert parse_window_end(None) is None
    # `inicio` is still 00:00:00Z.
    assert _parse_datetime(START) == datetime(2025, 10, 1, tzinfo=UTC)


def test_window_is_365_days_and_52_14_weeks():
    start = _parse_datetime(START)
    end = parse_window_end(END)
    assert window_length(start, end) == timedelta(days=365)
    assert window_length(start, end) / timedelta(weeks=1) == pytest.approx(DEFAULT_WINDOW_WEEKS)
    assert DEFAULT_WINDOW_WEEKS == pytest.approx(365 / 7)
    assert MONTHLY_FREQ_THRESHOLD == pytest.approx(12 / (365 / 7))


# ------------------------------------------------------------------------- releases


def _rel(tag: str, published_at: str) -> Release:
    return Release(tag_name=tag, published_at=published_at)


@pytest.fixture
def boundary_releases() -> list[Release]:
    return [
        _rel("before", "2025-09-30T23:59:59Z"),
        _rel("start", "2025-10-01T00:00:00Z"),
        _rel("sep30-midnight", "2026-09-30T00:00:00Z"),
        _rel("sep30-last-second", "2026-09-30T23:59:59Z"),
        _rel("oct01-midnight", "2026-10-01T00:00:00Z"),
    ]


def test_filter_window_date_only_end_includes_whole_last_day(boundary_releases):
    window = filter_window(boundary_releases, START, END)
    assert [r.tag_name for r in window.in_window] == [
        "start",
        "sep30-midnight",
        "sep30-last-second",
    ]
    assert window.anchor is not None and window.anchor.tag_name == "before"
    assert window.count == 3


def test_filter_window_microsecond_before_next_day_is_inside():
    rel = _rel("edge", datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=UTC).isoformat())
    assert filter_window([rel], START, END).count == 1


def test_filter_window_explicit_datetime_end_is_unchanged(boundary_releases):
    window = filter_window(boundary_releases, START, "2026-09-30T00:00:00Z")
    assert [r.tag_name for r in window.in_window] == ["start", "sep30-midnight"]


def test_filter_window_accepts_parsed_end_of_day(boundary_releases):
    window = filter_window(boundary_releases, _parse_datetime(START), parse_window_end(END))
    assert window.count == 3


def test_count_valid_releases_date_only_end(boundary_releases):
    assert count_valid_releases(boundary_releases, START, END) == 3


# ---------------------------------------------------------------------------- runs


def _runs_handler(created_ats: list[str]):
    """Fake `actions/runs` honoring GitHub's inclusive `created=start..end` filter."""

    runs = [
        {
            "id": i,
            "workflow_id": 1,
            "head_branch": "main",
            "event": "push",
            "conclusion": "success",
            "created_at": ts,
            "run_started_at": ts,
            "updated_at": ts,
        }
        for i, ts in enumerate(created_ats, start=1)
    ]
    seen_filters: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/o/r/actions/runs":
            created = request.url.params["created"]
            seen_filters.append(created)
            lo, hi = created.split("..")
            lo_dt, hi_dt = _parse_datetime(lo), _parse_datetime(hi)
            page = [r for r in runs if lo_dt <= _parse_datetime(r["created_at"]) <= hi_dt]
            return httpx.Response(
                200, json={"total_count": len(page), "workflow_runs": page}, request=request
            )
        return httpx.Response(404, request=request)

    return handler, seen_filters


@pytest.mark.parametrize("end_date", [END, parse_window_end(END), LAST_INSTANT.isoformat()])
async def test_collect_runs_date_only_end_includes_whole_last_day(end_date):
    handler, seen = _runs_handler(
        [
            "2026-09-29T12:00:00Z",
            "2026-09-30T00:00:00Z",
            "2026-09-30T23:59:59Z",
            "2026-10-01T00:00:00Z",
        ]
    )
    async with GitHubClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), cache=None
    ) as client:
        result = await collect_workflow_runs(
            owner="o",
            repo="r",
            client=client,
            branch="main",
            start_date=START,
            end_date=end_date,
            save_to_parquet=False,
        )

    started = sorted(r.run_started_at.isoformat() for r in result.runs)
    assert started == [
        "2026-09-29T12:00:00+00:00",
        "2026-09-30T00:00:00+00:00",
        "2026-09-30T23:59:59+00:00",
    ]
    # The last monthly interval ends at the last second of 2026-09-30.
    assert any(f.endswith("..2026-09-30T23:59:59Z") for f in seen)
    assert not any("2026-10-01" in f for f in seen)


async def test_collect_runs_explicit_datetime_end_is_unchanged():
    handler, _ = _runs_handler(["2026-09-30T00:00:00Z", "2026-09-30T23:59:59Z"])
    async with GitHubClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), cache=None
    ) as client:
        result = await collect_workflow_runs(
            owner="o",
            repo="r",
            client=client,
            branch="main",
            start_date=START,
            end_date="2026-09-30T00:00:00Z",
            save_to_parquet=False,
        )
    assert [r.run_started_at.isoformat() for r in result.runs] == ["2026-09-30T00:00:00+00:00"]


# ------------------------------------------------------------------ censoring cutoff


def _cfr_input(published_at: str):
    # A single release followed by nothing: ok if evaluated, censored past the cutoff.
    return [(Release(tag_name="v1", published_at=published_at), [Commit(sha="a", committed_at=published_at)])]


@pytest.mark.parametrize(
    "published_at, outcome",
    [
        # cutoff = 2026-09-30T23:59:59.999999Z - 7d = 2026-09-23T23:59:59.999999Z
        ("2026-09-23T00:00:00Z", ReleaseOutcome.OK),
        ("2026-09-23T23:59:59Z", ReleaseOutcome.OK),
        ("2026-09-24T00:00:00Z", ReleaseOutcome.CENSORED),
        ("2026-09-30T00:00:00Z", ReleaseOutcome.CENSORED),
        ("2026-09-30T23:59:59Z", ReleaseOutcome.CENSORED),
    ],
)
def test_censoring_cutoff_uses_end_of_day(published_at, outcome):
    result = calculate_cfr_b(_cfr_input(published_at), window_end=END)
    assert dict(result.outcomes)["v1"] == outcome


def test_censoring_cutoff_explicit_datetime_end_is_unchanged():
    # Old behavior for an explicit instant: cutoff = 2026-09-23T00:00:00Z.
    ok = calculate_cfr_b(_cfr_input("2026-09-23T00:00:00Z"), window_end="2026-09-30T00:00:00Z")
    late = calculate_cfr_b(_cfr_input("2026-09-23T00:00:01Z"), window_end="2026-09-30T00:00:00Z")
    assert dict(ok.outcomes)["v1"] == ReleaseOutcome.OK
    assert dict(late.outcomes)["v1"] == ReleaseOutcome.CENSORED


def test_censoring_cutoff_string_and_parsed_end_agree():
    releases = _cfr_input("2026-09-24T00:00:00Z")
    assert calculate_cfr_b(releases, END).censored_releases == 1
    assert calculate_cfr_b(releases, parse_window_end(END)).censored_releases == 1


# ------------------------------------------------------ deployment frequency / pipeline


def test_deployment_frequency_denominator_is_365_over_7():
    releases = [_rel(f"v{i}", f"2026-0{i}-01T00:00:00Z") for i in range(1, 6)]
    assert calculate_deployment_frequency(releases) == pytest.approx(5 / (365 / 7))
    # Not the old 52.1 denominator.
    assert calculate_deployment_frequency(releases) != pytest.approx(5 / 52.1, rel=1e-6)


def test_deployment_frequency_counts_last_day_releases():
    releases = [_rel("a", "2026-09-30T00:00:00Z"), _rel("b", "2026-09-30T23:59:59Z"), _rel("c", "2026-10-01T00:00:00Z")]
    freq = calculate_deployment_frequency(
        releases, start_date=_parse_datetime(START), end_date=parse_window_end(END)
    )
    assert freq == pytest.approx(2 / (365 / 7))


def test_pipeline_uses_end_of_day_and_365_day_weeks():
    pipeline = PipelineOrchestrator(
        config={"janela": {"inicio": START, "fim": END}}
    )
    assert pipeline.window_start == datetime(2025, 10, 1, tzinfo=UTC)
    assert pipeline.window_end == LAST_INSTANT
    assert pipeline.window_weeks == pytest.approx(365 / 7)
    assert pipeline.window_weeks == pytest.approx(DEFAULT_WINDOW_WEEKS)

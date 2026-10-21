"""Collector for GitHub Actions workflow runs on the default branch with adaptive parallel slicing and Parquet storage."""

from __future__ import annotations

import asyncio
import calendar
import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from metricas.schemas import WorkflowRun, _parse_datetime, parse_window_end
from metricas.stability import ConclusionCategory, classify_conclusion
from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)

# The Actions "list workflow runs" endpoint exposes at most 1,000 results per
# query (10 pages x 100), no matter how large ``total_count`` is.
RUNS_PER_PAGE = 100
MAX_READABLE_PAGES = 10


def _to_utc_datetime(val: datetime | str) -> datetime:
    """Ensure a datetime or ISO string is converted to a UTC timezone-aware datetime."""
    dt = _parse_datetime(val)
    if dt is None:
        raise ValueError("Datetime value cannot be None")
    return dt.astimezone(timezone.utc)


def _format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 string in UTC for GitHub API queries."""
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def split_window_into_months(
    start_date: datetime | str, end_date: datetime | str
) -> list[tuple[datetime, datetime]]:
    """Split an observation window into contiguous calendar-month intervals."""
    start = _to_utc_datetime(start_date)
    end = _to_utc_datetime(end_date)

    if start > end:
        raise ValueError(f"start_date ({start}) cannot be after end_date ({end})")

    intervals: list[tuple[datetime, datetime]] = []
    current_start = start

    while current_start < end:
        _, last_day = calendar.monthrange(current_start.year, current_start.month)
        month_end = datetime(
            current_start.year,
            current_start.month,
            last_day,
            23,
            59,
            59,
            999999,
            tzinfo=timezone.utc,
        )

        slice_end = min(month_end, end)
        intervals.append((current_start, slice_end))

        if slice_end >= end:
            break

        if current_start.month == 12:
            next_month_start = datetime(
                current_start.year + 1, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc
            )
        else:
            next_month_start = datetime(
                current_start.year,
                current_start.month + 1,
                1,
                0,
                0,
                0,
                0,
                tzinfo=timezone.utc,
            )

        current_start = next_month_start

    return intervals


@dataclass
class WorkflowRunsCollectionResult:
    """Summary and details of collected workflow runs for a repository."""

    owner: str
    repo: str
    branch: str
    runs: list[WorkflowRun]
    total_runs: int
    valid_runs_count: int
    passed_t4: bool
    bisection_events: list[dict[str, Any]] = field(default_factory=list)
    parquet_path: Path | None = None
    api_requests: int = 0
    unsplittable_intervals: list[dict[str, Any]] = field(default_factory=list)
    # Only for `reconcile_workflow_runs`: one entry per coarse interval (see there)
    reconciliation: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _FetchStats:
    """Per-repository counters shared by every (concurrent) interval fetch."""

    api_requests: int = 0
    unsplittable_intervals: list[dict[str, Any]] = field(default_factory=list)


def save_runs_to_parquet(
    runs: list[WorkflowRun],
    owner: str,
    repo: str,
    output_path: str | Path,
) -> Path:
    """Serialize workflow runs to a columnar Parquet file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    repo_full_name = f"{owner}/{repo}"

    ids: list[int] = []
    repos: list[str] = []
    workflow_ids: list[str] = []
    names: list[str | None] = []
    events: list[str | None] = []
    branches: list[str | None] = []
    conclusions: list[str | None] = []
    started_ats: list[datetime] = []
    updated_ats: list[datetime] = []
    is_valids: list[bool] = []

    for r in runs:
        ids.append(int(r.id) if r.id is not None else 0)
        repos.append(repo_full_name)
        workflow_ids.append(str(r.workflow_id))
        names.append(r.name)
        events.append(r.event)
        branches.append(r.branch)
        conclusions.append(r.conclusion)

        started_dt = (
            r.run_started_at
            if isinstance(r.run_started_at, datetime)
            else _to_utc_datetime(r.run_started_at)
        )
        updated_dt = (
            r.updated_at
            if isinstance(r.updated_at, datetime)
            else _to_utc_datetime(r.updated_at)
        )
        started_ats.append(started_dt.astimezone(timezone.utc))
        updated_ats.append(updated_dt.astimezone(timezone.utc))

        is_valid = classify_conclusion(r.conclusion) in (
            ConclusionCategory.SUCCESS,
            ConclusionCategory.FAILURE,
        )
        is_valids.append(is_valid)

    schema = pa.schema(
        [
            ("id", pa.int64()),
            ("repo", pa.string()),
            ("workflow_id", pa.string()),
            ("name", pa.string()),
            ("event", pa.string()),
            ("branch", pa.string()),
            ("conclusion", pa.string()),
            ("run_started_at", pa.timestamp("us", tz="UTC")),
            ("updated_at", pa.timestamp("us", tz="UTC")),
            ("is_valid", pa.bool_()),
        ]
    )

    table = pa.Table.from_arrays(
        [
            pa.array(ids, type=pa.int64()),
            pa.array(repos, type=pa.string()),
            pa.array(workflow_ids, type=pa.string()),
            pa.array(names, type=pa.string()),
            pa.array(events, type=pa.string()),
            pa.array(branches, type=pa.string()),
            pa.array(conclusions, type=pa.string()),
            pa.array(started_ats, type=pa.timestamp("us", tz="UTC")),
            pa.array(updated_ats, type=pa.timestamp("us", tz="UTC")),
            pa.array(is_valids, type=pa.bool_()),
        ],
        schema=schema,
    )

    pq.write_table(table, path, compression="snappy")
    return path


def load_runs_from_parquet(parquet_path: str | Path) -> list[WorkflowRun]:
    """Load workflow runs from a Parquet file into WorkflowRun dataclasses."""
    table = pq.read_table(parquet_path)
    pydict = table.to_pydict()

    runs: list[WorkflowRun] = []
    total = len(pydict["id"])

    for i in range(total):
        runs.append(
            WorkflowRun(
                id=pydict["id"][i],
                workflow_id=pydict["workflow_id"][i],
                conclusion=pydict["conclusion"][i],
                run_started_at=pydict["run_started_at"][i],
                updated_at=pydict["updated_at"][i],
                name=pydict["name"][i],
                event=pydict["event"][i],
                branch=pydict["branch"][i],
            )
        )

    return runs


async def _resolve_default_branch(
    client: GitHubClient, owner: str, repo: str, branch: str | None
) -> str:
    """Resolve the default branch, querying the GitHub API if not provided."""
    if branch:
        return branch

    resp = await client.get(f"/repos/{owner}/{repo}")
    data = resp.json()
    default_branch = data.get("default_branch")
    if not default_branch:
        logger.warning(
            "Could not determine default_branch for %s/%s. Falling back to 'main'.",
            owner,
            repo,
        )
        return "main"
    return str(default_branch)


def _floor_to_second(dt: datetime) -> datetime:
    """Drop sub-second precision: the GitHub ``created`` filter has 1 s resolution."""
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def _runs_url(owner: str, repo: str) -> str:
    return f"/repos/{owner}/{repo}/actions/runs"


def _runs_query_params(
    branch: str, start_str: str, end_str: str, per_page: int, page: int
) -> dict[str, Any]:
    """Query of the runs endpoint: the filters of the collection, shared by every caller."""
    return {
        "branch": branch,
        "event": "push",
        "created": f"{start_str}..{end_str}",
        "per_page": per_page,
        "page": page,
    }


def _workflow_run_from_raw(r_dict: dict[str, Any]) -> WorkflowRun:
    """Convert a run of the API payload into a `WorkflowRun`."""
    started = r_dict.get("run_started_at") or r_dict.get("created_at")
    updated = r_dict.get("updated_at") or started
    return WorkflowRun(
        id=r_dict.get("id"),
        workflow_id=r_dict.get("workflow_id", ""),
        conclusion=r_dict.get("conclusion"),
        run_started_at=started,
        updated_at=updated,
        name=r_dict.get("name"),
        event=r_dict.get("event"),
        branch=r_dict.get("head_branch"),
    )


def _is_valid_run(run: WorkflowRun) -> bool:
    return classify_conclusion(run.conclusion) in (
        ConclusionCategory.SUCCESS,
        ConclusionCategory.FAILURE,
    )


async def _fetch_runs_for_interval(
    client: GitHubClient,
    owner: str,
    repo: str,
    branch: str,
    start_dt: datetime,
    end_dt: datetime,
    threshold_ceiling: int,
    bisection_events: list[dict[str, Any]],
    stats: _FetchStats | None = None,
) -> list[dict[str, Any]]:
    """Fetch the runs of a closed ``[start_dt, end_dt]`` interval (whole seconds).

    While ``total_count >= threshold_ceiling`` the interval is split in half and
    both halves are queried in parallel, recursively, with no depth limit and no
    minimum size in days. The halves are disjoint (``[start, mid]`` and
    ``[mid + 1 s, end]``), so every split strictly shrinks the interval.

    Residual case: an interval of a single second (cannot be split any further)
    that still reports ``total_count >= threshold_ceiling`` is read as far as the
    API allows (10 pages x 100 = 1,000 runs) and recorded in
    ``stats.unsplittable_intervals``; the caller logs one warning per repository.
    """
    if stats is None:
        stats = _FetchStats()

    start_dt = _floor_to_second(start_dt)
    end_dt = _floor_to_second(end_dt)
    start_str = _format_iso(start_dt)
    end_str = _format_iso(end_dt)

    url = _runs_url(owner, repo)

    def page_params(page: int) -> dict[str, Any]:
        return _runs_query_params(branch, start_str, end_str, RUNS_PER_PAGE, page)

    stats.api_requests += 1
    first_resp = await client.get(url, params=page_params(1))
    data = first_resp.json()
    total_count = data.get("total_count", 0)
    page_runs = data.get("workflow_runs", [])

    saturated = total_count >= threshold_ceiling
    interval_seconds = int((end_dt - start_dt).total_seconds())

    if saturated and interval_seconds >= 1:
        logger.info(
            "Interval %s..%s for %s/%s exceeded limit (total_count=%d). Applying parallel adaptive slicing.",
            start_str,
            end_str,
            owner,
            repo,
            total_count,
        )
        bisection_events.append(
            {
                "start": start_str,
                "end": end_str,
                "total_count": total_count,
            }
        )

        mid_dt = start_dt + timedelta(seconds=interval_seconds // 2)
        sub_intervals: list[tuple[datetime, datetime]] = [
            (start_dt, mid_dt),
            (mid_dt + timedelta(seconds=1), end_dt),
        ]

        # Query all sub-intervals in parallel!
        tasks = [
            _fetch_runs_for_interval(
                client=client,
                owner=owner,
                repo=repo,
                branch=branch,
                start_dt=s,
                end_dt=e,
                threshold_ceiling=threshold_ceiling,
                bisection_events=bisection_events,
                stats=stats,
            )
            for s, e in sub_intervals
        ]

        sub_results = await asyncio.gather(*tasks)
        combined: list[dict[str, Any]] = []
        for res in sub_results:
            combined.extend(res)
        return combined

    # Paginate the remaining pages in parallel (the API serves at most 10 pages)
    all_runs = list(page_runs)
    num_pages = (total_count + RUNS_PER_PAGE - 1) // RUNS_PER_PAGE

    if num_pages > 1:
        max_page = min(num_pages, MAX_READABLE_PAGES)
        stats.api_requests += max_page - 1
        page_tasks = [client.get(url, params=page_params(p)) for p in range(2, max_page + 1)]
        page_responses = await asyncio.gather(*page_tasks)
        for resp in page_responses:
            all_runs.extend(resp.json().get("workflow_runs", []))

    if saturated:
        # Smallest unit (1 s) and still >= ceiling: read what is readable and report.
        stats.unsplittable_intervals.append(
            {
                "start": start_str,
                "end": end_str,
                "total_count": total_count,
                "runs_read": len(all_runs),
            }
        )

    return all_runs


async def collect_workflow_runs(
    owner: str,
    repo: str,
    client: GitHubClient | None = None,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    branch: str | None = None,
    save_to_parquet: bool = True,
    output_dir: str | Path = "dados/runs",
    threshold_ceiling: int = 1000,
) -> WorkflowRunsCollectionResult:
    """Collect push workflow runs for the default branch across observation window in parallel."""
    owns_client = False
    if client is None:
        client = GitHubClient()
        owns_client = True

    try:
        resolved_branch = await _resolve_default_branch(client, owner, repo, branch)

        if end_date is None:
            end_dt = datetime.now(timezone.utc)
        else:
            # A date-only end_date means the end of that day (see `parse_window_end`).
            end_dt = _to_utc_datetime(parse_window_end(end_date))  # type: ignore[arg-type]

        if start_date is None:
            start_dt = end_dt.replace(year=end_dt.year - 1)
        else:
            start_dt = _to_utc_datetime(start_date)

        monthly_intervals = split_window_into_months(start_dt, end_dt)
        bisection_events: list[dict[str, Any]] = []
        stats = _FetchStats()

        # Fetch all monthly intervals concurrently!
        month_tasks = [
            _fetch_runs_for_interval(
                client=client,
                owner=owner,
                repo=repo,
                branch=resolved_branch,
                start_dt=slice_start,
                end_dt=slice_end,
                threshold_ceiling=threshold_ceiling,
                bisection_events=bisection_events,
                stats=stats,
            )
            for slice_start, slice_end in monthly_intervals
        ]

        monthly_results = await asyncio.gather(*month_tasks)

        if stats.unsplittable_intervals:
            # Once per repository: residual case, intervals of 1 s with >= ceiling runs.
            logger.warning(
                "%s/%s: %d one-second interval(s) still report total_count >= %d and "
                "cannot be split further; only the first %d runs of each are readable "
                "(sum of total_count=%d, runs read=%d). First: %s",
                owner,
                repo,
                len(stats.unsplittable_intervals),
                threshold_ceiling,
                MAX_READABLE_PAGES * RUNS_PER_PAGE,
                sum(e["total_count"] for e in stats.unsplittable_intervals),
                sum(e["runs_read"] for e in stats.unsplittable_intervals),
                stats.unsplittable_intervals[0]["start"],
            )

        # Deduplicate runs by id
        raw_runs_by_id: dict[int | str, dict[str, Any]] = {}
        for slice_runs in monthly_results:
            for run_dict in slice_runs:
                run_id = run_dict.get("id")
                if run_id is not None:
                    raw_runs_by_id[run_id] = run_dict

        workflow_runs = [_workflow_run_from_raw(r) for r in raw_runs_by_id.values()]
        valid_runs_count = sum(1 for r in workflow_runs if _is_valid_run(r))

        passed_t4 = valid_runs_count >= 50

        parquet_path: Path | None = None
        if save_to_parquet:
            dest_file = Path(output_dir) / f"{owner}__{repo}.parquet"
            parquet_path = save_runs_to_parquet(
                workflow_runs, owner=owner, repo=repo, output_path=dest_file
            )

        return WorkflowRunsCollectionResult(
            owner=owner,
            repo=repo,
            branch=resolved_branch,
            runs=workflow_runs,
            total_runs=len(workflow_runs),
            valid_runs_count=valid_runs_count,
            passed_t4=passed_t4,
            bisection_events=bisection_events,
            parquet_path=parquet_path,
            api_requests=stats.api_requests,
            unsplittable_intervals=stats.unsplittable_intervals,
        )

    finally:
        if owns_client:
            await client.close()


async def count_runs_in_interval(
    client: GitHubClient,
    owner: str,
    repo: str,
    branch: str,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    """`total_count` of the runs of a closed interval, asking for a single run (1 request).

    Same filters as the collection (default branch, ``event=push``, ``created``
    range in whole seconds); only ``per_page`` changes.
    """
    start_str = _format_iso(_floor_to_second(start_dt))
    end_str = _format_iso(_floor_to_second(end_dt))
    resp = await client.get(
        _runs_url(owner, repo), params=_runs_query_params(branch, start_str, end_str, 1, 1)
    )
    return int(resp.json().get("total_count", 0))


def _with_api_workflow_id(run: WorkflowRun) -> WorkflowRun:
    """Give a stored run the `workflow_id` type the API returns (int).

    Parquet keeps `workflow_id` as a string while the API payload has an integer; mixing
    both would split one workflow in two groups in the CFR/recovery calculations.
    """
    if isinstance(run.workflow_id, str) and run.workflow_id.isdigit():
        return dataclasses.replace(run, workflow_id=int(run.workflow_id))
    return run


def _in_interval(run: WorkflowRun, start_dt: datetime, end_dt: datetime) -> bool:
    started = _floor_to_second(_to_utc_datetime(run.run_started_at))
    return _floor_to_second(start_dt) <= started <= _floor_to_second(end_dt)


async def reconcile_workflow_runs(
    owner: str,
    repo: str,
    previous_runs: Sequence[WorkflowRun],
    client: GitHubClient,
    start_date: datetime | str,
    previous_end_date: datetime | str,
    end_date: datetime | str,
    branch: str,
    threshold_ceiling: int = 1000,
) -> WorkflowRunsCollectionResult:
    """Rebuild the runs of the window from a previous collection, spending few requests.

    `previous_runs` were collected for ``[start_date, previous_end_date]``. The
    previous window is cut in the same calendar-month intervals as the full
    collection; for each one the API is asked only for ``total_count``
    (`count_runs_in_interval`):

    - equal to the number of previous runs in the interval: the previous runs
      are kept (a full re-collection, with any slicing, returns that same set);
    - different (interval truncated at 1,000, deleted or expired runs, runs
      that moved across the boundary): the interval is fetched again with the
      collector's recursive splitting (`_fetch_runs_for_interval`).

    The tail ``(previous_end_date, end_date]`` is always fetched with the same
    collector. Returns the same result type as `collect_workflow_runs`, with
    `reconciliation` describing every interval (action ``kept``/``refetched``/``tail``).

    Runs are matched to an interval by ``run_started_at`` (the stored
    timestamp) while the API filters on ``created_at``; a re-run of an old run
    makes the counts differ, which only costs a re-fetch of that interval.
    """
    start_dt = _to_utc_datetime(start_date)
    prev_end_dt = _to_utc_datetime(previous_end_date)
    end_dt = _to_utc_datetime(parse_window_end(end_date))  # type: ignore[arg-type]

    bisection_events: list[dict[str, Any]] = []
    stats = _FetchStats()

    intervals = split_window_into_months(start_dt, prev_end_dt)
    tail: tuple[datetime, datetime] | None = None
    tail_start = _floor_to_second(prev_end_dt) + timedelta(seconds=1)
    if tail_start <= _floor_to_second(end_dt):
        tail = (tail_start, end_dt)

    async def handle(slice_start: datetime, slice_end: datetime) -> tuple[list[WorkflowRun], list[dict[str, Any]], dict[str, Any]]:
        committed = [
            _with_api_workflow_id(r)
            for r in previous_runs
            if _in_interval(r, slice_start, slice_end)
        ]
        stats.api_requests += 1
        api_count = await count_runs_in_interval(client, owner, repo, branch, slice_start, slice_end)
        entry: dict[str, Any] = {
            "start": _format_iso(_floor_to_second(slice_start)),
            "end": _format_iso(_floor_to_second(slice_end)),
            "previous_count": len(committed),
            "api_count": api_count,
        }
        if api_count == len(committed):
            entry["action"] = "kept"
            return committed, [], entry
        raw = await _fetch_runs_for_interval(
            client=client,
            owner=owner,
            repo=repo,
            branch=branch,
            start_dt=slice_start,
            end_dt=slice_end,
            threshold_ceiling=threshold_ceiling,
            bisection_events=bisection_events,
            stats=stats,
        )
        entry["action"] = "refetched"
        entry["fetched_count"] = len(raw)
        return [], raw, entry

    async def fetch_tail(slice_start: datetime, slice_end: datetime) -> tuple[list[WorkflowRun], list[dict[str, Any]], dict[str, Any]]:
        raw = await _fetch_runs_for_interval(
            client=client,
            owner=owner,
            repo=repo,
            branch=branch,
            start_dt=slice_start,
            end_dt=slice_end,
            threshold_ceiling=threshold_ceiling,
            bisection_events=bisection_events,
            stats=stats,
        )
        entry = {
            "start": _format_iso(_floor_to_second(slice_start)),
            "end": _format_iso(_floor_to_second(slice_end)),
            "action": "tail",
            "fetched_count": len(raw),
        }
        return [], raw, entry

    tasks = [handle(s, e) for s, e in intervals]
    if tail is not None:
        tasks.append(fetch_tail(*tail))
    outcomes = await asyncio.gather(*tasks)

    by_id: dict[int | str, WorkflowRun] = {}
    reconciliation: list[dict[str, Any]] = []
    for kept_runs, raw_runs, entry in outcomes:
        reconciliation.append(entry)
        for run in kept_runs:
            by_id[run.id] = run  # type: ignore[index]
        for raw in raw_runs:
            if raw.get("id") is not None:
                by_id[raw["id"]] = _workflow_run_from_raw(raw)

    workflow_runs = list(by_id.values())
    valid_runs_count = sum(1 for r in workflow_runs if _is_valid_run(r))
    return WorkflowRunsCollectionResult(
        owner=owner,
        repo=repo,
        branch=branch,
        runs=workflow_runs,
        total_runs=len(workflow_runs),
        valid_runs_count=valid_runs_count,
        passed_t4=valid_runs_count >= 50,
        bisection_events=bisection_events,
        api_requests=stats.api_requests,
        unsplittable_intervals=stats.unsplittable_intervals,
        reconciliation=reconciliation,
    )

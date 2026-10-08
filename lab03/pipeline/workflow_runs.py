"""Collector for GitHub Actions workflow runs on the default branch with temporal bisection and Parquet storage."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
import logging
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from metricas.schemas import WorkflowRun, _parse_datetime
from metricas.stability import ConclusionCategory, classify_conclusion
from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)


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
    """Split an observation window into contiguous calendar-month intervals.

    Each interval spans from start to end (inclusive/contiguous) in UTC.
    """
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

        # Move to the very start of the next month (or next microsecond)
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


def _resolve_default_branch(
    client: GitHubClient, owner: str, repo: str, branch: str | None
) -> str:
    """Resolve the default branch, querying the GitHub API if not provided."""
    if branch:
        return branch

    resp = client.get(f"/repos/{owner}/{repo}")
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


def _fetch_runs_for_interval(
    client: GitHubClient,
    owner: str,
    repo: str,
    branch: str,
    start_dt: datetime,
    end_dt: datetime,
    threshold_ceiling: int,
    min_interval_seconds: float,
    bisection_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fetch runs for a time interval with recursive bisection on total_count >= threshold_ceiling."""
    start_str = _format_iso(start_dt)
    end_str = _format_iso(end_dt)
    date_filter = f"{start_str}..{end_str}"

    url = f"/repos/{owner}/{repo}/actions/runs"
    params = {
        "branch": branch,
        "event": "push",
        "created": date_filter,
        "per_page": 100,
        "page": 1,
    }

    first_resp = client.get(url, params=params)
    data = first_resp.json()
    total_count = data.get("total_count", 0)
    page_runs = data.get("workflow_runs", [])

    interval_duration = (end_dt - start_dt).total_seconds()

    # If ceiling reached and interval can still be meaningfully divided:
    if total_count >= threshold_ceiling and interval_duration > min_interval_seconds:
        logger.warning(
            "Interval %s to %s for %s/%s hit GitHub Actions limit (total_count=%d >= %d). Bisecting interval.",
            start_str,
            end_str,
            owner,
            repo,
            total_count,
            threshold_ceiling,
        )
        bisection_events.append(
            {
                "start": start_str,
                "end": end_str,
                "total_count": total_count,
            }
        )

        mid_dt = start_dt + (end_dt - start_dt) / 2

        left_runs = _fetch_runs_for_interval(
            client=client,
            owner=owner,
            repo=repo,
            branch=branch,
            start_dt=start_dt,
            end_dt=mid_dt,
            threshold_ceiling=threshold_ceiling,
            min_interval_seconds=min_interval_seconds,
            bisection_events=bisection_events,
        )

        right_runs = _fetch_runs_for_interval(
            client=client,
            owner=owner,
            repo=repo,
            branch=branch,
            start_dt=mid_dt,
            end_dt=end_dt,
            threshold_ceiling=threshold_ceiling,
            min_interval_seconds=min_interval_seconds,
            bisection_events=bisection_events,
        )

        return left_runs + right_runs

    # Under ceiling, or cannot be divided further: paginate all available pages
    all_runs = list(page_runs)
    num_pages = (total_count + 99) // 100

    # Paginate remaining pages if any
    for page in range(2, num_pages + 1):
        if page > 10 and total_count >= threshold_ceiling:
            # GitHub REST Actions runs API caps pagination at 10 pages (1,000 runs)
            break
        page_params = {
            "branch": branch,
            "event": "push",
            "created": date_filter,
            "per_page": 100,
            "page": page,
        }
        resp = client.get(url, params=page_params)
        runs_on_page = resp.json().get("workflow_runs", [])
        if not runs_on_page:
            break
        all_runs.extend(runs_on_page)

    return all_runs


def collect_workflow_runs(
    owner: str,
    repo: str,
    client: GitHubClient | None = None,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    branch: str | None = None,
    save_to_parquet: bool = True,
    output_dir: str | Path = "dados/runs",
    threshold_ceiling: int = 1000,
    min_interval_seconds: float = 3600.0,
) -> WorkflowRunsCollectionResult:
    """Collect all push workflow runs for the default branch across the observation window.

    Applies calendar-month slicing and recursive bisection whenever total_count >= 1000.
    Deduplicates runs by id, computes valid runs for T4, and optionally writes to Parquet.
    """
    owns_client = False
    if client is None:
        client = GitHubClient()
        owns_client = True

    try:
        resolved_branch = _resolve_default_branch(client, owner, repo, branch)

        # Default window: 12 months up to now if not provided
        if end_date is None:
            end_dt = datetime.now(timezone.utc)
        else:
            end_dt = _to_utc_datetime(end_date)

        if start_date is None:
            start_dt = end_dt.replace(year=end_dt.year - 1)
        else:
            start_dt = _to_utc_datetime(start_date)

        monthly_intervals = split_window_into_months(start_dt, end_dt)

        bisection_events: list[dict[str, Any]] = []
        raw_runs_by_id: dict[int | str, dict[str, Any]] = {}

        for slice_start, slice_end in monthly_intervals:
            slice_runs = _fetch_runs_for_interval(
                client=client,
                owner=owner,
                repo=repo,
                branch=resolved_branch,
                start_dt=slice_start,
                end_dt=slice_end,
                threshold_ceiling=threshold_ceiling,
                min_interval_seconds=min_interval_seconds,
                bisection_events=bisection_events,
            )

            for run_dict in slice_runs:
                run_id = run_dict.get("id")
                if run_id is not None:
                    raw_runs_by_id[run_id] = run_dict

        # Convert to WorkflowRun dataclasses and classify validity
        workflow_runs: list[WorkflowRun] = []
        valid_runs_count = 0

        for r_dict in raw_runs_by_id.values():
            started = r_dict.get("run_started_at") or r_dict.get("created_at")
            updated = r_dict.get("updated_at") or started
            conclusion = r_dict.get("conclusion")

            wf_run = WorkflowRun(
                id=r_dict.get("id"),
                workflow_id=r_dict.get("workflow_id", ""),
                conclusion=conclusion,
                run_started_at=started,
                updated_at=updated,
                name=r_dict.get("name"),
                event=r_dict.get("event"),
                branch=r_dict.get("head_branch"),
            )
            workflow_runs.append(wf_run)

            cat = classify_conclusion(conclusion)
            if cat in (ConclusionCategory.SUCCESS, ConclusionCategory.FAILURE):
                valid_runs_count += 1

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
        )

    finally:
        if owns_client:
            client.close()

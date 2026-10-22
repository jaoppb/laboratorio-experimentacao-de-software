"""Collection of releases and tags (deploy units) from the GitHub REST API (Async)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.parquet as pq

from metricas.schemas import Commit, Release, _parse_datetime, parse_window_end
from pipeline.commit_store import (
    COMMITS_DIR,
    distinct_commits,
    save_commits_to_parquet,
    write_parquet_batches,
)
from pipeline.commits import ComparisonStatus, ReleaseCommits

if TYPE_CHECKING:
    from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)

PER_PAGE = 100

def parse_release(payload: dict[str, Any]) -> Release | None:
    """Convert a release JSON object from the API into a `Release`."""
    if payload.get("draft") or not payload.get("published_at"):
        return None
    return Release(
        tag_name=payload["tag_name"],
        published_at=payload["published_at"],
        draft=False,
        prerelease=bool(payload.get("prerelease", False)),
    )


def parse_graphql_release(node: dict[str, Any]) -> Release | None:
    """Convert a release node from GraphQL API into a `Release`."""
    if node.get("isDraft") or not node.get("publishedAt"):
        return None
    return Release(
        tag_name=node["tagName"],
        published_at=node["publishedAt"],
        draft=False,
        prerelease=bool(node.get("isPrerelease", False)),
    )


async def fetch_releases_graphql(
    client: GitHubClient,
    owner: str,
    repo: str,
    window_start: datetime | str | None = None,
) -> tuple[dict[str, Any], list[Release]]:
    """Fetch repository metadata and releases via GraphQL, paginating only if needed."""
    from pipeline.graphql.loader import load_query

    query = load_query("repo_details.graphql")
    start = _parse_datetime(window_start)
    releases: list[Release] = []

    after_cursor: str | None = None
    repo_data: dict[str, Any] = {}

    while True:
        variables: dict[str, Any] = {"owner": owner, "name": repo}
        if after_cursor:
            variables["after"] = after_cursor
        resp_data = await client.graphql(query, variables=variables)
        repo_data = resp_data.get("data", {}).get("repository") or {}
        if not repo_data:
            break

        rel_block = repo_data.get("releases") or {}
        nodes = rel_block.get("nodes") or []
        page_info = rel_block.get("pageInfo") or {}

        reached_anchor = False
        for node in nodes:
            rel = parse_graphql_release(node)
            if rel is None:
                continue
            releases.append(rel)
            if start is not None and not rel.prerelease and rel.published_at < start:
                reached_anchor = True

        has_next = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        if reached_anchor or not has_next or not end_cursor:
            break

        after_cursor = end_cursor

    sorted_releases = sorted(releases, key=lambda r: r.published_at)
    return repo_data, sorted_releases


async def fetch_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    window_start: datetime | str | None = None,
    use_graphql: bool = False,
) -> list[Release]:
    """Fetch the published (non-draft) releases of a repository, oldest first."""
    if use_graphql:
        try:
            _, rels = await fetch_releases_graphql(
                client=client, owner=owner, repo=repo, window_start=window_start
            )
            return rels
        except Exception as exc:
            logger.debug(
                "GraphQL fetch_releases failed for %s/%s (%s), falling back to REST",
                owner,
                repo,
                exc,
            )

    start = _parse_datetime(window_start)
    releases: list[Release] = []

    async for response in client.get_paginated(
        f"/repos/{owner}/{repo}/releases", params={"per_page": PER_PAGE}
    ):
        reached_anchor = False
        for item in response.json():
            release = parse_release(item)
            if release is None:
                continue
            releases.append(release)
            if (
                start is not None
                and not release.prerelease
                and release.published_at < start
            ):
                reached_anchor = True
        if reached_anchor:
            break

    return sorted(releases, key=lambda r: r.published_at)


async def fetch_tags(
    client: GitHubClient,
    owner: str,
    repo: str,
    max_tags: int | None = None,
) -> list[Release]:
    """Fetch the tags of a repository as deploy units (RQ 07 variant), oldest first."""
    tags: list[tuple[str, str]] = []
    async for response in client.get_paginated(
        f"/repos/{owner}/{repo}/tags", params={"per_page": PER_PAGE}
    ):
        for item in response.json():
            tags.append((item["name"], item["commit"]["sha"]))
            if max_tags is not None and len(tags) >= max_tags:
                break
        if max_tags is not None and len(tags) >= max_tags:
            break

    dates_by_sha: dict[str, datetime] = {}
    result: list[Release] = []
    for name, sha in tags:
        if sha not in dates_by_sha:
            resp = await client.get(f"/repos/{owner}/{repo}/commits/{sha}")
            commit = resp.json()
            dates_by_sha[sha] = _parse_datetime(commit["commit"]["author"]["date"])  # type: ignore
        result.append(Release(tag_name=name, published_at=dates_by_sha[sha]))

    return sorted(result, key=lambda r: r.published_at)


def deploy_units(
    releases: Sequence[Release], include_prerelease: bool = False
) -> list[Release]:
    """Filter releases by the deploy unit definition, oldest first."""
    return sorted(
        (
            r
            for r in releases
            if not r.draft and (include_prerelease or not r.prerelease)
        ),
        key=lambda r: r.published_at,
    )


@dataclass
class WindowReleases:
    """Deploy units inside the observation window and the one right before it."""

    in_window: list[Release] = field(default_factory=list)
    anchor: Release | None = None

    @property
    def count(self) -> int:
        """Number of valid deploys in the window."""
        return len(self.in_window)

    def with_anchor(self) -> list[Release]:
        """Anchor (if any) followed by the in-window releases, oldest first."""
        return ([self.anchor] if self.anchor else []) + self.in_window


def filter_window(
    releases: Sequence[Release],
    window_start: datetime | str,
    window_end: datetime | str,
    include_prerelease: bool = False,
) -> WindowReleases:
    """Select the deploy units inside [window_start, window_end].

    A date-only `window_end` includes the whole day (see `parse_window_end`).
    """
    start = _parse_datetime(window_start)
    end = parse_window_end(window_end)
    units = deploy_units(releases, include_prerelease=include_prerelease)

    before = [r for r in units if r.published_at < start]  # type: ignore
    in_window = [r for r in units if start <= r.published_at <= end]  # type: ignore
    return WindowReleases(in_window=in_window, anchor=before[-1] if before else None)


def count_valid_releases(
    releases: Sequence[Release],
    window_start: datetime | str,
    window_end: datetime | str,
) -> int:
    """Count published, non-prerelease releases inside the window (>= 5 criterion)."""
    return filter_window(releases, window_start, window_end).count


# Rows per Parquet batch of the unit files; a batch is also closed once it
# holds this many commit SHAs, so a few huge ranges cannot make it large.
UNIT_BATCH_ROWS = 200
UNIT_BATCH_SHAS = 100_000

_RELEASES_SCHEMA = pa.schema(
    [
        ("tag_name", pa.string()),
        ("published_at", pa.timestamp("us", tz="UTC")),
        ("prerelease", pa.bool_()),
        ("previous_release", pa.string()),
        ("status", pa.string()),
        ("commits_count", pa.int64()),
        ("commit_shas", pa.list_(pa.string())),
    ]
)

_TAGS_SCHEMA = pa.schema(
    [
        ("tag_name", pa.string()),
        ("published_at", pa.timestamp("us", tz="UTC")),
        ("commit_sha", pa.string()),
        ("previous_tag", pa.string()),
        ("commits_count", pa.int64()),
        ("commit_shas", pa.list_(pa.string())),
    ]
)


def _unit_batches(
    units: Iterable[ReleaseCommits],
    columns: Sequence[str],
    row: Callable[[ReleaseCommits], tuple[Any, ...]],
    schema: pa.Schema,
    max_rows: int | None = None,
    max_shas: int | None = None,
) -> Iterator[list[pa.Array]]:
    """Group the rows of the units into batches of arrays (by row and SHA budget)."""
    max_rows = UNIT_BATCH_ROWS if max_rows is None else max_rows
    max_shas = UNIT_BATCH_SHAS if max_shas is None else max_shas
    buffers: list[list[Any]] = [[] for _ in columns]
    shas_in_batch = 0

    def flush() -> list[pa.Array]:
        return [pa.array(values, type=schema.field(name).type) for name, values in zip(columns, buffers)]

    for unit in units:
        values = row(unit)
        for buf, value in zip(buffers, values):
            buf.append(value)
        shas_in_batch += len(values[-1])
        if len(buffers[0]) >= max_rows or shas_in_batch >= max_shas:
            yield flush()
            buffers = [[] for _ in columns]
            shas_in_batch = 0
    if buffers[0]:
        yield flush()


def save_releases_to_parquet(
    release_commits: Sequence[ReleaseCommits],
    owner: str,
    repo: str,
    output_path: str | Path,
    batch_rows: int | None = None,
) -> Path:
    """Serialize evaluated window releases to a columnar Parquet file.

    One row per release; `commit_shas` lists the SHAs of the range (the commits
    themselves are in the repository's commit store, see `pipeline.commit_store`).
    Written in batches of `batch_rows` rows.
    """
    columns = [f.name for f in _RELEASES_SCHEMA]

    def row(rc: ReleaseCommits) -> tuple[Any, ...]:
        rel = rc.release
        shas = [c.sha for c in rc.commits]
        return (
            rel.tag_name,
            rel.published_at,
            rel.prerelease,
            rc.previous.tag_name if rc.previous else None,
            rc.status.value,
            len(rc.commits) if rc.status == ComparisonStatus.OK else None,
            shas,
        )

    return write_parquet_batches(
        Path(output_path),
        _RELEASES_SCHEMA,
        _unit_batches(release_commits, columns, row, _RELEASES_SCHEMA, max_rows=batch_rows),
    )


def save_tags_to_parquet(
    tag_commits: Sequence[ReleaseCommits],
    owner: str,
    repo: str,
    output_path: str | Path,
    batch_rows: int | None = None,
) -> Path:
    """Serialize evaluated window tags to a columnar Parquet file (same layout idea as releases)."""
    columns = [f.name for f in _TAGS_SCHEMA]

    def row(tc: ReleaseCommits) -> tuple[Any, ...]:
        tag = tc.release
        return (
            tag.tag_name,
            tag.published_at,
            getattr(tag, "commit_sha", None),
            tc.previous.tag_name if tc.previous else None,
            len(tc.commits),
            [c.sha for c in tc.commits],
        )

    return write_parquet_batches(
        Path(output_path),
        _TAGS_SCHEMA,
        _unit_batches(tag_commits, columns, row, _TAGS_SCHEMA, max_rows=batch_rows),
    )


def save_repository_units(
    dados_dir: str | Path,
    owner: str,
    repo: str,
    release_commits_c1: Sequence[ReleaseCommits],
    release_commits_c2: Sequence[ReleaseCommits],
    tag_commits_c3: Sequence[ReleaseCommits],
    commit_cache: Mapping[str, Commit],
) -> None:
    """Persist the three deploy-unit files and the commit store of one repository.

    The commit store goes first (it holds every commit the unit files point
    to), then `releases/`, `releases_c2/` and `tags/`. Every file is atomic.
    """
    dados = Path(dados_dir)
    name = f"{owner}__{repo}.parquet"
    store = distinct_commits(
        release_commits_c1, release_commits_c2, tag_commits_c3, known=commit_cache
    )
    save_commits_to_parquet(store.values(), dados / COMMITS_DIR / name)
    save_releases_to_parquet(release_commits_c1, owner, repo, dados / "releases" / name)
    save_releases_to_parquet(release_commits_c2, owner, repo, dados / "releases_c2" / name)
    save_tags_to_parquet(tag_commits_c3, owner, repo, dados / "tags" / name)

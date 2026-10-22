"""Normalized commit store of a repository and the one reader of the unit files.

Layout (Issue #56, memory bound of the regeneration):

- `dados/commits/{owner}__{repo}.parquet`: one row per *distinct* commit of the
  repository (`sha`, `committed_at` ISO string, `message`, `full_message`),
  shared by C1, C2 and C3;
- `dados/releases/`, `dados/releases_c2/` and `dados/tags/`: one row per deploy
  unit with `commit_shas` (list of SHAs of the range, in `git log` order)
  instead of the commits themselves.

`load_release_commits` and `load_tag_commits` join both and return the same
`ReleaseCommits` the collection produces. Every consumer reads through them;
the old layout (nested `commits` struct) is not supported.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from metricas.schemas import Commit, Release
from pipeline.commits import ComparisonStatus, ReleaseCommits

COMMITS_DIR = "commits"
COMMIT_BATCH_ROWS = 20_000
READ_BATCH_ROWS = 200

COMMITS_SCHEMA = pa.schema(
    [
        ("sha", pa.string()),
        ("committed_at", pa.string()),
        ("message", pa.string()),
        ("full_message", pa.string()),
    ]
)


class CommitStoreError(Exception):
    """The unit files and the commit store disagree (a SHA without its commit)."""


def commit_store_file(dados_dir: Path | str, full_name: str) -> Path:
    """`dados/commits/{owner}__{repo}.parquet` of `owner/repo`."""
    return Path(dados_dir) / COMMITS_DIR / f"{full_name.replace('/', '__')}.parquet"


def commits_dir_for(units_dir: Path | str) -> Path:
    """Commit store directory next to a unit directory (`releases/`, `tags/`, ...)."""
    return Path(units_dir).parent / COMMITS_DIR


def _iso(value: object) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)  # type: ignore[union-attr]


def write_parquet_batches(
    path: Path,
    schema: pa.Schema,
    batches: Iterable[list[pa.Array] | pa.Table],
) -> Path:
    """Write `batches` to `path` with a `ParquetWriter`, one row group per batch.

    Each batch (a table, or the arrays of the schema's columns) is written and
    released before the next one is built. The file appears atomically: it is
    written to `<name>.parquet.tmp` and renamed, and the temporary file is
    removed if anything fails. With no batch the file has the schema and no rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".parquet.tmp")
    try:
        with pq.ParquetWriter(tmp_path, schema, compression="snappy") as writer:
            for batch in batches:
                table = (
                    batch
                    if isinstance(batch, pa.Table)
                    else pa.Table.from_arrays(batch, schema=schema)
                )
                writer.write_table(table)
                del batch, table
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


def distinct_commits(
    *unit_lists: Iterable[ReleaseCommits], known: Mapping[str, Commit] | None = None
) -> dict[str, Commit]:
    """`{sha: Commit}` of `known` plus every commit of the given units (first one seen wins).

    The writers use it with the repository's SHA table as `known`, so the commit
    store holds every SHA the unit files point to even if some commits did not
    pass through the table.
    """
    table: dict[str, Commit] = dict(known) if known else {}
    for units in unit_lists:
        for unit in units:
            for commit in unit.commits:
                table.setdefault(commit.sha, commit)
    return table


def save_commits_to_parquet(
    commits: Iterable[Commit],
    output_path: str | Path,
    batch_rows: int = COMMIT_BATCH_ROWS,
) -> Path:
    """Write the commit store (one row per commit, in iteration order) in batches, atomically."""
    def batches() -> Iterator[list[pa.Array]]:
        sha: list[str] = []
        committed_at: list[str] = []
        message: list[str] = []
        full_message: list[str | None] = []
        for commit in commits:
            sha.append(commit.sha)
            committed_at.append(_iso(commit.committed_at))
            message.append(commit.message or "")
            full_message.append(commit.full_message)
            if len(sha) >= batch_rows:
                yield _arrays(sha, committed_at, message, full_message)
                sha, committed_at, message, full_message = [], [], [], []
        if sha:
            yield _arrays(sha, committed_at, message, full_message)

    return write_parquet_batches(Path(output_path), COMMITS_SCHEMA, batches())


def _arrays(*columns: list) -> list[pa.Array]:
    return [pa.array(values, type=field.type) for values, field in zip(columns, COMMITS_SCHEMA)]


def load_commit_store(path: str | Path) -> dict[str, Commit]:
    """Read a commit store into `{sha: Commit}` (insertion order = file order)."""
    table: dict[str, Commit] = {}
    for batch in pq.ParquetFile(path).iter_batches(batch_size=COMMIT_BATCH_ROWS):
        for record in batch.to_pylist():
            table[record["sha"]] = Commit.from_record(record)
    return table


def _resolve_commits(commits: Mapping[str, Commit] | Path | str) -> Mapping[str, Commit]:
    return commits if isinstance(commits, Mapping) else load_commit_store(commits)


def _iter_rows(path: Path | str) -> Iterator[dict]:
    parquet = pq.ParquetFile(path)
    if "commit_shas" not in parquet.schema_arrow.names:
        raise CommitStoreError(
            f"{path} is in the old layout (nested commits, no commit_shas); regenerate it with "
            "`python -m pipeline.persist_releases` / `python -m analises.persistir_amostra_ouro` "
            "(see dados/README.md)"
        )
    for batch in parquet.iter_batches(batch_size=READ_BATCH_ROWS):
        yield from batch.to_pylist()


def _join(
    row: dict, table: Mapping[str, Commit], commits_path: object
) -> list[Commit]:
    try:
        return [table[sha] for sha in row["commit_shas"] or []]
    except KeyError as exc:
        raise CommitStoreError(
            f"commit {exc.args[0]} of {row['tag_name']} is not in the commit store {commits_path}"
        ) from None


def load_release_commits(
    path: str | Path, commits: Mapping[str, Commit] | Path | str
) -> list[ReleaseCommits]:
    """Rebuild the `ReleaseCommits` of a `releases/` or `releases_c2/` file.

    `commits` is the commit store file of the repository, or its already loaded
    table (load it once per repository when reading several files). Only what
    the metrics need is faithful: the release (tag, publication date,
    pre-release flag), the status and the commits. `previous` stays None because
    the file keeps only the previous tag *name*, available as
    `ReleaseCommits.previous_tag_name`.
    """
    table = _resolve_commits(commits)
    result: list[ReleaseCommits] = []
    for row in _iter_rows(path):
        release = Release(
            tag_name=row["tag_name"],
            published_at=row["published_at"],
            prerelease=bool(row["prerelease"]),
        )
        status = ComparisonStatus(row["status"])
        unit_commits = _join(row, table, commits) if status == ComparisonStatus.OK else []
        result.append(
            ReleaseCommits(
                release, None, status, unit_commits, previous_tag_name=row["previous_release"]
            )
        )
    return result


def load_tag_commits(
    path: str | Path, commits: Mapping[str, Commit] | Path | str
) -> list[ReleaseCommits]:
    """Rebuild the `ReleaseCommits` of the C3 tags of a repository from its `tags/` file.

    The file does not keep the comparison status: a tag with a previous tag is
    loaded as `OK` (even when the original comparison was `NOT_FOUND`, which is
    saved with no commits) and one without as `FIRST_RELEASE`. The columns that
    use it only need the window count and the commit lead times, which are the
    same either way (no commits contribute to the median).
    """
    table = _resolve_commits(commits)
    result: list[ReleaseCommits] = []
    for row in _iter_rows(path):
        tag = Release(
            tag_name=row["tag_name"],
            published_at=row["published_at"],
            commit_sha=row["commit_sha"],
        )
        if row["previous_tag"] is None:
            result.append(ReleaseCommits(tag, None, ComparisonStatus.FIRST_RELEASE))
            continue
        result.append(
            ReleaseCommits(
                tag,
                None,
                ComparisonStatus.OK,
                _join(row, table, commits),
                previous_tag_name=row["previous_tag"],
            )
        )
    return result

"""Batched Parquet writers, the commit store and the unified reader (Issue #56)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from metricas.lead_time import calculate_lead_time
from metricas.schemas import Commit, Release
from pipeline import commit_store
from pipeline.backfill_cfr_b import apply_cfr_b
from pipeline.commit_store import (
    CommitStoreError,
    commit_store_file,
    distinct_commits,
    load_commit_store,
    load_release_commits,
    load_tag_commits,
    save_commits_to_parquet,
    write_parquet_batches,
)
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.orchestrator import compute_cfr_b_columns
from pipeline.releases import (
    save_releases_to_parquet,
    save_repository_units,
    save_tags_to_parquet,
)

WINDOW_END = datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)


def _commit(i: int, message: str | None = None, full: str | None = None) -> Commit:
    return Commit(
        sha=f"{i:040x}",
        committed_at=f"2024-03-{(i % 27) + 1:02d}T10:00:00+00:00",
        message=message if message is not None else f"fix: change {i}",
        full_message=full,
    )


def _history(n_releases: int, per_range: int, overlap: int) -> list[ReleaseCommits]:
    """Chain of releases whose consecutive ranges share `overlap` commits."""
    units = [
        ReleaseCommits(
            Release(tag_name="v0", published_at="2024-01-01T00:00:00Z"),
            None,
            ComparisonStatus.FIRST_RELEASE,
        )
    ]
    for r in range(1, n_releases):
        first = max(0, (r - 1) * (per_range - overlap))
        units.append(
            ReleaseCommits(
                Release(tag_name=f"v{r}", published_at=f"2024-{(r % 11) + 1:02d}-15T00:00:00Z"),
                units[-1].release,
                ComparisonStatus.OK,
                [_commit(first + k) for k in range(per_range)],
            )
        )
    return units


# ------------------------------------------------------------- batched writers


def test_releases_are_written_in_several_batches(tmp_path):
    units = _history(n_releases=11, per_range=3, overlap=1)
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet", batch_rows=4)

    assert pq.ParquetFile(out).metadata.num_row_groups == 3  # 4 + 4 + 3 rows
    table = pq.read_table(out)
    assert table.num_rows == 11
    assert table.column_names == [
        "tag_name", "published_at", "prerelease", "previous_release", "status",
        "commits_count", "commit_shas",
    ]  # fmt: skip
    assert table.schema.field("commit_shas").type == pa.list_(pa.string())
    assert table["commits_count"].to_pylist()[1:] == [3] * 10
    assert table["commit_shas"].to_pylist()[1] == [c.sha for c in units[1].commits]
    assert not list(tmp_path.glob("*.tmp"))


def test_batches_also_close_on_a_sha_budget(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.releases.UNIT_BATCH_SHAS", 5)
    units = _history(n_releases=6, per_range=3, overlap=0)
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet")
    # 3 SHAs per OK unit: a batch closes as soon as it holds 5 or more
    assert pq.ParquetFile(out).metadata.num_row_groups > 1
    assert pq.read_table(out).num_rows == 6


def test_writers_accept_empty_input(tmp_path):
    releases = save_releases_to_parquet([], "o", "r", tmp_path / "r.parquet")
    tags = save_tags_to_parquet([], "o", "r", tmp_path / "t.parquet")
    store = save_commits_to_parquet([], tmp_path / "c.parquet")

    assert pq.read_table(releases).num_rows == 0
    assert "commit_shas" in pq.read_table(releases).column_names
    assert pq.read_table(tags).num_rows == 0
    assert pq.read_table(store).num_rows == 0
    assert load_release_commits(releases, store) == []
    assert load_tag_commits(tags, store) == []


def test_tags_are_written_in_batches_with_shas_only(tmp_path):
    units = _history(n_releases=7, per_range=2, overlap=1)
    for unit in units:
        unit.release.commit_sha = f"tag-{unit.release.tag_name}"
    out = save_tags_to_parquet(units, "o", "r", tmp_path / "t.parquet", batch_rows=3)

    assert pq.ParquetFile(out).metadata.num_row_groups == 3
    table = pq.read_table(out)
    assert table.column_names == [
        "tag_name", "published_at", "commit_sha", "previous_tag", "commits_count", "commit_shas",
    ]  # fmt: skip
    assert table["commit_sha"].to_pylist()[2] == "tag-v2"
    assert table["commits_count"].to_pylist() == [0] + [2] * 6


def test_commit_store_is_written_in_batches_with_the_documented_schema(tmp_path):
    commits = [_commit(i, full=None if i % 2 else f"fix: change {i}\n\nbody") for i in range(25)]
    out = save_commits_to_parquet(commits, tmp_path / "c.parquet", batch_rows=10)

    assert pq.ParquetFile(out).metadata.num_row_groups == 3
    table = pq.read_table(out)
    assert table.schema.equals(
        pa.schema(
            [
                ("sha", pa.string()),
                ("committed_at", pa.string()),
                ("message", pa.string()),
                ("full_message", pa.string()),
            ]
        )
    )
    assert table["sha"].to_pylist() == [c.sha for c in commits]
    assert table["committed_at"][0].as_py() == "2024-03-01T10:00:00+00:00"
    assert table["full_message"].null_count == 12
    assert load_commit_store(out) == {c.sha: c for c in commits}


def test_atomic_write_keeps_the_previous_file_and_removes_the_temporary_on_failure(tmp_path):
    path = tmp_path / "c.parquet"
    save_commits_to_parquet([_commit(1)], path)
    before = path.read_bytes()

    def exploding():
        yield [pa.array(["x"]), pa.array(["y"]), pa.array(["z"]), pa.array([None], pa.string())]
        raise RuntimeError("disk on fire")

    with pytest.raises(RuntimeError):
        write_parquet_batches(path, commit_store.COMMITS_SCHEMA, exploding())

    assert path.read_bytes() == before  # the old file is intact
    assert not list(tmp_path.glob("*.tmp"))  # and no partial file is left


def test_the_file_appears_only_at_the_end(tmp_path):
    path = tmp_path / "c.parquet"
    seen = []

    def batches():
        for i in range(3):
            seen.append((path.exists(), (tmp_path / "c.parquet.tmp").exists()))
            yield [pa.array([f"s{i}"]), pa.array(["d"]), pa.array(["m"]), pa.array([None], pa.string())]

    write_parquet_batches(path, commit_store.COMMITS_SCHEMA, batches())
    assert seen == [(False, True)] * 3
    assert path.exists() and not (tmp_path / "c.parquet.tmp").exists()


# ------------------------------------------------------------------ the reader


def test_round_trip_gives_the_same_release_commits(tmp_path):
    units = _history(n_releases=9, per_range=4, overlap=2)
    store = save_commits_to_parquet(distinct_commits(units).values(), tmp_path / "c.parquet")
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet", batch_rows=2)

    loaded = load_release_commits(out, store)

    assert [u.release for u in loaded] == [u.release for u in units]
    assert [u.status for u in loaded] == [u.status for u in units]
    assert [u.commits for u in loaded] == [u.commits for u in units]  # same order, same fields
    assert [u.previous_name for u in loaded] == [u.previous_name for u in units]
    assert [u.previous_name for u in loaded][:2] == [None, "v0"]
    assert [u.previous for u in loaded] == [None] * len(units)  # only the name is stored


def test_loaded_units_share_one_commit_object_per_sha(tmp_path):
    units = _history(n_releases=6, per_range=4, overlap=3)
    store = save_commits_to_parquet(distinct_commits(units).values(), tmp_path / "c.parquet")
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet")

    loaded = load_release_commits(out, store)

    ids = {id(c) for u in loaded for c in u.commits}
    assert len(ids) == len({c.sha for u in units for c in u.commits})


def test_reader_takes_a_preloaded_table(tmp_path):
    units = _history(n_releases=4, per_range=2, overlap=1)
    store = save_commits_to_parquet(distinct_commits(units).values(), tmp_path / "c.parquet")
    r = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet")
    t = save_tags_to_parquet(units, "o", "r", tmp_path / "t.parquet")

    table = load_commit_store(store)  # once per repository
    assert load_release_commits(r, table)[2].commits is not None
    assert load_release_commits(r, table) == load_release_commits(r, store)
    assert load_tag_commits(t, table) == load_tag_commits(t, store)


def test_non_ok_units_load_without_commits(tmp_path):
    rel1 = Release(tag_name="v1", published_at="2024-03-01T00:00:00Z")
    rel2 = Release(tag_name="v2", published_at="2024-04-01T00:00:00Z")
    units = [
        ReleaseCommits(rel1, None, ComparisonStatus.FIRST_RELEASE),
        ReleaseCommits(rel2, rel1, ComparisonStatus.NOT_FOUND),
    ]
    store = save_commits_to_parquet([], tmp_path / "c.parquet")
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet")

    loaded = load_release_commits(out, store)
    assert [u.status for u in loaded] == [ComparisonStatus.FIRST_RELEASE, ComparisonStatus.NOT_FOUND]
    assert all(u.commits == [] and u.commits_or_none is None for u in loaded)
    assert loaded[1].previous_name == "v1"


def test_tag_reader_keeps_the_documented_status_rule(tmp_path):
    t1 = Release(tag_name="t1", published_at="2024-03-01T00:00:00Z", commit_sha="c1")
    t2 = Release(tag_name="t2", published_at="2024-03-11T00:00:00Z", commit_sha="c2")
    units = [
        ReleaseCommits(t1, None, ComparisonStatus.FIRST_RELEASE),
        ReleaseCommits(t2, t1, ComparisonStatus.NOT_FOUND),
    ]
    store = save_commits_to_parquet([], tmp_path / "c.parquet")
    out = save_tags_to_parquet(units, "o", "r", tmp_path / "t.parquet")

    first, second = load_tag_commits(out, store)
    assert first.status == ComparisonStatus.FIRST_RELEASE and first.commits_or_none is None
    assert second.status == ComparisonStatus.OK and second.commits == []  # not_found is saved empty
    assert (first.release.commit_sha, second.release.commit_sha) == ("c1", "c2")


def test_a_sha_missing_from_the_store_is_an_error(tmp_path):
    units = _history(n_releases=3, per_range=2, overlap=0)
    store = save_commits_to_parquet(list(distinct_commits(units).values())[:1], tmp_path / "c.parquet")
    out = save_releases_to_parquet(units, "o", "r", tmp_path / "r.parquet")

    with pytest.raises(CommitStoreError, match="not in the commit store"):
        load_release_commits(out, store)


def test_the_old_nested_layout_is_rejected_with_the_way_to_regenerate(tmp_path):
    old_struct = pa.struct([("sha", pa.string()), ("committed_at", pa.string())])
    path = tmp_path / "old.parquet"
    pq.write_table(
        pa.table(
            {
                "tag_name": ["v1"],
                "commits": pa.array([[{"sha": "s", "committed_at": "x"}]], type=pa.list_(old_struct)),
            }
        ),
        path,
    )
    store = save_commits_to_parquet([], tmp_path / "c.parquet")

    with pytest.raises(CommitStoreError, match="old layout.*persist_releases"):
        load_release_commits(path, store)
    with pytest.raises(CommitStoreError, match="old layout"):
        load_tag_commits(path, store)


def test_commit_store_path_follows_the_naming_of_the_other_folders(tmp_path):
    assert commit_store_file(tmp_path, "acme/alpha") == tmp_path / "commits" / "acme__alpha.parquet"
    assert commit_store.commits_dir_for(tmp_path / "releases") == tmp_path / "commits"


# ------------------------------------------- metrics from files == from memory


def test_lead_time_and_cfr_b_from_files_equal_those_from_memory(tmp_path):
    day = "T00:00:00Z"
    r0 = Release(tag_name="v1.0.0", published_at="2024-03-01" + day)
    r1 = Release(tag_name="v1.0.1", published_at="2024-03-03" + day)
    r2 = Release(tag_name="v1.1.0", published_at="2024-04-10" + day)
    r3 = Release(tag_name="v1.1.1", published_at="2024-04-12" + day)
    shared = Commit(sha="e" * 40, committed_at="2024-02-20T00:00:00Z", message="fix: shared")
    units = [
        ReleaseCommits(r0, None, ComparisonStatus.FIRST_RELEASE),
        ReleaseCommits(
            r1, r0, ComparisonStatus.OK,
            [shared, Commit(sha="a" * 40, committed_at="2024-02-28T00:00:00Z", message="fix: x")],
        ),  # fmt: skip
        ReleaseCommits(
            r2, r1, ComparisonStatus.OK,
            [shared, Commit(sha="b" * 40, committed_at="2024-04-01T00:00:00Z", message="feat: y",
                            full_message="feat: y\n\nFixes #1")],
        ),  # fmt: skip
        ReleaseCommits(r3, r2, ComparisonStatus.NOT_FOUND),
    ]
    units[1].commits[0] = units[2].commits[0] = shared
    units_dir = tmp_path / "releases"
    save_repository_units(tmp_path, "o", "r", units, [], [], distinct_commits(units))

    loaded = load_release_commits(units_dir / "o__r.parquet", tmp_path / "commits" / "o__r.parquet")

    lead = lambda us: calculate_lead_time([(u.release, u.commits_or_none) for u in us])  # noqa: E731
    assert lead(loaded) == lead(units)
    for version in ("v1", "v1_full_message"):
        assert compute_cfr_b_columns(loaded, WINDOW_END, version) == compute_cfr_b_columns(
            units, WINDOW_END, version
        )
    record = {"releases_count_window": None}
    apply_cfr_b(record, loaded, WINDOW_END, "v1")
    assert record["cfr_b_evaluated_releases"] + record["cfr_b_censored_releases"] + record[
        "cfr_b_skipped_releases"
    ] == len(units)


def test_save_repository_units_writes_the_four_files_and_every_referenced_sha(tmp_path):
    c1 = _history(n_releases=4, per_range=3, overlap=1)
    c2 = _history(n_releases=5, per_range=3, overlap=2)
    c3 = _history(n_releases=3, per_range=2, overlap=0)
    cache = distinct_commits(c1)  # a table that misses the C2/C3 commits

    save_repository_units(tmp_path, "o", "r", c1, c2, c3, cache)

    store = load_commit_store(tmp_path / "commits" / "o__r.parquet")
    needed = {c.sha for units in (c1, c2, c3) for u in units for c in u.commits}
    assert set(store) == needed
    for folder, units in (("releases", c1), ("releases_c2", c2)):
        loaded = load_release_commits(tmp_path / folder / "o__r.parquet", store)
        assert [u.commits for u in loaded] == [u.commits for u in units]
    assert [u.commits for u in load_tag_commits(tmp_path / "tags" / "o__r.parquet", store)][1:] == [
        u.commits for u in c3[1:]
    ]
    assert sorted(p.name for p in Path(tmp_path).iterdir()) == [
        "commits", "releases", "releases_c2", "tags",
    ]  # fmt: skip

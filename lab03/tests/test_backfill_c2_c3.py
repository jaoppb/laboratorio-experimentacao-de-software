"""Tests for the pre-release/tag/C2/C3 backfill command (pipeline.backfill_c2_c3)."""

from __future__ import annotations

import csv
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import pyarrow.parquet as pq
import pytest
import yaml

from metricas.schemas import Commit, Release, _parse_datetime, parse_window_end
from pipeline import backfill_c2_c3
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.orchestrator import (
    SCHEMA_REPOSITORIOS,
    compute_c2_c3_columns,
    save_repositories_dataset,
)
from pipeline.releases import save_releases_to_parquet, save_tags_to_parquet

FULL_COLUMNS = [f.name for f in SCHEMA_REPOSITORIOS]

# Test window: 2024-01-01 to 2024-12-31 (`fim` date-only = end of the day) = 366 days
WEEKS = 366 / 7
WINDOW = (_parse_datetime("2024-01-01"), parse_window_end("2024-12-31"))


def _commit(sha: str, committed_at: str, message: str = "m") -> Commit:
    return Commit(sha=sha, committed_at=committed_at, message=message)


def _rc(tag, published, status, commits=(), previous=None, prerelease=False):
    return ReleaseCommits(
        Release(tag_name=tag, published_at=published, prerelease=prerelease),
        previous,
        status,
        list(commits),
    )


def _build_units() -> dict[str, dict]:
    """C2 releases, C3 tags and totals of three repositories."""
    v1 = Release(tag_name="v1.0", published_at="2024-03-02T00:00:00Z")
    t1 = Release(tag_name="t1", published_at="2024-03-01T00:00:00Z")
    return {
        # 1 release + 1 pre-release in C2 (lead times 24h and 48h), 2 tags in C3
        "org/full": {
            "c2": [
                _rc("v1.0", "2024-03-02T00:00:00Z", ComparisonStatus.FIRST_RELEASE),
                _rc(
                    "v1.1-rc1",
                    "2024-04-03T00:00:00Z",
                    ComparisonStatus.OK,
                    [_commit("a", "2024-04-02T00:00:00Z")],
                    previous=v1,
                    prerelease=True,
                ),
                _rc(
                    "v1.1",
                    "2024-05-03T00:00:00Z",
                    ComparisonStatus.OK,
                    [_commit("b", "2024-05-01T00:00:00Z")],
                    previous=v1,
                ),
            ],
            "c3": [
                _rc("t1", "2024-03-01T00:00:00Z", ComparisonStatus.FIRST_RELEASE),
                _rc(
                    "t2",
                    "2024-03-11T00:00:00Z",
                    ComparisonStatus.OK,
                    [_commit("c", "2024-03-10T00:00:00Z")],
                    previous=t1,
                ),
            ],
            "meta": {
                "releases_count_window": 2,
                "total_releases": 5,
                "total_prereleases": 2,
                "total_tags": 9,
            },
        },
        # Only unknown commits: no lead time in either definition, no pre-releases
        "org/nolt": {
            "c2": [_rc("v1", "2024-03-02T00:00:00Z", ComparisonStatus.FIRST_RELEASE)],
            "c3": [],
            "meta": {
                "releases_count_window": 1,
                "total_releases": 1,
                "total_prereleases": 0,
                "total_tags": 0,
            },
        },
        "org/empty": {
            "c2": [],
            "c3": [],
            "meta": {
                "releases_count_window": 0,
                "total_releases": 0,
                "total_prereleases": 0,
                "total_tags": 3,
            },
        },
    }


def _legacy_record(full_name: str, releases_count_window: int, total_releases: int) -> dict:
    owner, name = full_name.split("/")
    return {
        "owner": owner,
        "name": name,
        "full_name": full_name,
        "stars": 1234,
        "language": "Python",
        "default_branch": "main",
        "created_at": "2020-01-01T00:00:00+00:00",
        "contributors_count": 3,
        "releases_count_window": releases_count_window,
        "total_releases": total_releases,
        "deployment_frequency": 0.123456789,
        "deployment_tier": "Low",
        "lead_time_a_hours": 1.5,
        "overall_dora_score": 2,
        "overall_dora_tier": "Medium",
        "cfr_b": 0.25,
        "cfr_b_tier": "Medium",
        "cfr_b_failed_releases": 1,
        "cfr_b_evaluated_releases": 4,
        "cfr_b_censored_releases": 0,
        "cfr_b_skipped_releases": 0,
    }


@pytest.fixture
def config(tmp_path: Path) -> dict:
    return {
        "janela": {"inicio": "2024-01-01", "fim": "2024-12-31"},
        "diretorios": {
            "dados": str(tmp_path / "dados"),
            "cache": str(tmp_path / "cache"),
            "git_cache": str(tmp_path / "git"),
        },
    }


@pytest.fixture
def units() -> dict[str, dict]:
    return _build_units()


@pytest.fixture
def dataset(tmp_path: Path, units) -> list[dict]:
    """Dataset as left by the CFR (b) backfill: the eight C2/C3 columns are null."""
    dados = tmp_path / "dados"
    records = [
        _legacy_record("org/full", 2, 5),
        _legacy_record("org/nolt", 1, 1),
        _legacy_record("org/empty", 0, 0),
    ]
    save_repositories_dataset(records, dados / "repositorios.parquet", dados / "repositorios.csv")
    return records


def _persist(units, dados: Path, names) -> None:
    for name in names:
        owner, repo = name.split("/")
        paths = backfill_c2_c3.repo_paths(dados, name)
        save_releases_to_parquet(units[name]["c2"], owner, repo, paths.releases_c2)
        save_tags_to_parquet(units[name]["c3"], owner, repo, paths.tags)
        backfill_c2_c3.write_meta(
            paths.meta, {**units[name]["meta"], "window": backfill_c2_c3.window_key(*WINDOW)}
        )


def _read_parquet(tmp_path: Path) -> list[dict]:
    return pq.read_table(tmp_path / "dados" / "repositorios.parquet").to_pylist()


def _read_csv(tmp_path: Path) -> list[dict]:
    with open(tmp_path / "dados" / "repositorios.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class _Client:
    token_pool = None

    async def close(self):
        pass


def test_compute_columns_semantics(units):
    full = units["org/full"]

    columns = compute_c2_c3_columns(
        full["c2"], full["c3"], total_prereleases=2, total_tags=9, window_weeks=WEEKS
    )

    assert columns == {
        "prereleases_count_window": 1,
        "total_prereleases": 2,
        "tags_count_window": 2,
        "total_tags": 9,
        "c2_deployment_frequency": 3 / WEEKS,
        "c2_lead_time_b_hours": 36.0,  # median of 24h (rc1) and 48h (v1.1)
        "c3_deployment_frequency": 2 / WEEKS,
        "c3_lead_time_b_hours": 24.0,
    }
    assert list(columns) == [
        c for c in FULL_COLUMNS if c in backfill_c2_c3.C2_C3_COLUMNS
    ]


def test_load_tag_commits_roundtrip(units, tmp_path):
    _persist(units, tmp_path, ["org/full"])

    loaded = backfill_c2_c3.load_tag_commits(tmp_path / "tags" / "org__full.parquet")

    assert [rc.release.tag_name for rc in loaded] == ["t1", "t2"]
    assert [rc.status for rc in loaded] == [ComparisonStatus.FIRST_RELEASE, ComparisonStatus.OK]
    assert loaded[1].commits[0].sha == "c"
    assert loaded[0].commits_or_none is None


def test_columns_from_files_equal_columns_from_memory(units, tmp_path):
    """The persisted files carry everything the columns need (no information loss)."""
    _persist(units, tmp_path, units)

    for name, data in units.items():
        record: dict = {}
        assert backfill_c2_c3.apply_c2_c3(
            record, backfill_c2_c3.repo_paths(tmp_path, name)
            , WEEKS
        ) == (True, True)
        expected = compute_c2_c3_columns(
            data["c2"],
            data["c3"],
            total_prereleases=data["meta"]["total_prereleases"],
            total_tags=data["meta"]["total_tags"],
            window_weeks=WEEKS,
        )
        assert record == expected, name


async def test_backfill_offline_fills_columns_and_keeps_everything_else(
    config, units, dataset, tmp_path
):
    _persist(units, tmp_path / "dados", units)

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True)

    assert report.ok and report.total == 3 and report.filled == 3
    assert report.count_mismatch == []
    assert report.with_prereleases == 1
    assert report.without_tags == 1
    assert report.without_c2_lead_time == 2
    assert report.without_c3_lead_time == 2

    rows = _read_parquet(tmp_path)
    assert [r["full_name"] for r in rows] == ["org/full", "org/nolt", "org/empty"]
    full, nolt, empty = rows
    assert full["prereleases_count_window"] == 1 and full["total_prereleases"] == 2
    assert full["tags_count_window"] == 2 and full["total_tags"] == 9
    assert full["c2_lead_time_b_hours"] == 36.0 and full["c3_lead_time_b_hours"] == 24.0
    assert nolt["c2_deployment_frequency"] == 1 / WEEKS
    assert nolt["c2_lead_time_b_hours"] is None and nolt["c3_lead_time_b_hours"] is None
    # no units: counts and frequencies are zero, only the lead time is null
    assert empty["c2_deployment_frequency"] == 0.0 and empty["c3_deployment_frequency"] == 0.0
    assert empty["total_tags"] == 3 and empty["tags_count_window"] == 0

    # Pre-existing columns are untouched (including the CFR (b) ones)
    for original, new in zip(dataset, rows):
        for key, value in original.items():
            assert new[key] == value, key


async def test_backfill_writes_full_schema_in_csv_and_parquet(config, units, dataset, tmp_path):
    _persist(units, tmp_path / "dados", units)

    await backfill_c2_c3.backfill_c2_c3(config, offline=True)

    parquet = pq.read_table(tmp_path / "dados" / "repositorios.parquet")
    assert parquet.column_names == FULL_COLUMNS
    csv_rows = _read_csv(tmp_path)
    assert list(csv_rows[0].keys()) == FULL_COLUMNS
    assert csv_rows[0]["total_tags"] == "9"
    assert csv_rows[1]["c2_lead_time_b_hours"] == ""
    assert csv_rows[0]["cfr_b"] == "0.25"


async def test_backfill_is_idempotent(config, units, dataset, tmp_path):
    _persist(units, tmp_path / "dados", units)

    await backfill_c2_c3.backfill_c2_c3(config, offline=True)
    first = ((tmp_path / "dados" / "repositorios.csv").read_bytes(), _read_parquet(tmp_path))
    await backfill_c2_c3.backfill_c2_c3(config, offline=True)
    second = ((tmp_path / "dados" / "repositorios.csv").read_bytes(), _read_parquet(tmp_path))

    assert first == second


async def test_backfill_offline_reports_missing_files(config, units, dataset, tmp_path):
    _persist(units, tmp_path / "dados", ["org/full", "org/empty"])

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True)

    assert not report.ok
    assert list(report.failed) == ["org/nolt"]
    rows = _read_parquet(tmp_path)
    assert [r["full_name"] for r in rows] == ["org/full", "org/nolt", "org/empty"]
    assert rows[0]["total_tags"] == 9
    assert rows[1]["total_tags"] is None and rows[1]["c2_deployment_frequency"] is None


async def test_incomplete_collection_is_not_reused(config, units, dataset, tmp_path):
    """The meta file is written last: without it the repository is collected again."""
    _persist(units, tmp_path / "dados", ["org/full"])
    backfill_c2_c3.repo_paths(tmp_path / "dados", "org/full").meta.unlink()

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True, limit=1)

    assert list(report.failed) == ["org/full"]


async def test_collection_for_another_window_is_stale_and_collected_again(
    config, units, dataset, tmp_path, monkeypatch
):
    dados = tmp_path / "dados"
    _persist(units, dados, units)
    # org/nolt was collected with the previous window convention (`fim` at 00:00Z)
    paths = backfill_c2_c3.repo_paths(dados, "org/nolt")
    meta = backfill_c2_c3.read_meta(paths.meta)
    meta["window"] = ["2024-01-01T00:00:00+00:00", "2024-12-31T00:00:00+00:00"]
    backfill_c2_c3.write_meta(paths.meta, meta)
    assert paths.complete() and not paths.complete(WINDOW)
    calls: list[str] = []

    async def fake_collect(client, full_name, **kwargs):
        calls.append(full_name)
        assert kwargs["window_end"] == WINDOW[1]
        _persist(units, kwargs["dados_dir"], [full_name])

    monkeypatch.setattr(backfill_c2_c3, "collect_repository_c2_c3", fake_collect)

    report = await backfill_c2_c3.backfill_c2_c3(config, client=_Client())

    assert calls == ["org/nolt"] and report.ok


async def test_backfill_collects_only_missing_and_resumes(
    config, units, dataset, tmp_path, monkeypatch
):
    dados = tmp_path / "dados"
    _persist(units, dados, ["org/full"])
    calls: list[str] = []

    async def fake_collect(client, full_name, **kwargs):
        calls.append(full_name)
        if full_name == "org/nolt":
            raise RuntimeError("boom")
        _persist(units, kwargs["dados_dir"], [full_name])

    monkeypatch.setattr(backfill_c2_c3, "collect_repository_c2_c3", fake_collect)

    report = await backfill_c2_c3.backfill_c2_c3(config, client=_Client(), num_workers=2)

    assert sorted(calls) == ["org/empty", "org/nolt"]
    assert report.collected == ["org/empty"]
    assert list(report.failed) == ["org/nolt"]
    assert "boom" in report.failed["org/nolt"]
    rows = _read_parquet(tmp_path)
    assert rows[0]["total_tags"] == 9 and rows[2]["total_tags"] == 3
    assert rows[1]["total_tags"] is None  # failed repository keeps null values

    calls.clear()

    async def fake_collect_ok(client, full_name, **kwargs):
        calls.append(full_name)
        _persist(units, kwargs["dados_dir"], [full_name])

    monkeypatch.setattr(backfill_c2_c3, "collect_repository_c2_c3", fake_collect_ok)
    report = await backfill_c2_c3.backfill_c2_c3(config, client=_Client())
    assert calls == ["org/nolt"]
    assert report.ok
    assert _read_parquet(tmp_path)[1]["c2_deployment_frequency"] == 1 / WEEKS


async def test_backfill_flags_count_mismatch_with_dataset(config, units, tmp_path):
    dados = tmp_path / "dados"
    save_repositories_dataset(
        [_legacy_record("org/full", 7, 5)],
        dados / "repositorios.parquet",
        dados / "repositorios.csv",
    )
    _persist(units, dados, ["org/full"])

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True)

    assert report.count_mismatch == ["org/full"]
    assert report.total_drift == []
    assert "divergente: org/full" in backfill_c2_c3.format_report(report)


async def test_backfill_flags_total_releases_drift_and_keeps_dataset_value(
    config, units, tmp_path
):
    dados = tmp_path / "dados"
    # the dataset was collected before 3 new releases were published
    save_repositories_dataset(
        [_legacy_record("org/full", 2, 2)],
        dados / "repositorios.parquet",
        dados / "repositorios.csv",
    )
    _persist(units, dados, ["org/full"])

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True)

    assert report.count_mismatch == [] and report.total_drift == ["org/full"]
    (row,) = _read_parquet(tmp_path)
    assert row["total_releases"] == 2  # never rewritten
    assert row["total_prereleases"] == 2


async def test_backfill_limit_keeps_all_rows(config, units, dataset, tmp_path):
    _persist(units, tmp_path / "dados", ["org/full"])

    report = await backfill_c2_c3.backfill_c2_c3(config, offline=True, limit=1)

    assert report.ok and report.total == 1
    rows = _read_parquet(tmp_path)
    assert len(rows) == 3
    assert rows[0]["total_tags"] == 9
    assert rows[1]["total_tags"] is None


async def test_backfill_requires_dataset(config):
    with pytest.raises(FileNotFoundError):
        await backfill_c2_c3.backfill_c2_c3(config, offline=True)


def _git(repo: Path, *args: str, date: str | None = None) -> None:
    env = {**os.environ}
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Repo with an anchor tag before the window, a pre-release tag and a release tag."""
    repo = tmp_path / "clone"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name, date, tag in [
        ("anchor", "2023-12-01T00:00:00Z", "v0.9"),
        ("rc", "2024-03-01T00:00:00Z", "v1.0-rc1"),
        ("final", "2024-06-01T00:00:00Z", "v1.0"),
        ("last-day", "2024-12-31T12:00:00Z", "v1.1"),
    ]:
        (repo / f"{name}.txt").write_text(name)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", f"fix: {name}", date=date)
        _git(repo, "tag", tag)
    return repo / ".git"


async def test_collect_repository_persists_c2_c3_and_columns_match(
    config, dataset, tmp_path, git_repo, monkeypatch
):
    """End to end with a real local Git repo: collection -> files -> columns."""
    releases = [
        Release(tag_name="v0.9", published_at="2023-12-02T00:00:00Z"),
        Release(tag_name="v1.0-rc1", published_at="2024-03-02T00:00:00Z", prerelease=True),
        Release(tag_name="v1.0", published_at="2024-06-02T00:00:00Z"),
        # last day of the window: only inside because `fim` date-only means end of day
        Release(tag_name="v1.1", published_at="2024-12-31T12:00:00Z"),
        Release(tag_name="v0.8", published_at="2023-11-01T00:00:00Z", prerelease=True),
    ]

    async def fake_fetch(client, owner, repo, window_start=None, use_graphql=False):
        return releases

    @asynccontextmanager
    async def fake_clone(owner, repo, cache_dir, auto_cleanup, token_pool=None):
        yield git_repo

    monkeypatch.setattr(backfill_c2_c3, "fetch_releases", fake_fetch)
    monkeypatch.setattr(backfill_c2_c3, "temporary_git_clone", fake_clone)
    dados = tmp_path / "dados"
    # only org/full is under test; the other repos are not in the persisted set
    save_repositories_dataset(
        [_legacy_record("org/full", 2, 5)],
        dados / "repositorios.parquet",
        dados / "repositorios.csv",
    )

    report = await backfill_c2_c3.backfill_c2_c3(config, client=_Client())

    assert report.ok and report.collected == ["org/full"] and report.count_mismatch == []
    (row,) = _read_parquet(tmp_path)
    assert row["prereleases_count_window"] == 1  # v1.0-rc1 (v0.8 is outside the window)
    assert row["total_prereleases"] == 2
    assert row["tags_count_window"] == 3  # includes v1.1 of the last day
    assert row["total_tags"] == 4
    assert row["c2_deployment_frequency"] == 3 / WEEKS
    assert row["c3_deployment_frequency"] == 3 / WEEKS
    # rc1 and v1.0 ship 1 commit published a day later (24h); v1.1 is published at its commit (0h)
    assert row["c2_lead_time_b_hours"] == 24.0
    # the tags are dated by their commit, which is also the commit date -> 0h
    assert row["c3_lead_time_b_hours"] == 0.0
    paths = backfill_c2_c3.repo_paths(dados, "org/full")
    assert paths.complete()
    assert [r["tag_name"] for r in pq.read_table(paths.releases_c2).to_pylist()] == [
        "v1.0-rc1",
        "v1.0",
        "v1.1",
    ]
    assert [r["tag_name"] for r in pq.read_table(paths.tags).to_pylist()] == [
        "v1.0-rc1",
        "v1.0",
        "v1.1",
    ]
    assert backfill_c2_c3.read_meta(paths.meta) == {
        "releases_count_window": 2,
        "total_releases": 5,
        "total_prereleases": 2,
        "total_tags": 4,
        "window": backfill_c2_c3.window_key(*WINDOW),
    }


def test_format_report_never_mentions_credentials():
    report = backfill_c2_c3.BackfillC2C3Report(total=2, filled=1)
    report.failed["org/x"] = "RuntimeError: boom"

    text = backfill_c2_c3.format_report(report)

    assert "Repositórios: 2" in text
    assert "falha: org/x: RuntimeError: boom" in text


def test_main_offline_returns_exit_code(config, units, dataset, tmp_path, monkeypatch, capsys):
    _persist(units, tmp_path / "dados", units)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["backfill_c2_c3", "--config", str(config_path), "--offline"])

    assert backfill_c2_c3.main() == 0
    assert "Colunas C2/C3 preenchidas: 3" in capsys.readouterr().out


async def test_files_removed_during_run_are_reported_not_fatal(
    config, units, dataset, tmp_path, monkeypatch
):
    dados = tmp_path / "dados"
    _persist(units, dados, units)

    async def fake_collect(client, full_name, **kwargs):  # pragma: no cover - not reached
        raise AssertionError

    monkeypatch.setattr(backfill_c2_c3, "collect_repository_c2_c3", fake_collect)
    original = backfill_c2_c3.repo_paths
    calls = {"n": 0}

    def flaky_repo_paths(dados_dir, full_name):
        paths = original(dados_dir, full_name)
        calls["n"] += 1
        # complete at the pending check (first 3 calls), gone when applying
        if calls["n"] > 3 and full_name == "org/nolt":
            paths.meta.unlink(missing_ok=True)
        return paths

    monkeypatch.setattr(backfill_c2_c3, "repo_paths", flaky_repo_paths)

    report = await backfill_c2_c3.backfill_c2_c3(config, client=_Client())

    assert list(report.failed) == ["org/nolt"]
    assert report.filled == 2

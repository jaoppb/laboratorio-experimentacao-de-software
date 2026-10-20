"""Tests for the CFR (b) backfill command (pipeline.backfill_cfr_b)."""

from __future__ import annotations

import csv
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from metricas.schemas import Commit, Release
from pipeline import backfill_cfr_b
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.orchestrator import SCHEMA_REPOSITORIOS, save_repositories_dataset
from pipeline.releases import save_releases_to_parquet

FULL_COLUMNS = [f.name for f in SCHEMA_REPOSITORIOS]


def _commit(message: str) -> Commit:
    return Commit(sha="s", committed_at="2024-02-01T00:00:00Z", message=message)


def _rc(tag, published, status, commits=(), previous=None):
    return ReleaseCommits(
        Release(tag_name=tag, published_at=published),
        previous,
        status,
        list(commits),
    )


def _build_histories() -> dict[str, list[ReleaseCommits]]:
    return {
        # v1.0.0 fails (v1.0.1 is a patch bump with a fix); v1.0.1 is ok -> 1/2
        "org/failing": [
            _rc("v1.0.0", "2024-03-01T00:00:00Z", ComparisonStatus.FIRST_RELEASE),
            _rc("v1.0.1", "2024-03-03T00:00:00Z", ComparisonStatus.OK, [_commit("fix: x")]),
        ],
        # only release published in the last 7 days of the window -> censored
        "org/censored": [
            _rc("v2.0.0", "2024-12-30T00:00:00Z", ComparisonStatus.FIRST_RELEASE),
        ],
        # next release has unknown commits -> v1.0.0 skipped; v1.0.1 ok -> 0/1
        "org/skipped": [
            _rc("v1.0.0", "2024-03-01T00:00:00Z", ComparisonStatus.OK, [_commit("feat")]),
            _rc("v1.0.1", "2024-03-03T00:00:00Z", ComparisonStatus.NOT_FOUND),
        ],
    }


def _legacy_record(full_name: str, releases_count_window: int) -> dict:
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
        "total_releases": releases_count_window,
        "deployment_frequency": 0.123456789,
        "deployment_tier": "Low",
        "lead_time_a_hours": 1.5,
        "overall_dora_score": 2,
        "overall_dora_tier": "Medium",
    }


@pytest.fixture
def config(tmp_path: Path) -> dict:
    return {
        "janela": {"inicio": "2024-01-01", "fim": "2024-12-31"},
        "cfr_b": {"heuristica": "v1"},
        "diretorios": {
            "dados": str(tmp_path / "dados"),
            "cache": str(tmp_path / "cache"),
            "git_cache": str(tmp_path / "git"),
        },
    }


@pytest.fixture
def histories() -> dict[str, list[ReleaseCommits]]:
    return _build_histories()


@pytest.fixture
def dataset(tmp_path: Path) -> list[dict]:
    """Legacy-like dataset: CFR (b) columns absent (null), order failing/censored/skipped."""
    dados = tmp_path / "dados"
    records = [
        _legacy_record("org/failing", 2),
        _legacy_record("org/censored", 1),
        _legacy_record("org/skipped", 2),
    ]
    save_repositories_dataset(records, dados / "repositorios.parquet", dados / "repositorios.csv")
    return records


def _persist(histories, releases_dir: Path, names) -> None:
    for name in names:
        owner, repo = name.split("/")
        save_releases_to_parquet(
            histories[name], owner, repo, releases_dir / f"{owner}__{repo}.parquet"
        )


def _read_parquet(tmp_path: Path) -> list[dict]:
    return pq.read_table(tmp_path / "dados" / "repositorios.parquet").to_pylist()


def _read_csv(tmp_path: Path) -> list[dict]:
    with open(tmp_path / "dados" / "repositorios.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_load_release_commits_roundtrip(histories, tmp_path):
    _persist(histories, tmp_path, ["org/skipped"])

    loaded = backfill_cfr_b.load_release_commits(tmp_path / "org__skipped.parquet")

    assert [rc.release.tag_name for rc in loaded] == ["v1.0.0", "v1.0.1"]
    assert [rc.status for rc in loaded] == [ComparisonStatus.OK, ComparisonStatus.NOT_FOUND]
    assert loaded[0].commits[0].message == "feat"
    assert loaded[1].commits_or_none is None
    assert loaded[0].release.published_at.isoformat().startswith("2024-03-01T00:00:00")


async def test_backfill_offline_fills_cfr_b_and_keeps_everything_else(
    config, histories, dataset, tmp_path
):
    _persist(histories, tmp_path / "dados" / "releases", histories)

    report = await backfill_cfr_b.backfill_cfr_b(config, offline=True)

    assert report.ok
    assert report.total == 3
    assert report.with_cfr_b == 2
    assert report.without_cfr_b == 1
    assert report.censored_repos == 1
    assert report.skipped_repos == 1
    assert report.count_mismatch == []
    assert dict(report.tiers) == {"Low": 1, "Elite": 1}

    rows = _read_parquet(tmp_path)
    assert [r["full_name"] for r in rows] == ["org/failing", "org/censored", "org/skipped"]
    failing, censored, skipped = rows
    assert (failing["cfr_b"], failing["cfr_b_tier"]) == (0.5, "Low")
    assert failing["cfr_b_failed_releases"] == 1
    assert failing["cfr_b_evaluated_releases"] == 2
    assert censored["cfr_b"] is None and censored["cfr_b_tier"] is None
    assert censored["cfr_b_censored_releases"] == 1
    assert censored["cfr_b_evaluated_releases"] == 0
    assert (skipped["cfr_b"], skipped["cfr_b_tier"]) == (0.0, "Elite")
    assert skipped["cfr_b_skipped_releases"] == 1
    assert skipped["cfr_b_evaluated_releases"] == 1

    # Pre-existing columns are untouched
    for original, new in zip(dataset, rows):
        for key, value in original.items():
            assert new[key] == value, key


async def test_backfill_writes_full_schema_in_csv_and_parquet(
    config, histories, dataset, tmp_path
):
    _persist(histories, tmp_path / "dados" / "releases", histories)

    await backfill_cfr_b.backfill_cfr_b(config, offline=True)

    parquet = pq.read_table(tmp_path / "dados" / "repositorios.parquet")
    assert parquet.column_names == FULL_COLUMNS
    csv_rows = _read_csv(tmp_path)
    assert list(csv_rows[0].keys()) == FULL_COLUMNS
    assert [r["full_name"] for r in csv_rows] == [r["full_name"] for r in parquet.to_pylist()]
    assert csv_rows[0]["cfr_b"] == "0.5"
    assert csv_rows[1]["cfr_b"] == "" and csv_rows[1]["cfr_b_tier"] == ""


async def test_backfill_is_idempotent(config, histories, dataset, tmp_path):
    _persist(histories, tmp_path / "dados" / "releases", histories)

    await backfill_cfr_b.backfill_cfr_b(config, offline=True)
    first = (
        (tmp_path / "dados" / "repositorios.csv").read_bytes(),
        _read_parquet(tmp_path),
    )
    await backfill_cfr_b.backfill_cfr_b(config, offline=True)
    second = (
        (tmp_path / "dados" / "repositorios.csv").read_bytes(),
        _read_parquet(tmp_path),
    )

    assert first == second


async def test_backfill_offline_reports_missing_files(config, histories, dataset, tmp_path):
    _persist(histories, tmp_path / "dados" / "releases", ["org/failing", "org/skipped"])

    report = await backfill_cfr_b.backfill_cfr_b(config, offline=True)

    assert not report.ok
    assert list(report.failed) == ["org/censored"]
    rows = _read_parquet(tmp_path)
    assert [r["full_name"] for r in rows] == ["org/failing", "org/censored", "org/skipped"]
    assert rows[0]["cfr_b"] == 0.5
    assert rows[1]["cfr_b"] is None and rows[1]["cfr_b_evaluated_releases"] is None


async def test_backfill_collects_only_missing_releases(
    config, histories, dataset, tmp_path, monkeypatch
):
    releases_dir = tmp_path / "dados" / "releases"
    _persist(histories, releases_dir, ["org/failing"])
    calls: list[str] = []

    async def fake_persist(client, full_name, **kwargs):
        calls.append(full_name)
        if full_name == "org/skipped":
            raise RuntimeError("boom")
        _persist(histories, kwargs["releases_dir"], [full_name])

    class _Client:
        token_pool = None

        async def close(self):
            pass

    monkeypatch.setattr(backfill_cfr_b, "persist_repository_releases", fake_persist)

    report = await backfill_cfr_b.backfill_cfr_b(config, client=_Client(), num_workers=2)

    assert sorted(calls) == ["org/censored", "org/skipped"]
    assert report.collected == ["org/censored"]
    assert list(report.failed) == ["org/skipped"]
    assert "boom" in report.failed["org/skipped"]
    rows = _read_parquet(tmp_path)
    assert rows[0]["cfr_b"] == 0.5
    assert rows[1]["cfr_b_censored_releases"] == 1
    assert rows[2]["cfr_b"] is None  # failed repository keeps null values

    # Resumable: a rerun only retries the failed repository
    calls.clear()

    async def fake_persist_ok(client, full_name, **kwargs):
        calls.append(full_name)
        _persist(histories, kwargs["releases_dir"], [full_name])

    monkeypatch.setattr(backfill_cfr_b, "persist_repository_releases", fake_persist_ok)
    report = await backfill_cfr_b.backfill_cfr_b(config, client=_Client())
    assert calls == ["org/skipped"]
    assert report.ok
    assert _read_parquet(tmp_path)[2]["cfr_b"] == 0.0


async def test_backfill_flags_count_mismatch_with_dataset(config, histories, tmp_path):
    dados = tmp_path / "dados"
    save_repositories_dataset(
        [_legacy_record("org/failing", 5)], dados / "repositorios.parquet", dados / "repositorios.csv"
    )
    _persist(histories, dados / "releases", ["org/failing"])

    report = await backfill_cfr_b.backfill_cfr_b(config, offline=True)

    assert report.count_mismatch == ["org/failing"]
    assert "divergente: org/failing" in backfill_cfr_b.format_report(report)


async def test_backfill_limit_keeps_all_rows(config, histories, dataset, tmp_path):
    _persist(histories, tmp_path / "dados" / "releases", ["org/failing"])

    report = await backfill_cfr_b.backfill_cfr_b(config, offline=True, limit=1)

    assert report.ok and report.total == 1
    rows = _read_parquet(tmp_path)
    assert len(rows) == 3
    assert rows[0]["cfr_b"] == 0.5
    assert rows[1]["cfr_b"] is None


async def test_backfill_rejects_unknown_heuristic(config, dataset):
    config["cfr_b"]["heuristica"] = "v99"

    with pytest.raises(ValueError, match="v99"):
        await backfill_cfr_b.backfill_cfr_b(config, offline=True)


async def test_backfill_requires_dataset(config):
    with pytest.raises(FileNotFoundError):
        await backfill_cfr_b.backfill_cfr_b(config, offline=True)


def test_format_report_never_mentions_credentials():
    report = backfill_cfr_b.BackfillReport(total=2, with_cfr_b=1, without_cfr_b=1)
    report.tiers["Elite"] += 1
    report.failed["org/x"] = "RuntimeError: boom"

    text = backfill_cfr_b.format_report(report)

    assert "Repositórios: 2" in text
    assert "Elite=1" in text
    assert "falha: org/x: RuntimeError: boom" in text


def test_main_offline_returns_exit_code(config, histories, dataset, tmp_path, monkeypatch, capsys):
    import yaml

    _persist(histories, tmp_path / "dados" / "releases", histories)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv", ["backfill_cfr_b", "--config", str(config_path), "--offline"]
    )

    assert backfill_cfr_b.main() == 0
    assert "Com CFR (b) calculado: 2" in capsys.readouterr().out

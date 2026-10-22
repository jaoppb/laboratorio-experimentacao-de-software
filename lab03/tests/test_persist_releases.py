"""Tests for the releases backfill command (pipeline.persist_releases)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from metricas.schemas import Commit, Release
from pipeline import persist_releases
from pipeline.commit_store import load_commit_store, load_release_commits, save_commits_to_parquet
from pipeline.commits import ComparisonStatus, ReleaseCommits


def _write_dataset(dados: Path, names: list[str]) -> None:
    dados.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"full_name": pa.array(names, type=pa.string())}),
        dados / "repositorios.parquet",
    )


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
def fake_collection(monkeypatch: pytest.MonkeyPatch):
    """Replace network and git with an in-memory history of three releases."""
    calls: list[str] = []
    history = [
        Release(tag_name="v0.9.0", published_at="2023-12-01T00:00:00Z"),
        Release(tag_name="v1.0.0", published_at="2024-03-01T00:00:00Z"),
        Release(tag_name="v1.0.1", published_at="2024-03-03T00:00:00Z"),
    ]

    async def fake_fetch_releases(client, owner, repo, window_start=None, use_graphql=False):
        calls.append(f"{owner}/{repo}")
        if repo == "broken":
            raise RuntimeError("boom")
        return history

    @asynccontextmanager
    async def fake_clone(owner, repo, cache_dir, auto_cleanup, token_pool):
        yield Path("unused")

    async def fake_collect(client, owner, repo, window, git_dir, commit_cache=None):
        ordered = window.with_anchor()
        return [
            ReleaseCommits(
                ordered[i],
                ordered[i - 1],
                ComparisonStatus.OK,
                [Commit(sha=f"s{i}", committed_at="2024-02-01T00:00:00Z", message="fix: x")],
            )
            for i in range(1, len(ordered))
        ]

    monkeypatch.setattr(persist_releases, "fetch_releases", fake_fetch_releases)
    monkeypatch.setattr(persist_releases, "temporary_git_clone", fake_clone)
    monkeypatch.setattr(persist_releases, "collect_release_commits", fake_collect)
    return calls


class _Client:
    token_pool = None


def test_accepted_repositories_missing_file(tmp_path: Path):
    assert persist_releases.accepted_repositories(tmp_path / "nope.parquet") == []


async def test_persist_all_saves_window_releases(config, fake_collection, tmp_path):
    _write_dataset(tmp_path / "dados", ["org/a", "org/b"])

    result = await persist_releases.persist_all(config, client=_Client(), num_workers=2)

    assert sorted(result["done"]) == ["org/a", "org/b"]
    table = pq.read_table(tmp_path / "dados" / "releases" / "org__a.parquet").to_pydict()
    assert table["tag_name"] == ["v1.0.0", "v1.0.1"]
    assert table["previous_release"] == ["v0.9.0", "v1.0.0"]
    assert table["status"] == ["ok", "ok"]
    assert table["commit_shas"] == [["s1"], ["s2"]]
    # the commits are in the repository's commit store, next to releases/
    units = load_release_commits(
        tmp_path / "dados" / "releases" / "org__a.parquet",
        tmp_path / "dados" / "commits" / "org__a.parquet",
    )
    assert units[1].commits[0].message == "fix: x"
    assert units[1].previous_name == "v1.0.0"


async def test_persist_extends_an_existing_commit_store(config, fake_collection, tmp_path):
    """The store is shared with C2/C3: persisting C1 keeps the commits already there."""
    _write_dataset(tmp_path / "dados", ["org/a"])
    store = tmp_path / "dados" / "commits" / "org__a.parquet"
    keep = Commit(sha="from-c3", committed_at="2024-02-02T00:00:00Z", message="chore: y")
    save_commits_to_parquet([keep], store)

    await persist_releases.persist_all(config, client=_Client())

    assert set(load_commit_store(store)) == {"from-c3", "s1", "s2"}


async def test_persist_all_skips_existing_and_reports_failures(
    config, fake_collection, tmp_path
):
    _write_dataset(tmp_path / "dados", ["org/a", "org/broken", "org/c"])
    releases_dir = tmp_path / "dados" / "releases"
    releases_dir.mkdir(parents=True)
    (releases_dir / "org__a.parquet").write_bytes(b"already there")
    (tmp_path / "dados" / "commits").mkdir()
    (tmp_path / "dados" / "commits" / "org__a.parquet").write_bytes(b"already there")

    result = await persist_releases.persist_all(config, client=_Client(), limit=2)

    assert fake_collection == ["org/broken"]
    assert result == {"done": [], "failed": ["org/broken"]}

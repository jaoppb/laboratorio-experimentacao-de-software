"""Integration tests for the complete Lab03 data mining pipeline and resumption (Issue #39)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from pipeline.http_client import GitHubClient
from pipeline.orchestrator import (
    PipelineOrchestrator,
    load_repositories_dataset,
    run_pipeline,
    save_repositories_dataset,
)


def _build_mock_http_handler():
    """Create a mock HTTP transport answering GitHub API endpoints."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)

        # 0. GraphQL API
        if "/graphql" in url_str:
            import json as _json
            body = _json.loads(request.content.decode("utf-8"))
            vars_dict = body.get("variables", {})
            name = vars_dict.get("name", "repo-valid-1")
            releases_count = 2 if "few-releases" in name else 6
            releases = [
                {
                    "tagName": f"v1.{i}",
                    "publishedAt": f"2026-0{i+1}-15T12:00:00Z",
                    "isDraft": False,
                    "isPrerelease": False,
                }
                for i in range(releases_count)
            ]
            return httpx.Response(
                200,
                json={
                    "data": {
                        "repository": {
                            "name": name,
                            "stargazerCount": 20000,
                            "createdAt": "2020-01-01T00:00:00Z",
                            "primaryLanguage": {"name": "Python"},
                            "defaultBranchRef": {"name": "main"},
                            "releases": {
                                "totalCount": len(releases),
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": releases,
                            },
                        }
                    }
                },
                request=request,
            )

        # 1. Search API
        if "/search/repositories" in url_str:
            return httpx.Response(
                200,
                json={
                    "total_count": 4,
                    "items": [
                        {
                            "full_name": "org/repo-valid-1",
                            "stargazers_count": 25000,
                            "language": "Python",
                            "created_at": "2020-01-01T00:00:00Z",
                            "default_branch": "main",
                        },
                        {
                            "full_name": "org/repo-no-actions",
                            "stargazers_count": 20000,
                            "language": "Go",
                            "created_at": "2021-01-01T00:00:00Z",
                            "default_branch": "main",
                        },
                        {
                            "full_name": "org/repo-few-releases",
                            "stargazers_count": 18000,
                            "language": "TypeScript",
                            "created_at": "2021-05-01T00:00:00Z",
                            "default_branch": "main",
                        },
                        {
                            "full_name": "org/repo-valid-2",
                            "stargazers_count": 15000,
                            "language": "Rust",
                            "created_at": "2022-01-01T00:00:00Z",
                            "default_branch": "main",
                        },
                    ],
                },
                request=request,
            )

        # 2. Actions workflows check
        if "/actions/workflows" in url_str:
            if "repo-no-actions" in url_str:
                return httpx.Response(200, json={"total_count": 0}, request=request)
            return httpx.Response(200, json={"total_count": 3}, request=request)

        # 3. Releases endpoint
        if "/releases" in url_str:
            if "repo-few-releases" in url_str:
                # Only 2 releases (less than 5 required)
                return httpx.Response(
                    200,
                    json=[
                        {
                            "tag_name": "v1.1",
                            "published_at": "2026-03-01T12:00:00Z",
                            "draft": False,
                            "prerelease": False,
                        },
                        {
                            "tag_name": "v1.0",
                            "published_at": "2026-01-01T12:00:00Z",
                            "draft": False,
                            "prerelease": False,
                        },
                    ],
                    request=request,
                )
            # Valid repos have 6 releases
            releases = [
                {
                    "tag_name": f"v1.{i}",
                    "published_at": f"2026-0{i+1}-15T12:00:00Z",
                    "draft": False,
                    "prerelease": False,
                }
                for i in range(6)
            ]
            return httpx.Response(200, json=releases, request=request)

        # 4. Repo metadata & contributors
        if "/contributors" in url_str:
            headers = {
                "Link": '<https://api.github.com/contributors?per_page=1&anon=true&page=42>; rel="last"'
            }
            return httpx.Response(200, headers=headers, json=[{"id": 1}], request=request)

        if "/repos/org/repo-" in url_str and "/actions" not in url_str and "/compare" not in url_str:
            name = url_str.split("/repos/org/")[-1].split("?")[0]
            return httpx.Response(
                200,
                json={
                    "stargazers_count": 20000,
                    "language": "Python",
                    "default_branch": "main",
                    "created_at": "2020-01-01T00:00:00Z",
                },
                request=request,
            )

        # 5. Workflow runs
        if "/actions/runs" in url_str:
            # 60 valid runs: 49 successes, 10 failures, 1 success at the end to resolve
            runs = []
            for i in range(49):
                runs.append(
                    {
                        "id": 1000 + i,
                        "workflow_id": 99,
                        "name": "CI",
                        "event": "push",
                        "head_branch": "main",
                        "conclusion": "success",
                        "run_started_at": f"2026-01-10T10:{i:02d}:00Z",
                        "updated_at": f"2026-01-10T10:{i:02d}:30Z",
                    }
                )
            for i in range(10):
                runs.append(
                    {
                        "id": 2000 + i,
                        "workflow_id": 99,
                        "name": "CI",
                        "event": "push",
                        "head_branch": "main",
                        "conclusion": "failure",
                        "run_started_at": f"2026-02-10T10:{i:02d}:00Z",
                        "updated_at": f"2026-02-10T10:{i:02d}:30Z",
                    }
                )
            # Resolving success
            runs.append(
                {
                    "id": 3000,
                    "workflow_id": 99,
                    "name": "CI",
                    "event": "push",
                    "head_branch": "main",
                    "conclusion": "success",
                    "run_started_at": "2026-02-10T11:00:00Z",
                    "updated_at": "2026-02-10T11:05:00Z",
                }
            )
            return httpx.Response(
                200,
                json={"total_count": len(runs), "workflow_runs": runs},
                request=request,
            )

        # 6. Compare commits
        if "/compare/" in url_str:
            commits = [
                {
                    "sha": f"abc{i}",
                    "commit": {
                        "author": {"date": f"2026-01-0{i+1}T10:00:00Z"},
                        "message": f"commit {i}",
                    },
                }
                for i in range(3)
            ]
            return httpx.Response(
                200,
                json={"total_commits": 3, "commits": commits},
                request=request,
            )

        return httpx.Response(200, json={}, request=request)

    return handler


@pytest.fixture(autouse=True)
def mock_git_clone_for_integration(monkeypatch):
    from contextlib import asynccontextmanager
    from metricas.schemas import Commit, Release
    from pipeline.commits import ComparisonStatus, ReleaseCommits

    @asynccontextmanager
    async def fake_temporary_clone(owner, repo, cache_dir, auto_cleanup, token_pool=None):
        yield Path(cache_dir) / f"{owner}__{repo}.git"

    async def fake_extract_tags(git_dir):
        return [
            Release(tag_name="v1.0", published_at="2026-01-15T12:00:00Z", commit_sha="sha-t0"),
            Release(tag_name="v1.1", published_at="2026-02-15T12:00:00Z", commit_sha="sha-t1"),
        ]

    async def fake_collect_from_git(git_dir, window):
        ordered = window.with_anchor()
        offset = 1 if window.anchor is not None else 0
        res = []
        for i in range(offset, len(ordered)):
            prev = ordered[i - 1] if i > 0 else None
            rel = ordered[i]
            if prev is None:
                res.append(ReleaseCommits(rel, None, ComparisonStatus.FIRST_RELEASE))
            else:
                commits = [
                    Commit(sha=f"sha-{j}", committed_at="2026-01-10T10:00:00Z", message=f"commit {j}")
                    for j in range(2)
                ]
                res.append(ReleaseCommits(rel, prev, ComparisonStatus.OK, commits))
        return res

    async def fake_collect_commits(client, owner, repo, window, git_dir=None):
        return await fake_collect_from_git(git_dir, window)

    monkeypatch.setattr("pipeline.orchestrator.temporary_git_clone", fake_temporary_clone)
    monkeypatch.setattr("pipeline.orchestrator.collect_release_commits", fake_collect_commits)
    monkeypatch.setattr("pipeline.orchestrator.collect_release_commits_from_git", fake_collect_from_git)
    monkeypatch.setattr("pipeline.orchestrator.extract_tags_from_git", fake_extract_tags)


@pytest.fixture
def test_config(tmp_path: Path) -> dict[str, Any]:
    dados_dir = tmp_path / "dados"
    cache_dir = tmp_path / "cache"
    return {
        "janela": {
            "inicio": "2025-10-01",
            "fim": "2026-09-30",
        },
        "amostra": {
            "tamanho_final": 2,
            "min_releases": 5,
            "min_workflow_runs": 50,
        },
        "busca": {
            "star_ranges": [">10000"],
        },
        "diretorios": {
            "dados": str(dados_dir),
            "cache": str(cache_dir),
        },
    }


async def test_pipeline_e2e_mock_success(test_config: dict[str, Any], tmp_path: Path):
    """Test full pipeline end-to-end execution, filtering, Parquet, and CSV generation."""
    transport = httpx.MockTransport(_build_mock_http_handler())
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        async with GitHubClient(
            client=mock_httpx,
            cache_path=tmp_path / "cache" / "http_cache.sqlite",
        ) as client:
            orchestrator = PipelineOrchestrator(
                config=test_config,
                client=client,
                limit=2,
            )
            result = await orchestrator.run_async()

    assert result["accepted_count"] == 2
    assert result["total_evaluated"] >= 4

    # Verify Parquet dataset
    parquet_path = Path(result["parquet_path"])
    assert parquet_path.is_file()
    records = load_repositories_dataset(parquet_path)
    assert len(records) == 2
    full_names = {r["full_name"] for r in records}
    assert full_names == {"org/repo-valid-1", "org/repo-valid-2"}

    # Verify columns and DORA metrics
    rec = records[0]
    assert rec["stars"] == 20000 or rec["stars"] == 25000
    assert rec["contributors_count"] == 42
    assert rec["releases_count_window"] == 6
    assert rec["workflow_runs_count_window"] == 60
    assert rec["deployment_frequency"] > 0
    assert rec["cfr_a"] is not None
    assert rec["recovery_hours"] is not None
    assert rec["overall_dora_tier"] in ("Elite", "High", "Medium", "Low")

    # Verify CSV dataset
    csv_path = Path(result["csv_path"])
    assert csv_path.is_file()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["full_name"] in full_names

    # Verify Funnel CSV
    funil_csv = Path(result["funil_csv"])
    assert funil_csv.is_file()
    with open(funil_csv, "r", encoding="utf-8") as f:
        funnel_rows = list(csv.DictReader(f))
        assert len(funnel_rows) == 5
        stages = [row["etapa"] for row in funnel_rows]
        assert "Busca inicial refinada por estrelas (Search API)" in stages[0]
        assert "Filtro de uso de CI/CD (GitHub Actions)" in stages[1]
        assert "Filtro de releases na janela" in stages[2]
        assert "Filtro de workflow runs na janela" in stages[3]
        assert "Amostra final selecionada" in stages[4]

        # Check discards
        assert int(funnel_rows[1]["descartados"]) == 1  # repo-no-actions
        assert int(funnel_rows[2]["descartados"]) == 1  # repo-few-releases
        assert int(funnel_rows[4]["quantidade_restante"]) == 2

    # Verify C2 and C3 columns and metrics
    assert rec["c2_deployment_frequency"] is not None
    assert rec["c2_lead_time_b_hours"] is not None
    assert rec["c3_deployment_frequency"] is not None
    assert rec["c3_lead_time_b_hours"] is not None
    assert rec["tags_count_window"] == 2
    assert rec["total_tags"] == 2

    # Verify workflow runs parquet files
    dados_path = Path(test_config["diretorios"]["dados"])
    runs_dir = dados_path / "runs"
    assert (runs_dir / "org__repo-valid-1.parquet").is_file()
    assert (runs_dir / "org__repo-valid-2.parquet").is_file()
    # Discarded repos must not have runs parquet files
    assert not (runs_dir / "org__repo-no-actions.parquet").exists()
    assert not (runs_dir / "org__repo-few-releases.parquet").exists()

    # Verify releases and tags parquet files
    releases_dir = dados_path / "releases"
    tags_dir = dados_path / "tags"
    assert (releases_dir / "org__repo-valid-1.parquet").is_file()
    assert (releases_dir / "org__repo-valid-2.parquet").is_file()
    assert (dados_path / "releases_c2" / "org__repo-valid-1.parquet").is_file()
    assert (tags_dir / "org__repo-valid-1.parquet").is_file()
    assert (tags_dir / "org__repo-valid-2.parquet").is_file()
    assert not (releases_dir / "org__repo-no-actions.parquet").exists()
    assert not (tags_dir / "org__repo-no-actions.parquet").exists()


async def test_pipeline_resumption_after_interruption(test_config: dict[str, Any], tmp_path: Path):
    """Verify that stopping early and resuming continues from where it left off."""
    transport = httpx.MockTransport(_build_mock_http_handler())
    cache_path = tmp_path / "cache" / "http_cache.sqlite"

    # --- Run 1: Run with limit = 1 (simulating interruption after first accepted repo) ---
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        async with GitHubClient(client=mock_httpx, cache_path=cache_path) as client1:
            orchestrator1 = PipelineOrchestrator(
                config=test_config,
                client=client1,
                limit=1,
            )
            result1 = await orchestrator1.run_async()

    assert result1["accepted_count"] == 1
    dataset1 = load_repositories_dataset(result1["parquet_path"])
    assert len(dataset1) == 1
    assert dataset1[0]["full_name"] == "org/repo-valid-1"

    # --- Run 2: Resume with target size limit = 2 using the same directories ---
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        async with GitHubClient(client=mock_httpx, cache_path=cache_path) as client2:
            orchestrator2 = PipelineOrchestrator(
                config=test_config,
                client=client2,
                limit=2,
            )
            result2 = await orchestrator2.run_async()

    assert result2["accepted_count"] == 2
    dataset2 = load_repositories_dataset(result2["parquet_path"])
    assert len(dataset2) == 2
    names = [r["full_name"] for r in dataset2]
    assert names == ["org/repo-valid-1", "org/repo-valid-2"]


CFR_B_COLUMNS = [
    "cfr_b",
    "cfr_b_tier",
    "cfr_b_failed_releases",
    "cfr_b_evaluated_releases",
    "cfr_b_censored_releases",
    "cfr_b_skipped_releases",
]


def _synthetic_release_commits(fix_message: str = "fix: crash on open"):
    """C1 releases: v2.0.0 -> v2.0.1 (patch + fix, 2 days later) -> v2.1.0 (months later)."""
    from metricas.schemas import Commit, Release
    from pipeline.commits import ComparisonStatus, ReleaseCommits

    r0 = Release(tag_name="v2.0.0", published_at="2026-01-10T12:00:00Z", commit_sha="s0")
    r1 = Release(tag_name="v2.0.1", published_at="2026-01-12T12:00:00Z", commit_sha="s1")
    r2 = Release(tag_name="v2.1.0", published_at="2026-06-01T12:00:00Z", commit_sha="s2")
    fix = Commit(sha="c1", committed_at="2026-01-11T10:00:00Z", message=fix_message)
    feat = Commit(sha="c2", committed_at="2026-05-20T10:00:00Z", message="feat: new thing")
    return [
        ReleaseCommits(r0, None, ComparisonStatus.FIRST_RELEASE),
        ReleaseCommits(r1, r0, ComparisonStatus.OK, [fix]),
        ReleaseCommits(r2, r1, ComparisonStatus.OK, [feat]),
    ]


def test_compute_cfr_b_columns_failed_release():
    from pipeline.orchestrator import compute_cfr_b_columns

    cols = compute_cfr_b_columns(_synthetic_release_commits(), "2026-09-30")

    assert set(cols) == set(CFR_B_COLUMNS)
    assert cols["cfr_b_failed_releases"] == 1  # v2.0.0 followed by corrective v2.0.1
    assert cols["cfr_b_evaluated_releases"] == 3
    assert cols["cfr_b_censored_releases"] == 0
    assert cols["cfr_b_skipped_releases"] == 0
    assert cols["cfr_b"] == pytest.approx(1 / 3)
    assert cols["cfr_b_tier"] == "Medium"


def test_compute_cfr_b_columns_censored_and_skipped():
    from metricas.schemas import Release
    from pipeline.commits import ComparisonStatus, ReleaseCommits
    from pipeline.orchestrator import compute_cfr_b_columns

    r0 = Release(tag_name="v1.0.0", published_at="2026-01-10T12:00:00Z", commit_sha="s0")
    r1 = Release(tag_name="v1.0.1", published_at="2026-01-11T12:00:00Z", commit_sha="s1")
    r2 = Release(tag_name="v1.1.0", published_at="2026-09-28T12:00:00Z", commit_sha="s2")
    rcs = [
        ReleaseCommits(r0, None, ComparisonStatus.FIRST_RELEASE),
        # compare 404: commits unknown -> v1.0.0 cannot be judged
        ReleaseCommits(r1, r0, ComparisonStatus.NOT_FOUND),
        ReleaseCommits(r2, r1, ComparisonStatus.OK, []),
    ]

    cols = compute_cfr_b_columns(rcs, "2026-09-30")

    assert cols["cfr_b_skipped_releases"] == 1
    assert cols["cfr_b_censored_releases"] == 1
    assert cols["cfr_b_evaluated_releases"] == 1
    assert cols["cfr_b_failed_releases"] == 0
    assert cols["cfr_b"] == 0.0
    assert cols["cfr_b_tier"] == "Elite"


def test_compute_cfr_b_columns_nothing_evaluated():
    from metricas.schemas import Release
    from pipeline.commits import ComparisonStatus, ReleaseCommits
    from pipeline.orchestrator import compute_cfr_b_columns

    r0 = Release(tag_name="v1.0.0", published_at="2026-09-28T12:00:00Z", commit_sha="s0")
    cols = compute_cfr_b_columns(
        [ReleaseCommits(r0, None, ComparisonStatus.FIRST_RELEASE)], "2026-09-30"
    )

    assert cols["cfr_b"] is None
    assert cols["cfr_b_tier"] is None
    assert cols["cfr_b_evaluated_releases"] == 0
    assert cols["cfr_b_censored_releases"] == 1


def test_compute_cfr_b_columns_unknown_heuristic():
    from pipeline.orchestrator import compute_cfr_b_columns

    with pytest.raises(KeyError):
        compute_cfr_b_columns(_synthetic_release_commits(), "2026-09-30", heuristic="v999")


def test_orchestrator_rejects_unknown_cfr_b_heuristic(test_config: dict[str, Any]):
    test_config["cfr_b"] = {"heuristica": "v999"}
    with pytest.raises(ValueError, match="v999"):
        PipelineOrchestrator(config=test_config)


def test_orchestrator_cfr_b_heuristic_defaults_and_config(test_config: dict[str, Any]):
    assert PipelineOrchestrator(config=test_config).cfr_b_heuristic == "v1"
    test_config["cfr_b"] = {"heuristica": "v1"}
    assert PipelineOrchestrator(config=test_config).cfr_b_heuristic == "v1"


async def test_pipeline_exports_cfr_b_columns(
    test_config: dict[str, Any], tmp_path: Path, monkeypatch
):
    """E2E: orchestrator computes CFR (b) on C1 releases and persists the columns."""

    async def fake_collect_commits(client, owner, repo, window, git_dir=None):
        return _synthetic_release_commits()

    monkeypatch.setattr("pipeline.orchestrator.collect_release_commits", fake_collect_commits)

    transport = httpx.MockTransport(_build_mock_http_handler())
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        async with GitHubClient(
            client=mock_httpx,
            cache_path=tmp_path / "cache" / "http_cache.sqlite",
        ) as client:
            orchestrator = PipelineOrchestrator(config=test_config, client=client, limit=2)
            result = await orchestrator.run_async()

    records = load_repositories_dataset(result["parquet_path"])
    assert len(records) == 2
    for rec in records:
        assert rec["cfr_b"] == pytest.approx(1 / 3)
        assert rec["cfr_b_tier"] == "Medium"
        assert rec["cfr_b_failed_releases"] == 1
        assert rec["cfr_b_evaluated_releases"] == 3
        assert rec["cfr_b_censored_releases"] == 0
        assert rec["cfr_b_skipped_releases"] == 0

    with open(result["csv_path"], "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert all(col in rows[0] for col in CFR_B_COLUMNS)
    assert float(rows[0]["cfr_b"]) == pytest.approx(1 / 3)
    assert rows[0]["cfr_b_tier"] == "Medium"


async def test_pipeline_cfr_b_default_fixture_has_no_failures(
    test_config: dict[str, Any], tmp_path: Path
):
    """With monthly releases and no fix commits nothing fails; the last-week release is censored."""
    test_config["janela"]["fim"] = "2026-06-20"  # last mock release (06-15) falls in the censored week
    transport = httpx.MockTransport(_build_mock_http_handler())
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        async with GitHubClient(
            client=mock_httpx,
            cache_path=tmp_path / "cache" / "http_cache.sqlite",
        ) as client:
            orchestrator = PipelineOrchestrator(config=test_config, client=client, limit=1)
            result = await orchestrator.run_async()

    rec = load_repositories_dataset(result["parquet_path"])[0]
    assert rec["cfr_b"] == 0.0
    assert rec["cfr_b_tier"] == "Elite"
    assert rec["cfr_b_failed_releases"] == 0
    assert rec["cfr_b_censored_releases"] == 1
    assert rec["cfr_b_evaluated_releases"] + rec["cfr_b_skipped_releases"] == 5


def test_load_repositories_dataset_old_file_without_cfr_b_columns(tmp_path: Path):
    """Datasets written before CFR (b) existed load with None in the new columns."""
    import pyarrow as pa

    path = tmp_path / "old.parquet"
    pq.write_table(
        pa.table({"full_name": ["org/old"], "stars": [1234]}),
        path,
    )

    rec = load_repositories_dataset(path)[0]
    assert rec["full_name"] == "org/old"
    for col in CFR_B_COLUMNS:
        assert rec[col] is None

    # Re-saving an old record keeps working and writes nulls
    out = tmp_path / "new.parquet"
    save_repositories_dataset([rec], out, tmp_path / "new.csv")
    assert load_repositories_dataset(out)[0]["cfr_b"] is None

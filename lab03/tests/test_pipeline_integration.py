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
        assert "Busca inicial por estrelas (Search API)" in stages[0]
        assert "Filtro de uso de CI/CD (GitHub Actions)" in stages[1]
        assert "Filtro de releases na janela" in stages[2]
        assert "Filtro de workflow runs na janela" in stages[3]
        assert "Amostra final selecionada" in stages[4]

        # Check discards
        assert int(funnel_rows[1]["descartados"]) == 1  # repo-no-actions
        assert int(funnel_rows[2]["descartados"]) == 1  # repo-few-releases
        assert int(funnel_rows[4]["quantidade_restante"]) == 2

    # Verify workflow runs parquet files
    runs_dir = Path(test_config["diretorios"]["dados"]) / "runs"
    assert (runs_dir / "org__repo-valid-1.parquet").is_file()
    assert (runs_dir / "org__repo-valid-2.parquet").is_file()
    # Discarded repos must not have runs parquet files
    assert not (runs_dir / "org__repo-no-actions.parquet").exists()
    assert not (runs_dir / "org__repo-few-releases.parquet").exists()


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

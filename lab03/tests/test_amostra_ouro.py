"""Testes para o módulo de amostragem-ouro e geração de planilhas (Issue #63)."""

from datetime import datetime
from pathlib import Path
import json

import openpyxl
import pandas as pd
import pytest

from analises.amostra_ouro import (
    DEFAULT_SEED,
    OPCOES_ENTREGA_REAL,
    OPCOES_RELEASE_CORRETIVA,
    OPCOES_TIPO_PROJETO,
    ReleaseItem,
    RepoSampleItem,
    construir_dados_amostra_ouro,
    exportar_planilhas,
    gerar_dataframe_rotulacao,
    salvar_planilha_excel,
    sortear_releases_repositorio,
    sortear_repositorios,
)


@pytest.fixture
def dummy_repos_df():
    return pd.DataFrame(
        [
            {
                "owner": f"owner{i}",
                "name": f"repo{i}",
                "full_name": f"owner{i}/repo{i}",
                "stars": 1000 + i * 10,
                "language": "Python" if i % 2 == 0 else "TypeScript",
                "releases_count_window": 10 + i,
            }
            for i in range(100)
        ]
    )


def test_sortear_repositorios_reprodutivel(tmp_path: Path, dummy_repos_df: pd.DataFrame):
    parquet_path = tmp_path / "repos.parquet"
    dummy_repos_df.to_parquet(parquet_path)

    sample1 = sortear_repositorios(parquet_path, n=60, seed=42)
    sample2 = sortear_repositorios(parquet_path, n=60, seed=42)
    sample_diff_seed = sortear_repositorios(parquet_path, n=60, seed=99)

    assert len(sample1) == 60
    assert len(sample2) == 60
    assert sample1["full_name"].tolist() == sample2["full_name"].tolist()
    assert sample1["full_name"].tolist() != sample_diff_seed["full_name"].tolist()


def test_sortear_releases_reprodutivel():
    releases = [
        ReleaseItem(
            tag_name=f"v1.{i}.0",
            published_at=f"2026-0{i+1}-15T12:00:00Z",
            release_url=f"https://github.com/org/repo/releases/tag/v1.{i}.0",
        )
        for i in range(10)
    ]

    s1 = sortear_releases_repositorio(releases, n=5, seed=123)
    s2 = sortear_releases_repositorio(releases, n=5, seed=123)
    s_diff = sortear_releases_repositorio(releases, n=5, seed=999)

    assert len(s1) == 5
    assert [r.tag_name for r in s1] == [r.tag_name for r in s2]
    assert [r.tag_name for r in s1] != [r.tag_name for r in s_diff]

    # Garante que as 5 sorteadas estão em ordem cronológica
    dates = [r.published_at for r in s1]
    assert dates == sorted(dates)


def test_sortear_releases_poucas_releases():
    releases = [
        ReleaseItem(
            tag_name=f"v1.{i}.0",
            published_at=f"2026-0{i+1}-01T00:00:00Z",
            release_url=f"https://github.com/org/repo/releases/tag/v1.{i}.0",
        )
        for i in range(3)
    ]
    sampled = sortear_releases_repositorio(releases, n=5, seed=42)
    assert len(sampled) == 3
    assert [r.tag_name for r in sampled] == ["v1.0.0", "v1.1.0", "v1.2.0"]


def test_dataframe_rotulacao_sem_colunas_heuristica():
    """Garante que NENHUMA coluna da heurística é vazada para a planilha de rotulação."""
    rel = ReleaseItem(
        tag_name="v1.0.0",
        published_at="2026-01-01T00:00:00Z",
        release_url="https://github.com/org/repo/releases/tag/v1.0.0",
    )
    item = RepoSampleItem(
        repo_idx=1,
        full_name="org/repo",
        owner="org",
        name="repo",
        repo_url="https://github.com/org/repo",
        stars=5000,
        language="Python",
        releases_count_window=10,
        releases=[rel],
    )

    df = gerar_dataframe_rotulacao([item])

    # Colunas proibidas da heurística
    colunas_proibidas = {
        "cfr_b",
        "heuristic",
        "heuristica",
        "is_corrective",
        "corrective",
        "commits_count",
        "has_fix",
        "lead_time_a_hours",
        "lead_time_b_hours",
    }

    colunas_atuais = set(df.columns)
    assert not (colunas_proibidas & colunas_atuais), f"Colunas da heurística encontradas: {colunas_proibidas & colunas_atuais}"

    # Colunas obrigatórias
    colunas_esperadas = {
        "repo_idx",
        "repo_name",
        "repo_url",
        "tipo_projeto",
        "entrega_real",
        "release_idx",
        "tag_name",
        "published_at",
        "release_url",
        "release_corretiva",
        "notas_justificativa",
    }
    assert colunas_esperadas.issubset(colunas_atuais)

    # Campos de preenchimento devem estar vazios
    assert df.loc[0, "tipo_projeto"] == ""
    assert df.loc[0, "entrega_real"] == ""
    assert df.loc[0, "release_corretiva"] == ""


def test_exportar_planilhas_csv_e_excel(tmp_path: Path):
    rel = ReleaseItem(
        tag_name="v1.0.0",
        published_at="2026-01-01T00:00:00Z",
        release_url="https://github.com/org/repo/releases/tag/v1.0.0",
    )
    item = RepoSampleItem(
        repo_idx=1,
        full_name="org/repo",
        owner="org",
        name="repo",
        repo_url="https://github.com/org/repo",
        stars=1000,
        language="Rust",
        releases_count_window=5,
        releases=[rel],
    )
    df = gerar_dataframe_rotulacao([item])

    avaliadores = [
        {"id": "marcela", "nome": "Marcela Campos"},
        {"id": "gabriel", "nome": "Gabriel Assis"},
        {"id": "joao", "nome": "João Pedro Peres"},
    ]

    arquivos = exportar_planilhas(df, tmp_path, avaliadores=avaliadores)

    # Verifica que foram gerados arquivos para cada avaliador + template
    assert "marcela" in arquivos
    assert "gabriel" in arquivos
    assert "joao" in arquivos
    assert "template" in arquivos

    for av_id in ["marcela", "gabriel", "joao", "template"]:
        csv_file, xlsx_file = arquivos[av_id]
        assert csv_file.is_file()
        assert xlsx_file.is_file()

        # Valida CSV
        df_csv = pd.read_csv(csv_file)
        assert len(df_csv) == 1
        assert df_csv.loc[0, "repo_name"] == "org/repo"

        # Valida Excel com openpyxl
        wb = openpyxl.load_workbook(xlsx_file)
        assert "Rotulacao_Amostra_Ouro" in wb.sheetnames
        assert "Instrucoes" in wb.sheetnames
        ws = wb["Rotulacao_Amostra_Ouro"]
        assert ws.cell(row=1, column=1).value == "repo_idx"
        assert ws.cell(row=2, column=2).value == "org/repo"

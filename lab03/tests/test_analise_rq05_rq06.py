"""Testes unitários da análise empírica das RQ 05 e RQ 06 (Sprint 03 - Gabriel Assis)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analises.analise_rq05_rq06 import (
    aplicar_correcao_holm_kruskal,
    aplicar_correcao_holm_pareadas,
    calcular_cliffs_delta,
    calcular_spearman,
    executar_analise_rq05_rq06,
    executar_comparacoes_pareadas,
    executar_kruskal,
    interpretar_cliffs_delta,
    interpretar_epsilon_squared,
    interpretar_spearman,
    main,
    preparar_fatores,
)


def test_interpretar_spearman():
    assert "fraca positiva" in interpretar_spearman(0.25)
    assert "moderada negativa" in interpretar_spearman(-0.45)
    assert "forte positiva" in interpretar_spearman(0.65)
    assert "desprezível" in interpretar_spearman(0.05)


def test_interpretar_epsilon_squared():
    assert interpretar_epsilon_squared(0.005) == "desprezível"
    assert interpretar_epsilon_squared(0.03) == "pequeno"
    assert interpretar_epsilon_squared(0.08) == "médio"
    assert interpretar_epsilon_squared(0.20) == "grande"
    assert interpretar_epsilon_squared(float("nan")) == "desprezível"


def test_interpretar_cliffs_delta():
    assert interpretar_cliffs_delta(0.10) == "desprezível"
    assert interpretar_cliffs_delta(0.25) == "pequeno"
    assert interpretar_cliffs_delta(0.40) == "médio"
    assert interpretar_cliffs_delta(0.60) == "grande"
    assert interpretar_cliffs_delta(float("nan")) == "indefinido"


def test_calcular_spearman_basico():
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    res = calcular_spearman(x, y, "RQ_TEST", "x", "y", "Teste Perfeito")

    assert res.n_pares == 5
    assert pytest.approx(res.rho) == 1.0
    assert res.p_valor < 0.01
    assert res.significativo_05 is True


def test_calcular_spearman_com_nulos():
    x = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])
    y = pd.Series([5.0, np.nan, 3.0, 2.0, 1.0])
    res = calcular_spearman(x, y, "RQ_TEST", "x", "y", "Teste Nulos")

    assert res.n_pares == 3  # apenas índices 0, 3, 4 têm ambos
    assert res.rho < 0.0


def test_calcular_spearman_poucos_dados():
    x = pd.Series([1.0, np.nan])
    y = pd.Series([1.0, 2.0])
    res = calcular_spearman(x, y, "RQ_TEST", "x", "y", "Teste Poucos")
    assert res.n_pares == 1
    assert np.isnan(res.rho)
    assert res.significativo_05 is False


def test_calcular_cliffs_delta():
    g1 = np.array([10.0, 20.0, 30.0])
    g2 = np.array([1.0, 2.0, 3.0])
    delta, interp = calcular_cliffs_delta(g1, g2)
    assert pytest.approx(delta) == 1.0
    assert interp == "grande"

    # Invertido
    delta_inv, interp_inv = calcular_cliffs_delta(g2, g1)
    assert pytest.approx(delta_inv) == -1.0
    assert interp_inv == "grande"


def test_preparar_fatores():
    df = pd.DataFrame({
        "full_name": ["org/a", "org/b", "org/c", "org/d"],
        "stars": [1000, 5000, 10000, 50000],
        "contributors_count": [5, 20, 80, 300],
        "language": ["Python", "Python", "Go", "Rust"],
        "created_at": [
            "2020-01-01T00:00:00Z",
            "2022-01-01T00:00:00Z",
            "2024-01-01T00:00:00Z",
            "2025-01-01T00:00:00Z",
        ],
    })
    df_tipo = pd.DataFrame({
        "full_name": ["org/a", "org/b", "org/c", "org/d"],
        "tipo_projeto": ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro"],
    })

    df_res = preparar_fatores(df, df_tipo)

    assert "quartil_estrelas" in df_res.columns
    assert "quartil_contribuidores" in df_res.columns
    assert "quartil_idade" in df_res.columns
    assert "linguagem_grupo" in df_res.columns
    assert "tipo_projeto" in df_res.columns
    assert (df_res["idade_anos"] > 0).all()


def test_executar_kruskal():
    df = pd.DataFrame({
        "grupo": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
        "valor": [10.0, 11.0, 12.0, 20.0, 21.0, 22.0, 30.0, 31.0, 32.0],
    })
    res = executar_kruskal(df, "grupo", "Fator Grupo", "valor", "Métrica Valor")

    assert res.k_grupos == 3
    assert res.n_total == 9
    assert res.h_stat > 0
    assert res.p_valor < 0.05
    assert res.significativo_raw is True
    assert res.epsilon_squared > 0.5


def test_executar_comparacoes_pareadas():
    df = pd.DataFrame({
        "grupo": ["A", "A", "A", "B", "B", "B"],
        "valor": [10.0, 11.0, 12.0, 50.0, 51.0, 52.0],
    })
    pares = [("A", "B")]
    res = executar_comparacoes_pareadas(df, "grupo", pares, "valor", "Métrica Valor")

    assert len(res) == 1
    assert res[0].grupo1 == "A"
    assert res[0].grupo2 == "B"
    assert res[0].cliffs_delta == -1.0


def test_correcao_holm():
    df = pd.DataFrame({
        "grupo": ["A", "A", "B", "B", "C", "C"],
        "v1": [1.0, 2.0, 10.0, 11.0, 20.0, 21.0],
        "v2": [1.0, 1.1, 1.0, 1.1, 1.0, 1.1],
    })
    k1 = executar_kruskal(df, "grupo", "Grupo", "v1", "v1")
    k2 = executar_kruskal(df, "grupo", "Grupo", "v2", "v2")

    res = aplicar_correcao_holm_kruskal([k1, k2])
    assert res[0].p_valor_holm >= res[0].p_valor
    assert res[1].p_valor_holm >= res[1].p_valor


def test_executar_analise_ponta_a_ponta(tmp_path: Path):
    np.random.seed(42)
    n = 20
    df = pd.DataFrame({
        "full_name": [f"org/repo{i}" for i in range(n)],
        "stars": np.random.randint(1000, 50000, n),
        "contributors_count": np.random.randint(5, 500, n),
        "language": np.random.choice(["Python", "TypeScript", "Go", "Rust"], n),
        "created_at": ["2022-01-01T00:00:00Z"] * n,
        "deployment_frequency": np.random.uniform(0.1, 5.0, n),
        "lead_time_b_hours": np.random.uniform(1.0, 200.0, n),
        "cfr_a": np.random.uniform(0.01, 0.30, n),
        "cfr_b": np.random.uniform(0.05, 0.40, n),
        "recovery_hours": np.random.uniform(0.5, 24.0, n),
    })
    df_tipo = pd.DataFrame({
        "full_name": [f"org/repo{i}" for i in range(n)],
        "tipo_projeto": np.random.choice(
            ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro"], n
        ),
    })

    csv_path = tmp_path / "repositorios.csv"
    tipo_path = tmp_path / "tipo_projeto.csv"
    df.to_csv(csv_path, index=False)
    df_tipo.to_csv(tipo_path, index=False)

    out_dir = tmp_path / "saida_rq05_rq06"
    res = executar_analise_rq05_rq06(csv_path, tipo_path, out_dir)

    assert len(res["rq05"]) == 2
    assert len(res["rq06_kruskal"]) == 25  # 5 fatores x 5 métricas
    assert len(res["rq06_comparacoes_pareadas"]) > 0
    assert (out_dir / "tabela_rq05_spearman.tex").is_file()
    assert (out_dir / "tabela_rq05_spearman.md").is_file()
    assert (out_dir / "tabela_rq06_kruskal.tex").is_file()
    assert (out_dir / "tabela_rq06_kruskal.md").is_file()
    assert (out_dir / "rq05_rq06_metricas.json").is_file()

    figs = list((out_dir / "figuras").glob("*.png"))
    assert len(figs) >= 3


def test_main_cli(tmp_path: Path):
    n = 10
    df = pd.DataFrame({
        "full_name": [f"org/repo{i}" for i in range(n)],
        "stars": [1000 * (i + 1) for i in range(n)],
        "contributors_count": [10 * (i + 1) for i in range(n)],
        "language": ["Python" if i % 2 == 0 else "TypeScript" for i in range(n)],
        "created_at": ["2023-01-01T00:00:00Z"] * n,
        "deployment_frequency": [0.5 * (i + 1) for i in range(n)],
        "lead_time_b_hours": [10.0 * (i + 1) for i in range(n)],
        "cfr_a": [0.02 * (i + 1) for i in range(n)],
        "cfr_b": [0.03 * (i + 1) for i in range(n)],
        "recovery_hours": [1.0 * (i + 1) for i in range(n)],
    })
    csv_path = tmp_path / "repos.csv"
    df.to_csv(csv_path, index=False)
    out_dir = tmp_path / "saida_cli"

    code = main(["--dataset", str(csv_path), "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "tabela_rq05_spearman.tex").is_file()

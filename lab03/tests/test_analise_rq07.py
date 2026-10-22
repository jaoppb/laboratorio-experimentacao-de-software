"""Testes unitários da análise de sensibilidade DORA (RQ 07 - Sprint 03 - João Pedro Peres)."""

from pathlib import Path

import pandas as pd
import pytest

from analises.analise_rq07 import (
    avaliar_combinacao_c1,
    avaliar_combinacao_c2,
    avaliar_combinacao_c3,
    calcular_sensibilidade_par,
    executar_analise_rq07,
    interpretar_kappa_fleiss_landis,
    main,
)


def test_interpretar_kappa():
    assert interpretar_kappa_fleiss_landis(0.15) == "leve"
    assert interpretar_kappa_fleiss_landis(0.35) == "razoável"
    assert interpretar_kappa_fleiss_landis(0.55) == "moderada"
    assert interpretar_kappa_fleiss_landis(0.75) == "substancial"
    assert interpretar_kappa_fleiss_landis(0.95) == "quase perfeita"
    assert interpretar_kappa_fleiss_landis(-0.1) == "pobre / sem concordância"


def test_calcular_sensibilidade_par_identicos():
    s1 = pd.Series(["Elite", "High", "Medium", "Low"])
    s2 = pd.Series(["Elite", "High", "Medium", "Low"])
    res = calcular_sensibilidade_par(s1, s2, "C1", "C2")

    assert res.n_repositorios == 4
    assert res.n_mudaram == 0
    assert res.percentual_mudanca == 0.0
    assert res.n_iguais == 4
    assert pytest.approx(res.kappa_linear) == 1.0


def test_calcular_sensibilidade_par_com_mudancas():
    # Elite=4, High=3, Medium=2, Low=1
    s1 = pd.Series(["Medium", "Medium", "High", "Low"])
    s2 = pd.Series(["High", "Low", "High", "Low"])
    res = calcular_sensibilidade_par(s1, s2, "C1", "C2")

    assert res.n_repositorios == 4
    assert res.n_mudaram == 2
    assert res.percentual_mudanca == 50.0
    assert res.n_subiram == 1  # Medium -> High
    assert res.n_desceram == 1  # Medium -> Low
    assert res.n_iguais == 2
    assert res.kappa_linear < 1.0


def test_avaliacoes_combinacoes():
    df = pd.DataFrame({
        "deployment_tier": ["High"],
        "lead_time_tier": ["High"],
        "cfr_tier": ["Elite"],
        "recovery_tier": ["High"],
        "c2_deployment_frequency": [1.5],
        "c2_lead_time_b_hours": [48.0],
        "c2_cfr_b": [0.10],
        "cfr_b": [0.10],
        "c3_deployment_frequency": [2.0],
        "c3_lead_time_b_hours": [36.0],
    })

    df_c1 = avaliar_combinacao_c1(df)
    assert len(df_c1) == 1
    assert "c1_overall_tier" in df_c1.columns

    df_c2 = avaliar_combinacao_c2(df)
    assert len(df_c2) == 1
    assert "c2_overall_tier" in df_c2.columns

    df_c3 = avaliar_combinacao_c3(df)
    assert len(df_c3) == 1
    assert "c3_overall_tier" in df_c3.columns


def test_executar_analise_ponta_a_ponta(tmp_path: Path):
    n = 10
    df = pd.DataFrame({
        "full_name": [f"org/repo{i}" for i in range(n)],
        "deployment_tier": ["High"] * n,
        "lead_time_tier": ["Medium"] * n,
        "cfr_tier": ["Elite"] * n,
        "recovery_tier": ["High"] * n,
        "c2_deployment_frequency": [0.5 * (i + 1) for i in range(n)],
        "c2_lead_time_b_hours": [24.0 * (i + 1) for i in range(n)],
        "c2_cfr_b": [0.05 * (i % 4) for i in range(n)],
        "cfr_b": [0.05 * (i % 4) for i in range(n)],
        "c3_deployment_frequency": [0.8 * (i + 1) for i in range(n)],
        "c3_lead_time_b_hours": [20.0 * (i + 1) for i in range(n)],
    })

    csv_path = tmp_path / "repositorios.csv"
    df.to_csv(csv_path, index=False)

    out_dir = tmp_path / "saida_rq07"
    res = executar_analise_rq07(csv_path, out_dir)

    assert res["n_repositorios"] == n
    assert len(res["comparacoes_pares"]) == 3
    assert (out_dir / "tabela_rq07_sensibilidade.tex").is_file()
    assert (out_dir / "tabela_rq07_sensibilidade.md").is_file()
    assert (out_dir / "tabela_rq07_distribuicao_tiers.tex").is_file()
    assert (out_dir / "tabela_rq07_distribuicao_tiers.md").is_file()
    assert (out_dir / "rq07_sensibilidade.json").is_file()

    figs = list((out_dir / "figuras").glob("*.png"))
    assert len(figs) == 2


def test_main_cli(tmp_path: Path):
    df = pd.DataFrame({
        "full_name": ["org/repo1"],
        "deployment_tier": ["High"],
        "lead_time_tier": ["High"],
        "cfr_tier": ["Elite"],
        "recovery_tier": ["High"],
        "c2_deployment_frequency": [1.0],
        "c2_lead_time_b_hours": [24.0],
        "c2_cfr_b": [0.10],
        "cfr_b": [0.10],
        "c3_deployment_frequency": [1.2],
        "c3_lead_time_b_hours": [20.0],
    })
    csv_path = tmp_path / "repos.csv"
    df.to_csv(csv_path, index=False)
    out_dir = tmp_path / "saida_cli"

    code = main(["--dataset", str(csv_path), "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "tabela_rq07_sensibilidade.tex").is_file()

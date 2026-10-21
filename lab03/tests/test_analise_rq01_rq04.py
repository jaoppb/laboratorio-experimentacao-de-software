"""Testes unitários da análise descritiva das RQ 01 a RQ 04 (Sprint 03)."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from analises.analise_rq01_rq04 import (
    EstatisticasDescritivas,
    calcular_distribuicao_tiers,
    calcular_estatisticas,
    executar_analise,
    main,
)


def test_calcular_estatisticas_basico():
    dados = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    est = calcular_estatisticas(dados, "teste", "Métrica Teste", "unid")
    assert est.n_total == 5
    assert est.n_validos == 5
    assert est.n_nulos == 0
    assert est.mediana == 30.0
    assert est.q1 == 20.0
    assert est.q3 == 40.0
    assert est.iqr == 20.0
    assert est.minimo == 10.0
    assert est.maximo == 50.0
    assert est.media == 30.0


def test_calcular_estatisticas_com_nulos():
    dados = pd.Series([10.0, np.nan, 30.0, None, 50.0])
    est = calcular_estatisticas(dados, "teste", "Métrica Teste", "unid")
    assert est.n_total == 5
    assert est.n_validos == 3
    assert est.n_nulos == 2
    assert est.mediana == 30.0
    assert est.minimo == 10.0
    assert est.maximo == 50.0


def test_calcular_estatisticas_vazio():
    dados = pd.Series([np.nan, None])
    est = calcular_estatisticas(dados, "teste", "Métrica Teste", "unid")
    assert est.n_total == 2
    assert est.n_validos == 0
    assert est.n_nulos == 2
    assert np.isnan(est.mediana)


def test_calcular_distribuicao_tiers():
    df = pd.DataFrame({
        "tier": ["Elite", "High", "High", "Medium", "Low", "Low", "Low"]
    })
    res = calcular_distribuicao_tiers(df, "tier")
    assert res["Elite"]["quantidade"] == 1
    assert res["High"]["quantidade"] == 2
    assert res["Medium"]["quantidade"] == 1
    assert res["Low"]["quantidade"] == 3
    assert pytest.approx(res["Elite"]["percentual"]) == (1 / 7) * 100
    assert pytest.approx(res["Low"]["percentual"]) == (3 / 7) * 100


def test_executar_analise_ponta_a_ponta(tmp_path: Path):
    # Criar dataset sintético mínimo com todas as colunas esperadas
    df = pd.DataFrame({
        "full_name": [f"org/repo{i}" for i in range(10)],
        "deployment_frequency": [0.5, 1.2, 3.4, 0.1, 7.5, 1.0, 2.0, 0.8, 0.2, 4.0],
        "deployment_tier": ["Medium", "High", "High", "Low", "Elite", "High", "High", "Medium", "Low", "High"],
        "lead_time_a_hours": [10.0, 24.0, 48.0, 100.0, 5.0, 12.0, 30.0, 50.0, None, 15.0],
        "lead_time_b_hours": [8.0, 20.0, 40.0, 90.0, 4.0, 10.0, 25.0, 45.0, None, 12.0],
        "lead_time_tier": ["High", "High", "Medium", "Medium", "Elite", "High", "Medium", "Medium", None, "High"],
        "cfr_a": [0.05, 0.10, 0.20, 0.02, 0.01, 0.08, 0.15, 0.04, 0.03, 0.12],
        "cfr_tier": ["Elite", "Elite", "High", "Elite", "Elite", "Elite", "Elite", "Elite", "Elite", "Elite"],
        "cfr_b": [0.15, 0.25, 0.35, 0.05, 0.00, 0.20, 0.30, 0.10, 0.08, 0.22],
        "cfr_b_tier": ["Elite", "High", "Medium", "Elite", "Elite", "High", "High", "Elite", "Elite", "High"],
        "recovery_hours": [1.5, 3.0, 5.0, 0.5, 0.2, 2.0, 4.0, 1.0, 0.8, 2.5],
        "recovery_tier": ["High", "High", "High", "Elite", "Elite", "High", "High", "High", "Elite", "High"],
        "censored_episodes_ratio": [0.0, 0.05, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0],
        "overall_dora_tier": ["High", "High", "High", "Medium", "Elite", "High", "High", "High", "Medium", "High"],
    })
    
    csv_path = tmp_path / "repos.csv"
    df.to_csv(csv_path, index=False)
    
    out_dir = tmp_path / "saida"
    res = executar_analise(csv_path, out_dir)
    
    assert res["n_repositorios"] == 10
    assert len(res["estatisticas"]) == 7
    assert (out_dir / "tabela_metricas_dora.md").is_file()
    assert (out_dir / "tabela_metricas_dora.tex").is_file()
    assert (out_dir / "tabela_tiers_dora.tex").is_file()
    assert (out_dir / "rq01_rq04_metricas.json").is_file()
    
    figuras = list((out_dir / "figuras").glob("*.png"))
    assert len(figuras) == 5


def test_main_cli(tmp_path: Path):
    df = pd.DataFrame({
        "full_name": ["org/repo1"],
        "deployment_frequency": [1.0],
        "deployment_tier": ["High"],
        "lead_time_a_hours": [24.0],
        "lead_time_b_hours": [20.0],
        "lead_time_tier": ["High"],
        "cfr_a": [0.05],
        "cfr_tier": ["Elite"],
        "cfr_b": [0.10],
        "cfr_b_tier": ["Elite"],
        "recovery_hours": [2.0],
        "recovery_tier": ["High"],
        "censored_episodes_ratio": [0.0],
        "overall_dora_tier": ["High"],
    })
    csv_path = tmp_path / "repos.csv"
    df.to_csv(csv_path, index=False)
    out_dir = tmp_path / "saida_cli"
    
    ret = main(["--dataset", str(csv_path), "--output-dir", str(out_dir)])
    assert ret == 0
    assert (out_dir / "tabela_metricas_dora.tex").is_file()

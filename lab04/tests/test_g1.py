"""Testes da figura G1 em Plotly."""

from __future__ import annotations

import pandas as pd
import pytest
import plotly.graph_objects as go

from src.graficos.g1 import figura_g1, carregar_dados_reais, carregar_parametros


def test_figura_g1_retorna_figure():
    fig = figura_g1()
    assert isinstance(fig, go.Figure)
    assert "G1" in fig.layout.title.text
    # 4 traces: real_com, sim_com, real_sem, sim_sem
    assert len(fig.data) == 4


def test_figura_g1_eixos_log_e_unidades():
    fig = figura_g1()
    assert fig.layout.xaxis.type == "log"
    assert fig.layout.xaxis2.type == "log"
    assert "log10" in fig.layout.xaxis.title.text.lower()
    assert "horas" in fig.layout.xaxis.title.text.lower()
    assert "contagem de prs" in fig.layout.yaxis.title.text.lower()
    assert "contagem de prs" in fig.layout.yaxis2.title.text.lower()


def test_figura_g1_reprodutivel_com_semente():
    fig1 = figura_g1(semente=42)
    fig2 = figura_g1(semente=42)
    for t1, t2 in zip(fig1.data, fig2.data):
        assert list(t1.x) == list(t2.x)


def test_figura_g1_aceita_dataframe_customizado():
    df_custom = pd.DataFrame({
        "grupo": ["com_bot"] * 5 + ["sem_bot"] * 5,
        "tempo_merge_horas": [1.0, 2.0, 3.0, 4.0, 5.0, 0.5, 1.5, 2.5, 3.5, 4.5],
    })
    params_custom = {
        "com_bot": {"n": 5, "mediana": 3.0, "sigma_log": 1.0},
        "sem_bot": {"n": 5, "mediana": 2.0, "sigma_log": 0.8},
    }
    fig = figura_g1(dados_reais=df_custom, parametros=params_custom)
    assert isinstance(fig, go.Figure)
    assert len(fig.data[0].x) == 5
    assert len(fig.data[1].x) == 5


def test_csv_invalido_levanta_erro(tmp_path):
    csv_errado = tmp_path / "errado.csv"
    csv_errado.write_text("coluna_errada,outra\n1,2\n", encoding="utf-8")
    with pytest.raises(KeyError, match="colunas obrigatórias"):
        carregar_dados_reais(csv_errado)


def test_parametros_invalidos_levanta_erro(tmp_path):
    json_errado = tmp_path / "param.json"
    json_errado.write_text('{"com_bot": {"n": 30}}', encoding="utf-8")
    with pytest.raises(KeyError, match="ausente"):
        carregar_parametros(json_errado)

"""Testes da figura G3 (erro tipo I)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.graficos.g3 import figura_g3

DF = pd.DataFrame(
    [
        {"cenario": "referencia", "teste": "welch", "n_rep": 10000, "taxa_rejeicao": 0.037},
        {"cenario": "referencia", "teste": "mannwhitney", "n_rep": 10000, "taxa_rejeicao": 0.046},
        {"cenario": "outliers", "teste": "welch", "n_rep": 10000, "taxa_rejeicao": 0.017},
        {"cenario": "outliers", "teste": "mannwhitney", "n_rep": 10000, "taxa_rejeicao": 0.048},
    ]
)


def test_devolve_figura_plotly_com_titulo():
    fig = figura_g3(DF)
    assert isinstance(fig, go.Figure)
    assert "G3" in fig.layout.title.text


def test_uma_barra_por_teste_com_uma_posicao_por_situacao():
    fig = figura_g3(DF)
    assert [t.name for t in fig.data] == ["t de Welch", "Mann-Whitney"]
    assert all(len(t.x) == 2 for t in fig.data)
    assert list(fig.data[0].y) == pytest.approx([3.7, 1.7])


def test_cores_dos_testes_vem_do_estilo():
    from src.estilo import COR_MANNWHITNEY, COR_WELCH

    fig = figura_g3(DF)
    assert fig.data[0].marker.color == COR_WELCH
    assert fig.data[1].marker.color == COR_MANNWHITNEY


def test_linha_em_5_por_cento():
    fig = figura_g3(DF)
    linhas = [s for s in fig.layout.shapes if s.type == "line"]
    assert len(linhas) == 1
    assert linhas[0].y0 == pytest.approx(5.0) and linhas[0].y1 == pytest.approx(5.0)


def test_eixos_com_nome_e_unidade_e_legenda():
    fig = figura_g3(DF)
    assert "%" in fig.layout.yaxis.title.text
    assert fig.layout.xaxis.title.text
    assert all(t.name for t in fig.data)


def test_dados_padrao_cobrem_q1_e_q3():
    fig = figura_g3()
    assert len(fig.data[0].x) == 6


def test_nao_altera_entrada():
    copia = DF.copy()
    figura_g3(DF)
    pd.testing.assert_frame_equal(DF, copia)


def test_coluna_faltando():
    with pytest.raises(KeyError):
        figura_g3(DF.drop(columns=["teste"]))


def test_vazio_e_alfa_invalido():
    with pytest.raises(ValueError):
        figura_g3(DF.iloc[0:0])
    with pytest.raises(ValueError, match="alfa"):
        figura_g3(DF, alfa=1.5)


def test_taxa_fora_do_intervalo():
    ruim = DF.copy()
    ruim.loc[0, "taxa_rejeicao"] = 1.2
    with pytest.raises(ValueError, match="taxa_rejeicao"):
        figura_g3(ruim)


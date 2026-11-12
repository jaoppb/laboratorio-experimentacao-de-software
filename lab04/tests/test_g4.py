"""Testes da figura G4 (curvas de poder)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.estilo import COR_MANNWHITNEY, COR_WELCH
from src.graficos.g4 import figura_g4


def _linhas():
    out = []
    for cen, bonus in (("com_bot", 0.0), ("referencia", 0.1)):
        for teste, base in (("welch", 0.0), ("mannwhitney", 0.1)):
            for r, p in ((1.0, 0.05), (2.0, 0.3), (4.0, 0.7)):
                out.append(
                    {
                        "cenario": cen,
                        "teste": teste,
                        "razao_medianas": r,
                        "n_rep": 10000,
                        "taxa_rejeicao": min(1.0, p + base + bonus),
                    }
                )
    return out


DF = pd.DataFrame(_linhas())


def test_devolve_figura_plotly_com_titulo():
    fig = figura_g4(DF)
    assert isinstance(fig, go.Figure)
    assert "G4" in fig.layout.title.text


def test_uma_curva_por_situacao_e_teste():
    fig = figura_g4(DF)
    assert len(fig.data) == 4
    assert all(len(t.x) == 3 for t in fig.data)


def test_mesma_cor_para_cada_teste():
    fig = figura_g4(DF)
    for traco in fig.data:
        esperado = COR_WELCH if "Welch" in traco.name else COR_MANNWHITNEY
        assert traco.line.color == esperado


def test_curvas_ordenadas_pelo_efeito():
    embaralhado = DF.sample(frac=1.0, random_state=1)
    fig = figura_g4(embaralhado)
    for traco in fig.data:
        assert list(traco.x) == sorted(traco.x)


def test_eixos_legenda_e_linha_de_alfa():
    fig = figura_g4(DF)
    assert "razão" in fig.layout.xaxis.title.text
    assert "%" in fig.layout.yaxis.title.text
    assert all(t.name for t in fig.data)
    assert len([s for s in fig.layout.shapes if s.type == "line"]) == 1


def test_dados_padrao_cobrem_q2_e_q3():
    fig = figura_g4()
    assert len(fig.data) == 12  # 6 situações × 2 testes


def test_nao_altera_entrada():
    copia = DF.copy()
    figura_g4(DF)
    pd.testing.assert_frame_equal(DF, copia)


def test_validacoes():
    with pytest.raises(KeyError):
        figura_g4(DF.drop(columns=["razao_medianas"]))
    with pytest.raises(ValueError):
        figura_g4(DF.iloc[0:0])
    with pytest.raises(ValueError, match="alfa"):
        figura_g4(DF, alfa=0.0)
    ruim = DF.copy()
    ruim.loc[0, "taxa_rejeicao"] = -0.1
    with pytest.raises(ValueError, match="taxa_rejeicao"):
        figura_g4(ruim)


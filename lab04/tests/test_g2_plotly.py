"""Testes da figura G2 em versão Plotly."""

from __future__ import annotations

import copy
import pytest
import plotly.graph_objects as go
from scipy import stats

from src.graficos.g2_plotly import figura_g2_plotly

WELCH = {"estatistica": 2.1, "gl": 57.3, "p_valor": 2 * stats.t.sf(2.1, 57.3)}
MW = {"estatistica": -1.7, "p_valor": 2 * stats.norm.sf(1.7)}


def test_devolve_figura_plotly():
    fig = figura_g2_plotly(WELCH, MW)
    assert isinstance(fig, go.Figure)
    assert "G2" in fig.layout.title.text
    # Deve conter múltiplos traces (curva de densidade, rejeição, p-valor, observada)
    assert len(fig.data) >= 8


def test_nao_altera_entradas():
    w, m = copy.deepcopy(WELCH), copy.deepcopy(MW)
    figura_g2_plotly(w, m)
    assert w == WELCH and m == MW


def test_rotulos_e_unidades_dos_eixos():
    fig = figura_g2_plotly(WELCH, MW)
    assert "Estatística t" in fig.layout.xaxis.title.text
    assert "Estatística z" in fig.layout.xaxis2.title.text
    assert "Densidade" in fig.layout.yaxis.title.text
    assert "Densidade" in fig.layout.yaxis2.title.text


def test_estatistica_extrema_fica_visivel():
    fig = figura_g2_plotly(
        {"estatistica": 8.0, "gl": 40.0, "p_valor": 2 * stats.t.sf(8, 40)},
        MW,
    )
    x_range = fig.layout.xaxis.range
    assert x_range[0] < -8.0 < 8.0 < x_range[1]


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_alpha_invalido(alpha):
    with pytest.raises(ValueError, match="alpha"):
        figura_g2_plotly(WELCH, MW, alpha=alpha)


@pytest.mark.parametrize("gl", [0.0, -3.0, float("nan"), float("inf")])
def test_gl_invalido(gl):
    with pytest.raises(ValueError, match="gl"):
        figura_g2_plotly({**WELCH, "gl": gl}, MW)


@pytest.mark.parametrize("chave", ["estatistica", "gl", "p_valor"])
def test_chave_faltando_welch(chave):
    w = {k: v for k, v in WELCH.items() if k != chave}
    with pytest.raises(KeyError, match=chave):
        figura_g2_plotly(w, MW)


@pytest.mark.parametrize("chave", ["estatistica", "p_valor"])
def test_chave_faltando_mw(chave):
    m = {k: v for k, v in MW.items() if k != chave}
    with pytest.raises(KeyError, match=chave):
        figura_g2_plotly(WELCH, m)


@pytest.mark.parametrize("p", [float("nan"), -0.1, 1.2])
def test_p_valor_invalido(p):
    with pytest.raises(ValueError, match="p_valor"):
        figura_g2_plotly({**WELCH, "p_valor": p}, MW)


@pytest.mark.parametrize("alt", ["less", "greater"])
def test_recusa_alternativa_unilateral(alt):
    with pytest.raises(ValueError, match="bilateral"):
        figura_g2_plotly({**WELCH, "alternativa": alt}, MW)
    with pytest.raises(ValueError, match="bilateral"):
        figura_g2_plotly(WELCH, {**MW, "alternativa": alt})


def test_to_html_funciona():
    fig = figura_g2_plotly(WELCH, MW)
    html = fig.to_html(include_plotlyjs=False)
    assert len(html) > 100
    assert "plotly" in html.lower()


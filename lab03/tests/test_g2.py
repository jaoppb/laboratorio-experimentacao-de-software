"""Testes da figura G2."""

import copy

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
from scipy import stats

from src.graficos.g2 import figura_g2
from src.simulacao import gerar_dados
from src.testes import aplicar_mannwhitney, aplicar_welch

WELCH = {"estatistica": 2.1, "gl": 57.3, "p_valor": 2 * stats.t.sf(2.1, 57.3)}
MW = {"estatistica": -1.7, "p_valor": 2 * stats.norm.sf(1.7)}


def _area_poligono(caminho) -> float:
    """Área por fórmula do cadarço de um polígono do fill_between."""
    v = caminho.vertices
    x, y = v[:, 0], v[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _area_gid(ax, gid) -> float:
    total = 0.0
    for col in ax.collections:
        if col.get_gid() == gid:
            for caminho in col.get_paths():
                total += _area_poligono(caminho)
    return total


def test_devolve_figura_com_dois_eixos():
    fig = figura_g2(WELCH, MW)
    assert len(fig.axes) == 2
    assert "G2" in fig.get_suptitle()


def test_nao_altera_entradas():
    w, m = copy.deepcopy(WELCH), copy.deepcopy(MW)
    figura_g2(w, m)
    assert w == WELCH and m == MW


def test_area_do_p_valor_integra_ao_p_bilateral():
    fig = figura_g2(WELCH, MW)
    ax_t, ax_z = fig.axes
    assert _area_gid(ax_t, "area_p_valor") == pytest.approx(WELCH["p_valor"], abs=2e-3)
    assert _area_gid(ax_z, "area_p_valor") == pytest.approx(MW["p_valor"], abs=2e-3)


def test_area_de_rejeicao_integra_a_alpha():
    fig = figura_g2(WELCH, MW, alpha=0.1)
    for ax in fig.axes:
        assert _area_gid(ax, "area_rejeicao") == pytest.approx(0.1, abs=2e-3)


def test_valores_criticos_anotados():
    fig = figura_g2(WELCH, MW, alpha=0.05)
    crit_t = stats.t.ppf(0.975, WELCH["gl"])
    crit_z = stats.norm.ppf(0.975)
    textos_t = [t.get_text() for t in fig.axes[0].texts]
    textos_z = [t.get_text() for t in fig.axes[1].texts]
    assert f"±{crit_t:.3f}" in textos_t
    assert f"±{crit_z:.3f}" in textos_z


def test_estatistica_extrema_fica_visivel():
    fig = figura_g2({"estatistica": 8.0, "gl": 40.0, "p_valor": 2 * stats.t.sf(8, 40)}, MW)
    esq, dir_ = fig.axes[0].get_xlim()
    assert esq < -8.0 < 8.0 < dir_
    crit = stats.t.ppf(0.975, 40.0)
    assert esq < -crit and crit < dir_


def test_dados_reais_com_semente_fixa():
    rng = np.random.default_rng(7)
    a, b = gerar_dados(rng, 50, 50, 10.0, 12.0, 0.8, 0.8)
    w, m = aplicar_welch(a, b), aplicar_mannwhitney(a, b)
    fig = figura_g2(w, m)
    ax_t, ax_z = fig.axes
    assert _area_gid(ax_t, "area_p_valor") == pytest.approx(w["p_valor"], abs=2e-3)
    assert _area_gid(ax_z, "area_p_valor") == pytest.approx(m["p_valor"], abs=2e-3)
    fig.canvas.draw()


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_alpha_invalido(alpha):
    with pytest.raises(ValueError, match="alpha"):
        figura_g2(WELCH, MW, alpha=alpha)


@pytest.mark.parametrize("gl", [0.0, -3.0, float("nan"), float("inf")])
def test_gl_invalido(gl):
    with pytest.raises(ValueError, match="gl"):
        figura_g2({**WELCH, "gl": gl}, MW)


@pytest.mark.parametrize("chave", ["estatistica", "gl", "p_valor"])
def test_chave_faltando_welch(chave):
    w = {k: v for k, v in WELCH.items() if k != chave}
    with pytest.raises(KeyError, match=chave):
        figura_g2(w, MW)


@pytest.mark.parametrize("chave", ["estatistica", "p_valor"])
def test_chave_faltando_mw(chave):
    m = {k: v for k, v in MW.items() if k != chave}
    with pytest.raises(KeyError, match=chave):
        figura_g2(WELCH, m)


def test_renderiza_sem_erro():
    figura_g2(WELCH, MW).canvas.draw()


@pytest.mark.parametrize("p", [float("nan"), -0.1, 1.2])
def test_p_valor_invalido(p):
    with pytest.raises(ValueError, match="p_valor"):
        figura_g2({**WELCH, "p_valor": p}, MW)


@pytest.mark.parametrize("alt", ["less", "greater"])
def test_recusa_alternativa_unilateral(alt):
    with pytest.raises(ValueError, match="bilateral"):
        figura_g2({**WELCH, "alternativa": alt}, MW)
    with pytest.raises(ValueError, match="bilateral"):
        figura_g2(WELCH, {**MW, "alternativa": alt})

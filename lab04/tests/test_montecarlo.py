"""Testes de src.montecarlo."""

import dataclasses

import numpy as np
import pytest

from src import montecarlo
from src.montecarlo import ResultadoMonteCarlo, executar_montecarlo
from src.testes import aplicar_welch

H0 = dict(n_a=50, n_b=50, mediana_a=10.0, mediana_b=10.0, sigma_a=0.5, sigma_b=0.5)


@pytest.fixture(scope="module")
def res_h0():
    return executar_montecarlo(np.random.default_rng(42), **H0)


def test_formato_e_alinhamento():
    r = executar_montecarlo(np.random.default_rng(1), n_rep=25, **H0)
    assert r.p_welch.shape == r.p_mannwhitney.shape == (25,)
    assert r.p_welch.dtype == np.float64
    assert ((r.p_welch >= 0) & (r.p_welch <= 1)).all()
    assert ((r.p_mannwhitney >= 0) & (r.p_mannwhitney <= 1)).all()


def test_resultado_imutavel():
    r = executar_montecarlo(np.random.default_rng(1), n_rep=3, **H0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.p_welch = np.zeros(3)


def test_reprodutivel_com_mesma_semente():
    r1 = executar_montecarlo(np.random.default_rng(42), n_rep=200, **H0)
    r2 = executar_montecarlo(np.random.default_rng(42), n_rep=200, **H0)
    np.testing.assert_array_equal(r1.p_welch, r2.p_welch)
    np.testing.assert_array_equal(r1.p_mannwhitney, r2.p_mannwhitney)


def test_sementes_distintas_diferem():
    r1 = executar_montecarlo(np.random.default_rng(1), n_rep=50, **H0)
    r2 = executar_montecarlo(np.random.default_rng(2), n_rep=50, **H0)
    assert not np.array_equal(r1.p_welch, r2.p_welch)


def test_n_rep_padrao_10000():
    assert montecarlo.N_REP_PADRAO == 10_000
    import inspect

    assert inspect.signature(executar_montecarlo).parameters["n_rep"].default == 10_000


def test_taxa_h0_proxima_de_5_porcento(res_h0):
    taxas = res_h0.taxa_rejeicao(0.05)
    assert 0.04 <= taxas["welch"] <= 0.06
    assert 0.04 <= taxas["mannwhitney"] <= 0.06


def test_taxa_com_alfa_distinto(res_h0):
    taxas = res_h0.taxa_rejeicao(0.01)
    assert 0.005 <= taxas["welch"] <= 0.015
    assert 0.005 <= taxas["mannwhitney"] <= 0.015
    assert res_h0.taxa_rejeicao(0.01)["welch"] < res_h0.taxa_rejeicao(0.05)["welch"]


def test_h1_rejeita_muito():
    r = executar_montecarlo(
        np.random.default_rng(42),
        n_rep=300,
        **{**H0, "mediana_b": 20.0},
    )
    taxas = r.taxa_rejeicao(0.05)
    assert taxas["welch"] > 0.9
    assert taxas["mannwhitney"] > 0.9


def test_alternativa_repassada():
    bilateral = executar_montecarlo(np.random.default_rng(7), n_rep=30, **H0)
    maior = executar_montecarlo(
        np.random.default_rng(7), n_rep=30, alternativa="greater", **H0
    )
    assert not np.array_equal(bilateral.p_welch, maior.p_welch)
    assert not np.array_equal(bilateral.p_mannwhitney, maior.p_mannwhitney)


def test_primeira_repeticao_confere_com_testes_diretos():
    from src.simulacao import gerar_dados

    a, b = gerar_dados(np.random.default_rng(5), **H0)
    r = executar_montecarlo(np.random.default_rng(5), n_rep=1, **H0)
    assert r.p_welch[0] == aplicar_welch(a, b)["p_valor"]


@pytest.mark.parametrize("n_rep", [0, -1, 2.5, True, "10"])
def test_n_rep_invalido(n_rep):
    with pytest.raises(ValueError, match="n_rep"):
        executar_montecarlo(np.random.default_rng(1), n_rep=n_rep, **H0)


def test_parametro_invalido_propaga():
    with pytest.raises(ValueError):
        executar_montecarlo(np.random.default_rng(1), n_rep=2, **{**H0, "sigma_a": 0})


@pytest.mark.parametrize("alfa", [0, 1, -0.1, 1.5, True, float("nan")])
def test_alfa_invalido(alfa):
    r = ResultadoMonteCarlo(np.array([0.1]), np.array([0.2]))
    with pytest.raises(ValueError, match="alfa"):
        r.taxa_rejeicao(alfa)

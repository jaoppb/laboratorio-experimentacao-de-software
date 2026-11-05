"""Testes de src.testes (Welch e Mann-Whitney)."""

import numpy as np
import pytest
from scipy import stats

from src.testes import aplicar_mannwhitney, aplicar_welch


@pytest.fixture
def amostras():
    rng = np.random.default_rng(42)
    return rng.lognormal(0.0, 1.0, 60), rng.lognormal(0.4, 1.5, 90)


@pytest.mark.parametrize("alt", ["two-sided", "less", "greater"])
def test_welch_confere_com_scipy(amostras, alt):
    a, b = amostras
    r = aplicar_welch(a, b, alternativa=alt)
    ref = stats.ttest_ind(a, b, equal_var=False, alternative=alt)
    assert r["estatistica"] == pytest.approx(ref.statistic)
    assert r["p_valor"] == pytest.approx(ref.pvalue)
    assert r["gl"] == pytest.approx(ref.df)
    assert r["alternativa"] == alt


def test_welch_gl_formula_manual(amostras):
    a, b = amostras
    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    gl = (va + vb) ** 2 / (va**2 / (a.size - 1) + vb**2 / (b.size - 1))
    assert aplicar_welch(a, b)["gl"] == pytest.approx(gl)


def test_welch_cohen_d_e_sinal(amostras):
    a, b = amostras
    d = (a.mean() - b.mean()) / np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    r = aplicar_welch(a, b)
    assert r["tamanho_efeito"] == pytest.approx(d)
    assert aplicar_welch(b, a)["tamanho_efeito"] == pytest.approx(-d)
    assert (aplicar_welch(a + 100, b)["tamanho_efeito"]) > 0


def test_welch_unilaterais_somam_um(amostras):
    a, b = amostras
    soma = (
        aplicar_welch(a, b, alternativa="less")["p_valor"]
        + aplicar_welch(a, b, alternativa="greater")["p_valor"]
    )
    assert soma == pytest.approx(1.0)


@pytest.mark.parametrize("alt", ["two-sided", "less", "greater"])
def test_mannwhitney_confere_com_scipy(amostras, alt):
    a, b = amostras
    r = aplicar_mannwhitney(a, b, alternativa=alt)
    ref = stats.mannwhitneyu(
        a, b, alternative=alt, method="asymptotic", use_continuity=True
    )
    assert r["p_valor"] == pytest.approx(ref.pvalue)
    u_ref = stats.mannwhitneyu(a, b, alternative="greater").statistic
    assert r["u"] == pytest.approx(u_ref)
    assert r["alternativa"] == alt


def test_mannwhitney_z_coerente_com_p_com_empates():
    rng = np.random.default_rng(7)
    a = rng.integers(0, 6, 40).astype(float)
    b = rng.integers(1, 8, 50).astype(float)
    r = aplicar_mannwhitney(a, b)
    ref = stats.mannwhitneyu(a, b, method="asymptotic", use_continuity=True)
    assert r["p_valor"] == pytest.approx(ref.pvalue)
    assert r["p_valor"] == pytest.approx(2 * stats.norm.sf(abs(r["estatistica"])))
    assert np.sign(r["estatistica"]) == np.sign(r["u"] - a.size * b.size / 2)


def test_mannwhitney_efeito_sinal_e_limites():
    a = np.arange(10.0, 20.0)
    b = np.arange(0.0, 10.0)
    assert aplicar_mannwhitney(a, b)["tamanho_efeito"] == pytest.approx(1.0)
    assert aplicar_mannwhitney(b, a)["tamanho_efeito"] == pytest.approx(-1.0)
    assert aplicar_mannwhitney(a, b)["estatistica"] > 0
    assert aplicar_mannwhitney(b, a)["estatistica"] < 0


def test_mannwhitney_efeito_em_intervalo_e_formula(amostras):
    a, b = amostras
    r = aplicar_mannwhitney(a, b)
    assert -1 <= r["tamanho_efeito"] <= 1
    assert r["tamanho_efeito"] == pytest.approx(2 * r["u"] / (a.size * b.size) - 1)


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
def test_taxa_de_rejeicao_sob_h0(fn):
    rng = np.random.default_rng(2024)
    ps = np.array(
        [
            fn(rng.lognormal(0, 1, 50), rng.lognormal(0, 1, 50))["p_valor"]
            for _ in range(1000)
        ]
    )
    assert 0.02 < (ps < 0.05).mean() < 0.09
    assert 0.35 < (ps < 0.5).mean() < 0.65


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
def test_sem_mutacao(fn, amostras):
    a, b = amostras
    a0, b0 = a.copy(), b.copy()
    fn(a, b)
    np.testing.assert_array_equal(a, a0)
    np.testing.assert_array_equal(b, b0)


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
def test_aceita_listas_e_chaves(fn):
    r = fn([1.0, 2.0, 3.0, 4.0], [2.0, 5.0, 7.0, 9.0])
    assert {"estatistica", "p_valor", "tamanho_efeito", "alternativa"} <= set(r)
    assert all(isinstance(r[k], float) for k in ("estatistica", "p_valor"))


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
@pytest.mark.parametrize(
    "a,b",
    [
        ([1.0], [1.0, 2.0]),
        ([1.0, 2.0], []),
        ([1.0, np.nan, 3.0], [1.0, 2.0]),
        ([1.0, 2.0], [1.0, np.inf]),
        ([[1.0, 2.0]], [1.0, 2.0]),
    ],
)
def test_entradas_invalidas(fn, a, b):
    with pytest.raises(ValueError):
        fn(a, b)


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
def test_alternativa_invalida(fn, amostras):
    with pytest.raises(ValueError, match="alternativa"):
        fn(*amostras, alternativa="maior")


@pytest.mark.parametrize("fn", [aplicar_welch, aplicar_mannwhitney])
def test_variancia_zero_nos_dois_grupos(fn):
    with pytest.raises(ValueError):
        fn([3.0, 3.0, 3.0], [3.0, 3.0])


def test_sanidade_de_velocidade():
    import time

    rng = np.random.default_rng(0)
    a, b = rng.lognormal(0, 1, 200), rng.lognormal(0, 1, 200)
    t0 = time.perf_counter()
    for _ in range(100):
        aplicar_welch(a, b)
        aplicar_mannwhitney(a, b)
    # ~0,3 ms por par na prática; limite frouxo (50 ms) só pega regressões grosseiras
    assert (time.perf_counter() - t0) / 100 < 0.05

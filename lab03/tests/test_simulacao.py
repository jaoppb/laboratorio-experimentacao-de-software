"""Testes do gerador de dados lognormais."""

import numpy as np
import pytest

from src.simulacao import gerar_dados

PARAMS = dict(n_a=30, n_b=40, mediana_a=10.0, mediana_b=20.0, sigma_a=0.5, sigma_b=1.0)


def gerar(semente=1, **kw):
    return gerar_dados(np.random.default_rng(semente), **{**PARAMS, **kw})


def test_tamanhos_e_dtype():
    a, b = gerar()
    assert a.shape == (30,) and b.shape == (40,)
    assert a.dtype == np.float64 and b.dtype == np.float64


def test_valores_positivos():
    a, b = gerar()
    assert (a > 0).all() and (b > 0).all()


def test_reprodutivel_com_mesma_semente():
    a1, b1 = gerar(7)
    a2, b2 = gerar(7)
    np.testing.assert_array_equal(a1, a2)
    np.testing.assert_array_equal(b1, b2)


def test_sementes_diferentes_dados_diferentes():
    a1, _ = gerar(1)
    a2, _ = gerar(2)
    assert not np.array_equal(a1, a2)


def test_mediana_e_sigma_amostrais():
    a, b = gerar(3, n_a=200_000, n_b=200_000)
    assert np.median(a) == pytest.approx(10.0, rel=0.02)
    assert np.median(b) == pytest.approx(20.0, rel=0.02)
    assert np.std(np.log(a)) == pytest.approx(0.5, rel=0.02)
    assert np.std(np.log(b)) == pytest.approx(1.0, rel=0.02)


def test_usa_apenas_o_rng_recebido():
    outro = np.random.default_rng(99)
    esperado = np.random.default_rng(99).random(5)
    gerar(1)
    np.testing.assert_array_equal(outro.random(5), esperado)


@pytest.mark.parametrize("campo", ["n_a", "n_b"])
@pytest.mark.parametrize("valor", [1, 0, -3, 2.5, 5.0, "10", None, True])
def test_n_invalido(campo, valor):
    with pytest.raises(ValueError, match=campo):
        gerar(**{campo: valor})


@pytest.mark.parametrize("campo", ["mediana_a", "mediana_b", "sigma_a", "sigma_b"])
@pytest.mark.parametrize(
    "valor", [0, -1.0, np.nan, np.inf, -np.inf, "1", None, True]
)
def test_float_invalido(campo, valor):
    with pytest.raises(ValueError, match=campo):
        gerar(**{campo: valor})

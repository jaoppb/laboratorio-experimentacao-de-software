"""Testes de src/pvalores.py (p-valores guardados e taxas recalculadas por α)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.pvalores import chave, carregar, recalcular_taxas, salvar

P = {
    chave("a", 1.0, "welch"): np.array([0.001, 0.02, 0.04, 0.5]),
    chave("a", 1.0, "mannwhitney"): np.array([0.001, 0.009, 0.5, 0.9]),
}
DF = pd.DataFrame(
    [
        {"cenario": "a", "teste": "welch", "n_rep": 4, "alfa": 0.05, "taxa_rejeicao": 0.75},
        {"cenario": "a", "teste": "mannwhitney", "n_rep": 4, "alfa": 0.05, "taxa_rejeicao": 0.5},
    ]
)


def test_ida_e_volta_preserva_os_p_valores(tmp_path):
    salvar(tmp_path / "p.npz", P)
    lido = carregar(tmp_path / "p.npz")
    assert set(lido) == set(P)
    for k in P:
        assert lido[k].dtype == np.float64
        np.testing.assert_array_equal(lido[k], P[k])


def test_recalcula_em_alfa_menor_e_atualiza_coluna_alfa():
    novo = recalcular_taxas(DF, P, 0.01)
    assert list(novo["taxa_rejeicao"]) == [0.25, 0.5]
    assert set(novo["alfa"]) == {0.01}
    assert list(DF["alfa"]) == [0.05, 0.05]  # entrada intacta


def test_alfa_original_reproduz_a_taxa_do_csv():
    novo = recalcular_taxas(DF, P, 0.05)
    assert list(novo["taxa_rejeicao"]) == list(DF["taxa_rejeicao"])


def test_usa_razao_medianas_quando_existe():
    p = {chave("a", 2.0, "welch"): np.array([0.001, 0.5])}
    df = pd.DataFrame(
        [{"cenario": "a", "teste": "welch", "razao_medianas": 2.0, "n_rep": 2,
          "alfa": 0.05, "taxa_rejeicao": 0.5}]
    )
    assert recalcular_taxas(df, p, 0.01)["taxa_rejeicao"].iloc[0] == 0.5


def test_n_rep_diferente_do_csv_e_erro():
    df = DF.assign(n_rep=10)
    with pytest.raises(ValueError, match="n_rep"):
        recalcular_taxas(df, P, 0.01)


def test_linha_sem_p_valores_e_erro():
    with pytest.raises(KeyError):
        recalcular_taxas(DF.assign(cenario="z"), P, 0.01)


@pytest.mark.parametrize("alfa", [0, 1, -0.1, True, "0.01"])
def test_alfa_invalido(alfa):
    with pytest.raises(ValueError, match="alfa"):
        recalcular_taxas(DF, P, alfa)


def test_carregadores_em_alfa_batem_com_csv_em_005(tmp_path):
    from src.graficos.dados_simulacao import (
        carregar_erro_tipo1,
        carregar_erro_tipo1_em,
        carregar_poder,
        carregar_poder_em,
    )

    pd.testing.assert_frame_equal(carregar_erro_tipo1_em(0.05), carregar_erro_tipo1())
    pd.testing.assert_frame_equal(carregar_poder_em(0.05), carregar_poder())
    menor = carregar_poder_em(0.01)
    assert (menor["taxa_rejeicao"] <= carregar_poder()["taxa_rejeicao"]).all()

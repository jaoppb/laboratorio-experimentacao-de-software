"""Testes do orquestrador das simulações Q1, Q2 e Q3."""

from __future__ import annotations

import csv

from scripts.rodar_simulacoes import executar

ARQUIVOS = ("q1_erro_tipo1.csv", "q2_poder.csv", "q3_erro_tipo1.csv", "q3_poder.csv")


def test_executar_grava_os_quatro_csvs(tmp_path):
    tempos = executar(diretorio=tmp_path, n_rep=20, verbose=False)
    assert set(tempos) == {"Q1", "Q2", "Q3"}
    for nome in ARQUIVOS:
        with open(tmp_path / nome, encoding="utf-8") as f:
            assert len(list(csv.DictReader(f))) > 0


def test_executar_e_reprodutivel(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    executar(diretorio=a, n_rep=20, verbose=False)
    executar(diretorio=b, n_rep=20, verbose=False)
    for nome in ARQUIVOS:
        assert (a / nome).read_bytes() == (b / nome).read_bytes()


def test_p_valores_guardados_reproduzem_os_csvs_em_alfa_005(tmp_path):
    import numpy as np
    import pandas as pd

    from src.pvalores import carregar, recalcular_taxas

    executar(diretorio=tmp_path, n_rep=40, verbose=False)
    pares = (
        ("q1_erro_tipo1.csv", "q1_p_valores.npz"),
        ("q2_poder.csv", "q2_p_valores.npz"),
        ("q3_erro_tipo1.csv", "q3_p_valores.npz"),
        ("q3_poder.csv", "q3_p_valores.npz"),
    )
    for nome_csv, nome_npz in pares:
        df = pd.read_csv(tmp_path / nome_csv)
        novo = recalcular_taxas(df, carregar(tmp_path / nome_npz), 0.05)
        np.testing.assert_array_equal(novo["taxa_rejeicao"], df["taxa_rejeicao"])


def test_p_valores_sao_reprodutiveis(tmp_path):
    from src.pvalores import carregar

    a, b = tmp_path / "a", tmp_path / "b"
    executar(diretorio=a, n_rep=20, verbose=False)
    executar(diretorio=b, n_rep=20, verbose=False)
    for nome in ("q1_p_valores.npz", "q2_p_valores.npz", "q3_p_valores.npz"):
        pa, pb = carregar(a / nome), carregar(b / nome)
        assert set(pa) == set(pb)
        assert all((pa[k] == pb[k]).all() for k in pa)

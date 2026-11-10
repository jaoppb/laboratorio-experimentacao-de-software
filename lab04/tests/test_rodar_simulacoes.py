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

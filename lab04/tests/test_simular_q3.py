"""Testes de scripts/simular_q3.py."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "simular_q3.py"
_spec = importlib.util.spec_from_file_location("simular_q3", CAMINHO)
simular_q3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simular_q3)


@pytest.fixture
def arquivo_parametros(tmp_path):
    caminho = tmp_path / "parametros.json"
    dados = {"sem_bot": {"n": 10, "mediana": 3.0, "sigma_log": 1.0}}
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def _ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_gera_os_dois_csv(tmp_path, arquivo_parametros):
    razoes = (1.0, 3.0)
    simular_q3.executar(tmp_path, arquivo_parametros, n_rep=15, razoes=razoes)
    tipo1 = _ler(tmp_path / "q3_erro_tipo1.csv")
    poder = _ler(tmp_path / "q3_poder.csv")
    n_cen = len(simular_q3.CENARIOS)
    assert len(tipo1) == n_cen * 2
    assert len(poder) == n_cen * len(razoes) * 2
    assert {r["cenario"] for r in tipo1} == set(simular_q3.CENARIOS)
    assert all(0.0 <= float(r["taxa_rejeicao"]) <= 1.0 for r in poder)


def test_tipo1_igual_a_razao_um_do_poder(tmp_path, arquivo_parametros):
    simular_q3.executar(tmp_path, arquivo_parametros, n_rep=15, razoes=(1.0, 2.0))
    tipo1 = {(r["cenario"], r["teste"]): r["taxa_rejeicao"] for r in _ler(tmp_path / "q3_erro_tipo1.csv")}
    zero = {
        (r["cenario"], r["teste"]): r["taxa_rejeicao"]
        for r in _ler(tmp_path / "q3_poder.csv")
        if float(r["razao_medianas"]) == 1.0
    }
    assert tipo1 == zero


def test_cada_cenario_muda_um_fator_da_referencia():
    n0, s0, p0 = simular_q3.CENARIOS["referencia"]
    for nome, (n, s, p) in simular_q3.CENARIOS.items():
        if nome != "referencia":
            assert sum([n != n0, s != s0, p != p0]) == 1


def test_contaminacao_aumenta_a_cauda():
    # Com 100% de contaminação todas as observações são multiplicadas: o ponto roda
    # sem erro e devolve taxas válidas.
    taxas = simular_q3.simular_ponto(3.0, 1.0, 10, 1.0, 1.0, 20)
    assert set(taxas) == {"welch", "mannwhitney"}


def test_deterministico_byte_a_byte(tmp_path, arquivo_parametros):
    for nome in ("a", "b"):
        simular_q3.executar(tmp_path / nome, arquivo_parametros, n_rep=10, razoes=(1.0, 3.0))
    for arq in ("q3_erro_tipo1.csv", "q3_poder.csv"):
        assert (tmp_path / "a" / arq).read_bytes() == (tmp_path / "b" / arq).read_bytes()

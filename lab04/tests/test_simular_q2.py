"""Testes de scripts/simular_q2.py."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


simular_q1 = _carregar("simular_q1")
simular_q2 = _carregar("simular_q2")

PARAMETROS = {
    "com_bot": {"n": 12, "mediana": 7.0, "sigma_log": 1.5},
    "sem_bot": {"n": 10, "mediana": 3.0, "sigma_log": 1.0},
}


@pytest.fixture
def arquivo_parametros(tmp_path):
    caminho = tmp_path / "parametros.json"
    caminho.write_text(json.dumps(PARAMETROS), encoding="utf-8")
    return caminho


def _ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_tem_todas_as_combinacoes(tmp_path, arquivo_parametros):
    razoes = (1.0, 2.0, 4.0)
    simular_q2.executar(tmp_path, arquivo_parametros, n_rep=20, razoes=razoes)
    linhas = _ler(tmp_path / "q2_poder.csv")
    assert list(linhas[0]) == simular_q2.COLUNAS
    assert len(linhas) == 2 * len(razoes) * 2
    assert {float(r["razao_medianas"]) for r in linhas} == set(razoes)
    assert all(0.0 <= float(r["taxa_rejeicao"]) <= 1.0 for r in linhas)


def test_minimo_cinco_efeitos_comecando_em_zero():
    assert len(simular_q2.RAZOES) >= 5
    assert simular_q2.RAZOES[0] == 1.0
    assert list(simular_q2.RAZOES) == sorted(simular_q2.RAZOES)


def test_efeito_zero_reproduz_q1(tmp_path, arquivo_parametros):
    simular_q1.executar(tmp_path / "q1", arquivo_parametros, n_rep=50)
    simular_q2.executar(tmp_path / "q2", arquivo_parametros, n_rep=50, razoes=(1.0,))
    q1 = {(r["cenario"], r["teste"]): r["taxa_rejeicao"] for r in _ler(tmp_path / "q1" / "q1_erro_tipo1.csv")}
    q2 = {(r["cenario"], r["teste"]): r["taxa_rejeicao"] for r in _ler(tmp_path / "q2" / "q2_poder.csv")}
    assert q1 == q2


def test_poder_cresce_com_o_efeito(arquivo_parametros):
    pequeno = simular_q2.simular_ponto(PARAMETROS["sem_bot"], 1.0, 300)
    grande = simular_q2.simular_ponto(PARAMETROS["sem_bot"], 20.0, 300)
    assert grande["mannwhitney"] > pequeno["mannwhitney"]


def test_deterministico_byte_a_byte(tmp_path, arquivo_parametros):
    for nome in ("a", "b"):
        simular_q2.executar(tmp_path / nome, arquivo_parametros, n_rep=10, razoes=(1.0, 3.0))
    assert (tmp_path / "a" / "q2_poder.csv").read_bytes() == (tmp_path / "b" / "q2_poder.csv").read_bytes()

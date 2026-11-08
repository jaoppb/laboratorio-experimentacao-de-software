"""Testes de scripts/simular_q1.py."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "simular_q1.py"
_spec = importlib.util.spec_from_file_location("simular_q1", CAMINHO)
simular_q1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simular_q1)

PARAMETROS = {
    "com_bot": {"n": 12, "mediana": 7.0, "sigma_log": 1.5},
    "sem_bot": {"n": 10, "mediana": 3.0, "sigma_log": 1.0},
}


@pytest.fixture
def arquivo_parametros(tmp_path):
    caminho = tmp_path / "parametros.json"
    caminho.write_text(json.dumps(PARAMETROS), encoding="utf-8")
    return caminho


def _executar(tmp_path, arquivo_parametros, n_rep=30, nome="saida"):
    saida = tmp_path / nome
    simular_q1.executar(saida, arquivo_parametros, n_rep)
    return saida / "q1_erro_tipo1.csv"


def test_csv_longo_com_quatro_linhas(tmp_path, arquivo_parametros):
    csv_q1 = _executar(tmp_path, arquivo_parametros)
    with open(csv_q1, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert list(linhas[0]) == ["cenario", "teste", "n_rep", "alfa", "taxa_rejeicao"]
    assert [(r["cenario"], r["teste"]) for r in linhas] == [
        ("com_bot", "welch"),
        ("com_bot", "mannwhitney"),
        ("sem_bot", "welch"),
        ("sem_bot", "mannwhitney"),
    ]
    for r in linhas:
        assert int(r["n_rep"]) == 30
        assert float(r["alfa"]) == 0.05
        assert 0.0 <= float(r["taxa_rejeicao"]) <= 1.0


def test_deterministico_byte_a_byte(tmp_path, arquivo_parametros):
    a = _executar(tmp_path, arquivo_parametros, nome="a").read_bytes()
    b = _executar(tmp_path, arquivo_parametros, nome="b").read_bytes()
    assert a == b


def test_h0_simetrica_usa_mesmos_parametros_nos_dois_grupos(monkeypatch):
    chamadas = []

    def falso(rng, **kw):
        chamadas.append(kw)
        raise RuntimeError("interrompe")

    monkeypatch.setattr(simular_q1, "executar_montecarlo", falso)
    with pytest.raises(RuntimeError):
        simular_q1.simular_cenario(PARAMETROS["com_bot"], 5)
    kw = chamadas[0]
    assert kw["n_a"] == kw["n_b"] == 12
    assert kw["mediana_a"] == kw["mediana_b"] == 7.0
    assert kw["sigma_a"] == kw["sigma_b"] == 1.5


def test_cenarios_usam_parametros_proprios(monkeypatch, tmp_path, arquivo_parametros):
    vistos = []
    original = simular_q1.executar_montecarlo

    def espia(rng, **kw):
        vistos.append(kw["mediana_a"])
        return original(rng, **kw)

    monkeypatch.setattr(simular_q1, "executar_montecarlo", espia)
    _executar(tmp_path, arquivo_parametros, n_rep=3)
    assert vistos == [7.0, 3.0]

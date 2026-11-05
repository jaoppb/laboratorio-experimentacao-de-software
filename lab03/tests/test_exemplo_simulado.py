"""Testes do script de exemplo da simulação (reprodutibilidade e contrato)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "exemplo_simulado.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("exemplo_simulado", CAMINHO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_duas_execucoes_geram_arquivos_identicos(tmp_path):
    modulo = _carregar()
    modulo.executar(tmp_path / "um")
    modulo.executar(tmp_path / "dois")
    for nome in ("exemplo.csv", "exemplo_resultado.json"):
        assert (tmp_path / "um" / nome).read_bytes() == (tmp_path / "dois" / nome).read_bytes()


def test_formato_do_csv_e_chaves_do_json(tmp_path):
    modulo = _carregar()
    modulo.executar(tmp_path)
    with open(tmp_path / "exemplo.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert list(linhas[0]) == ["grupo", "valor"]
    assert [linha["grupo"] for linha in linhas] == ["A"] * modulo.N_A + ["B"] * modulo.N_B
    res = json.loads((tmp_path / "exemplo_resultado.json").read_text(encoding="utf-8"))
    assert list(res)[:4] == ["semente", "parametros", "welch", "mannwhitney"]
    assert res["semente"] == 42
    assert res["parametros"]["alpha"] == 0.05
    assert {"estatistica", "p_valor", "tamanho_efeito", "alternativa", "gl"} <= set(res["welch"])
    assert {"estatistica", "p_valor", "tamanho_efeito", "alternativa", "u"} <= set(res["mannwhitney"])


def test_arquivos_commitados_batem_com_o_script(tmp_path):
    modulo = _carregar()
    modulo.executar(tmp_path)
    for nome in ("exemplo.csv", "exemplo_resultado.json"):
        assert (tmp_path / nome).read_bytes() == (modulo.DIRETORIO_SAIDA / nome).read_bytes()

"""Testes de scripts/testar_dados_reais.py."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "testar_dados_reais.py"
_spec = importlib.util.spec_from_file_location("testar_dados_reais", CAMINHO)
testar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(testar)


def _csv(tmp_path, com, sem):
    caminho = tmp_path / "pr.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["repo", "pr_number", "grupo", "tempo_merge_horas", "url"])
        for i, v in enumerate(com):
            w.writerow(["r", i, "com_bot", v, "u"])
        for i, v in enumerate(sem):
            w.writerow(["r", 100 + i, "sem_bot", v, "u"])
    return caminho


def test_campos_do_resultado(tmp_path):
    entrada = _csv(tmp_path, [1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7])
    saida = tmp_path / "r.json"
    res = testar.executar(entrada, saida)
    assert json.loads(saida.read_text(encoding="utf-8")) == res
    assert res["n"] == {"com_bot": 6, "sem_bot": 6}
    for t in ("welch", "mannwhitney"):
        assert {"estatistica", "p_valor", "tamanho_efeito", "conclusao"} <= set(res[t])


def test_diferenca_clara_rejeita_h0(tmp_path):
    entrada = _csv(tmp_path, list(range(100, 112)), list(range(1, 13)))
    res = testar.executar(entrada, tmp_path / "r.json")
    assert res["welch"]["p_valor"] < 0.05
    assert res["mannwhitney"]["p_valor"] < 0.05
    assert res["concordam"] is True
    assert res["mannwhitney"]["tamanho_efeito"] > 0
    assert res["welch"]["conclusao"].startswith("rejeita H0")


def test_grupos_iguais_nao_rejeitam(tmp_path):
    v = [1.0, 2.5, 3.0, 4.2, 5.1, 6.3, 7.7, 9.0]
    res = testar.executar(_csv(tmp_path, v, v[::-1]), tmp_path / "r.json")
    assert res["welch"]["conclusao"].startswith("não rejeita")
    assert res["mannwhitney"]["conclusao"].startswith("não rejeita")


@pytest.mark.parametrize(
    "valor,esperado",
    [(0.05, "desprezível"), (0.3, "pequeno"), (-0.6, "médio"), (0.9, "grande")],
)
def test_magnitude(valor, esperado):
    assert testar.magnitude(valor, (0.2, 0.5, 0.8)) == esperado


def test_dados_reais_do_repositorio():
    res = testar.executar(arquivo_saida=Path("/dev/null"))
    assert res["n"] == {"com_bot": 30, "sem_bot": 30}

"""Testes da comparação agente × humana do `tipo_projeto` (Issue #69, etapa 2).

Fixtures sintéticas com métricas calculadas à mão; nenhum teste depende dos rótulos
humanos reais.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from analises.comparar_tipo_agentes_humano import (
    ReferenciaHumanaInvalidaError,
    analisar,
    carregar_repos_invalidos,
    carregar_tipo_humano,
    comparar,
    formatar_markdown,
    main,
)

LIB, APP, CLI, OUT = "biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro"


def test_comparar_metricas_a_mao():
    repos = ["r1", "r2", "r3", "r4"]
    humano = {"r1": LIB, "r2": LIB, "r3": APP, "r4": APP}
    agente = {"r1": LIB, "r2": APP, "r3": APP, "r4": APP}
    m = comparar("t", agente, humano, repos, {"r2": "porque sim"})
    assert m.n == 4
    assert m.concordancia == pytest.approx(0.75)
    # po = 0.75; pe = (2/4*1/4) + (2/4*3/4) = 0.5 -> kappa = 0.5
    assert m.kappa == pytest.approx(0.5)
    assert m.matriz.loc[LIB, LIB] == 1 and m.matriz.loc[LIB, APP] == 1
    assert m.matriz.loc[APP, APP] == 2 and m.matriz.loc[APP, LIB] == 0
    assert m.por_classe.loc[LIB, "precisao"] == pytest.approx(1.0)
    assert m.por_classe.loc[LIB, "recall"] == pytest.approx(0.5)
    assert m.por_classe.loc[APP, "precisao"] == pytest.approx(2 / 3)
    assert m.por_classe.loc[APP, "recall"] == pytest.approx(1.0)
    assert m.por_classe.loc[CLI, "suporte_humano"] == 0
    assert list(m.divergencias["full_name"]) == ["r2"]
    assert m.divergencias.iloc[0]["justificativa_agente"] == "porque sim"


def test_kappa_indefinido_com_uma_classe():
    m = comparar("t", {"r1": APP, "r2": APP}, {"r1": APP, "r2": APP}, ["r1", "r2"])
    assert m.concordancia == 1.0
    assert math.isnan(m.kappa)
    assert m.divergencias.empty


def test_subconjunto_vazio():
    m = comparar("t", {}, {}, [])
    assert m.n == 0 and math.isnan(m.concordancia) and math.isnan(m.kappa)


def test_rotulo_faltante():
    with pytest.raises(ReferenciaHumanaInvalidaError):
        comparar("t", {"r1": APP}, {}, ["r1"])


def _csv_humano(tmp_path, linhas):
    caminho = tmp_path / "rotulos.csv"
    pd.DataFrame(linhas, columns=["repo_name", "tipo_projeto"]).to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho


def test_carregar_tipo_humano_com_bom(tmp_path):
    caminho = _csv_humano(tmp_path, [("a/x", APP)] * 5 + [("b/y", CLI)] * 5)
    assert carregar_tipo_humano(caminho) == {"a/x": APP, "b/y": CLI}


def test_carregar_tipo_humano_rejeita_inconsistencia_e_vazio(tmp_path):
    with pytest.raises(ReferenciaHumanaInvalidaError, match="divergentes"):
        carregar_tipo_humano(_csv_humano(tmp_path, [("a/x", APP), ("a/x", CLI)]))
    with pytest.raises(ReferenciaHumanaInvalidaError, match="inválido/vazio"):
        carregar_tipo_humano(_csv_humano(tmp_path, [("a/x", "")]))


def _montar(tmp_path):
    nomes = ["a/x", "b/y", "c/z", "d/w"]
    agentes = pd.DataFrame(
        {
            "full_name": nomes,
            "tipo_projeto": [LIB, APP, CLI, OUT],
            "tipo_projeto_origem": ["agente"] * 4,
            "confianca": ["alta"] * 4,
            "justificativa": ["j"] * 4,
            "fontes": ["f"] * 4,
            "rotulador": ["r"] * 4,
            "data_utc": ["2026-10-21T00:00:00Z"] * 4,
            "versao_rubrica": ["v"] * 4,
        }
    )
    (tmp_path / "agentes.csv").write_text(agentes.to_csv(index=False), encoding="utf-8")
    pd.DataFrame({"full_name": nomes}).to_csv(tmp_path / "repos.csv", index=False)
    # humana rotulou 3 dos 4 repositórios; c/z e d/w têm linhas nulas
    humano = [("a/x", LIB)] * 5 + [("b/y", CLI)] * 5 + [("c/z", CLI)] * 5
    _csv = _csv_humano(tmp_path, humano)
    pd.DataFrame({"repo_idx": [3, 3], "release_idx": [1, 2], "repo_name": ["c/z", "c/z"]}).to_csv(
        tmp_path / "invalidas.csv", index=False
    )
    return tmp_path / "agentes.csv", _csv, tmp_path / "invalidas.csv", tmp_path / "repos.csv"


def test_analisar_separa_validos_e_nulos(tmp_path):
    ag, hu, inv, repos = _montar(tmp_path)
    assert carregar_repos_invalidos(inv) == {"c/z"}
    validos, nulos, todos = analisar(ag, hu, inv, repos)
    assert (validos.n, nulos.n, todos.n) == (2, 1, 3)
    assert validos.concordancia == pytest.approx(0.5)  # a/x bate; b/y não
    assert nulos.concordancia == 1.0
    assert todos.concordancia == pytest.approx(2 / 3)
    assert list(todos.divergencias["full_name"]) == ["b/y"]


def test_analisar_rejeita_repo_humano_fora_do_conjunto(tmp_path):
    ag, hu, inv, repos = _montar(tmp_path)
    pd.DataFrame({"full_name": ["a/x", "b/y"]}).to_csv(repos, index=False)
    ag.write_text(pd.read_csv(ag).iloc[:2].to_csv(index=False), encoding="utf-8")
    with pytest.raises(ReferenciaHumanaInvalidaError, match="fora do conjunto"):
        analisar(ag, hu, inv, repos)


def test_markdown_e_cli(tmp_path, capsys):
    ag, hu, inv, repos = _montar(tmp_path)
    texto = formatar_markdown(analisar(ag, hu, inv, repos))
    assert "Kappa de Cohen" in texto and "Matriz de confusão" in texto
    saida = tmp_path / "div.csv"
    rc = main(
        ["--agentes", str(ag), "--humano", str(hu), "--invalidas", str(inv), "--repositorios", str(repos),
         "--saida-divergencias", str(saida)]
    )
    assert rc == 0
    assert pd.read_csv(saida)["full_name"].tolist() == ["b/y"]
    assert "todos os 60" in capsys.readouterr().out


def test_cli_recusa_gravar_em_validacao(tmp_path):
    ag, hu, inv, repos = _montar(tmp_path)
    destino = tmp_path / "validacao"
    destino.mkdir()
    rc = main(
        ["--agentes", str(ag), "--humano", str(hu), "--invalidas", str(inv), "--repositorios", str(repos),
         "--saida-divergencias", str(destino / "x.csv")]
    )
    assert rc == 1 and not (destino / "x.csv").exists()


def test_cli_erro_retorna_1(tmp_path, capsys):
    assert main(["--agentes", str(tmp_path / "nao_existe.csv")]) == 1

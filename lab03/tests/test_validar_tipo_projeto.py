"""Testes do validador de `tipo_projeto_agentes.csv` (Issue #69).

Usam fixtures sintéticas; o último teste confere o arquivo congelado do repositório
contra `dados/repositorios.csv` (sem ler rótulos humanos nem colunas de desfecho).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analises.validar_tipo_projeto import (
    COLUNAS,
    TipoProjetoInvalidoError,
    listar_problemas,
    main,
    validar,
)

LAB03 = Path(__file__).resolve().parent.parent
NOMES = ["a/x", "b/y", "c/z"]


def _df(**alteracoes) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "full_name": NOMES,
            "tipo_projeto": ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI"],
            "tipo_projeto_origem": ["agente"] * 3,
            "confianca": ["alta", "media", "baixa"],
            "justificativa": ["j1", "j2", "j3"],
            "fontes": ["f"] * 3,
            "rotulador": ["r"] * 3,
            "data_utc": ["2026-10-21T00:00:00Z"] * 3,
            "versao_rubrica": ["rubrica-tipo-v1"] * 3,
        }
    )
    for coluna, valores in alteracoes.items():
        df[coluna] = valores
    return df


def _escrever(tmp_path: Path, df: pd.DataFrame, nomes=NOMES) -> tuple[Path, Path]:
    arquivo = tmp_path / "tipo.csv"
    repos = tmp_path / "repos.csv"
    df.to_csv(arquivo, index=False)
    pd.DataFrame({"full_name": nomes, "stars": [1] * len(nomes)}).to_csv(repos, index=False)
    return arquivo, repos


def test_valido_nao_tem_problemas():
    assert listar_problemas(_df(), NOMES) == []


def test_colunas_ausentes():
    df = _df().drop(columns=["tipo_projeto_origem"])
    assert "colunas ausentes: tipo_projeto_origem" in listar_problemas(df, NOMES)[0]


def test_coluna_extra_e_reportada():
    df = _df()
    df["deployment_tier"] = "Elite"
    assert any("inesperadas" in p for p in listar_problemas(df, NOMES))


def test_contagem_e_ausentes():
    problemas = listar_problemas(_df().iloc[:2], NOMES)
    assert any("2 linhas; esperado 3" in p for p in problemas)
    assert any("ausentes: c/z" in p for p in problemas)


def test_duplicado_e_fora_do_conjunto():
    df = _df(full_name=["a/x", "a/x", "q/w"])
    problemas = listar_problemas(df, NOMES)
    assert any("duplicado: a/x" in p for p in problemas)
    assert any("fora de repositorios.csv: q/w" in p for p in problemas)


def test_ordem_diferente():
    df = _df(full_name=["b/y", "a/x", "c/z"])
    assert any("ordem diferente" in p for p in listar_problemas(df, NOMES))


def test_tipo_invalido():
    df = _df(tipo_projeto=["biblioteca/framework", "app", "ferramenta CLI"])
    assert any("fora dos permitidos: app" in p for p in listar_problemas(df, NOMES))


def test_origem_deve_ser_agente():
    df = _df(tipo_projeto_origem=["agente", "humano", "agente"])
    assert any("tipo_projeto_origem" in p for p in listar_problemas(df, NOMES))


def test_campo_vazio():
    df = _df(justificativa=["j1", "  ", "j3"])
    assert any("'justificativa' vazio em: b/y" in p for p in listar_problemas(df, NOMES))


def test_confianca_e_versao():
    df = _df(confianca=["alta", "muito", "baixa"], versao_rubrica=["v1", "v1", "v2"])
    problemas = listar_problemas(df, NOMES)
    assert any("confianca" in p for p in problemas)
    assert any("mais de uma versao_rubrica" in p for p in problemas)


def test_validar_e_cli(tmp_path, capsys):
    arquivo, repos = _escrever(tmp_path, _df())
    assert len(validar(arquivo, repos)) == 3
    assert main(["--arquivo", str(arquivo), "--repositorios", str(repos)]) == 0
    assert "OK: 3 linhas" in capsys.readouterr().out


def test_validar_levanta_e_cli_retorna_1(tmp_path, capsys):
    arquivo, repos = _escrever(tmp_path, _df(tipo_projeto=["x", "x", "x"]))
    with pytest.raises(TipoProjetoInvalidoError):
        validar(arquivo, repos)
    assert main(["--arquivo", str(arquivo), "--repositorios", str(repos)]) == 1
    assert "fora dos permitidos" in capsys.readouterr().err


def test_arquivo_congelado_do_repositorio_e_valido():
    df = validar(LAB03 / "dados/tipo_projeto_agentes.csv", LAB03 / "dados/repositorios.csv")
    assert len(df) == 330
    assert list(df.columns) == list(COLUNAS)
    assert set(df["tipo_projeto_origem"]) == {"agente"}


def test_harmonizacao_reproduz_o_arquivo_congelado():
    """bruto + log de harmonização == arquivo congelado (rastreabilidade das 9 mudanças)."""
    kw = dict(dtype=str, keep_default_na=False, encoding="utf-8")
    bruto = pd.read_csv(LAB03 / "dados/tipo_projeto_agentes_bruto.csv", **kw).set_index("full_name")
    log = pd.read_csv(LAB03 / "dados/tipo_projeto_agentes_harmonizacao.csv", **kw).set_index("full_name")
    final = pd.read_csv(LAB03 / "dados/tipo_projeto_agentes.csv", **kw).set_index("full_name")
    assert list(bruto.index) == list(final.index)
    assert (bruto.loc[log.index, "tipo_projeto"] == log["tipo_antigo"]).all()
    esperado = bruto["tipo_projeto"].copy()
    esperado.loc[log.index] = log["tipo_novo"]
    assert (esperado == final["tipo_projeto"]).all()
    nao_alterados = final.index.difference(log.index)
    assert (bruto.loc[nao_alterados, "justificativa"] == final.loc[nao_alterados, "justificativa"]).all()

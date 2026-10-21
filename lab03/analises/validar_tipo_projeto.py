"""Validador do `tipo_projeto` rotulado por agentes (Issue #69).

Confere `dados/tipo_projeto_agentes.csv` contra `dados/repositorios.csv`:

* exatamente as mesmas linhas, **no mesmo conjunto e na mesma ordem** (330);
* sem duplicatas e sem campos vazios;
* `tipo_projeto` ∈ {biblioteca/framework, aplicação/serviço, ferramenta CLI, outro};
* `tipo_projeto_origem` presente e igual a `agente` em todas as linhas;
* `confianca` ∈ {alta, media, baixa} e `versao_rubrica` única.

O módulo só lê arquivos. Não lê rótulos humanos nem colunas de desfecho (DORA).

Execução (a partir de `lab03/`):
    uv run python -m analises.validar_tipo_projeto
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

DEFAULT_ARQUIVO = "dados/tipo_projeto_agentes.csv"
DEFAULT_REPOSITORIOS = "dados/repositorios.csv"

TIPOS_PERMITIDOS = ("biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro")
ORIGEM_AGENTE = "agente"
CONFIANCAS_PERMITIDAS = ("alta", "media", "baixa")
COLUNAS = (
    "full_name",
    "tipo_projeto",
    "tipo_projeto_origem",
    "confianca",
    "justificativa",
    "fontes",
    "rotulador",
    "data_utc",
    "versao_rubrica",
)


class TipoProjetoInvalidoError(ValueError):
    """O arquivo de tipo do projeto viola o contrato (lista todos os problemas)."""

    def __init__(self, problemas: list[str]):
        self.problemas = problemas
        super().__init__("tipo_projeto_agentes.csv inválido:\n- " + "\n- ".join(problemas))


def _ler(path: Path | str, colunas: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
        usecols=colunas,
    )


def listar_problemas(df: pd.DataFrame, full_names_esperados: list[str]) -> list[str]:
    """Retorna a lista de violações (vazia = válido)."""
    problemas: list[str] = []
    faltantes = [c for c in COLUNAS if c not in df.columns]
    if faltantes:
        return [f"colunas ausentes: {', '.join(faltantes)}"]
    extras = [c for c in df.columns if c not in COLUNAS]
    if extras:
        problemas.append(f"colunas inesperadas: {', '.join(extras)}")

    if len(df) != len(full_names_esperados):
        problemas.append(f"{len(df)} linhas; esperado {len(full_names_esperados)}")
    duplicados = sorted(set(df["full_name"][df["full_name"].duplicated()]))
    if duplicados:
        problemas.append(f"full_name duplicado: {', '.join(duplicados)}")

    obtidos = list(df["full_name"])
    ausentes = sorted(set(full_names_esperados) - set(obtidos))
    sobrando = sorted(set(obtidos) - set(full_names_esperados))
    if ausentes:
        problemas.append(f"repositórios ausentes: {', '.join(ausentes)}")
    if sobrando:
        problemas.append(f"repositórios fora de repositorios.csv: {', '.join(sobrando)}")
    if not ausentes and not sobrando and not duplicados and obtidos != full_names_esperados:
        problemas.append("mesmo conjunto de repositórios, mas ordem diferente de repositorios.csv")

    for coluna in COLUNAS:
        vazios = df.loc[df[coluna].str.strip() == "", "full_name"].tolist()
        if vazios:
            problemas.append(f"campo '{coluna}' vazio em: {', '.join(vazios[:5])}")

    invalidos = sorted(set(df["tipo_projeto"]) - set(TIPOS_PERMITIDOS) - {""})
    if invalidos:
        problemas.append(f"tipo_projeto fora dos permitidos: {', '.join(invalidos)}")
    origens = sorted(set(df["tipo_projeto_origem"]) - {""})
    if origens != [ORIGEM_AGENTE] and origens:
        problemas.append(f"tipo_projeto_origem deve ser '{ORIGEM_AGENTE}' em todas as linhas; achou {origens}")
    conf = sorted(set(df["confianca"]) - set(CONFIANCAS_PERMITIDAS) - {""})
    if conf:
        problemas.append(f"confianca fora de {CONFIANCAS_PERMITIDAS}: {', '.join(conf)}")
    versoes = sorted(set(df["versao_rubrica"]) - {""})
    if len(versoes) > 1:
        problemas.append(f"mais de uma versao_rubrica: {', '.join(versoes)}")
    return problemas


def validar(
    arquivo: Path | str = DEFAULT_ARQUIVO,
    repositorios: Path | str = DEFAULT_REPOSITORIOS,
) -> pd.DataFrame:
    """Valida o arquivo e o devolve; levanta `TipoProjetoInvalidoError` se houver violações."""
    df = _ler(arquivo)
    esperados = _ler(repositorios, ["full_name"])["full_name"].tolist()
    problemas = listar_problemas(df, esperados)
    if problemas:
        raise TipoProjetoInvalidoError(problemas)
    return df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--arquivo", default=DEFAULT_ARQUIVO)
    parser.add_argument("--repositorios", default=DEFAULT_REPOSITORIOS)
    args = parser.parse_args(argv)
    try:
        df = validar(args.arquivo, args.repositorios)
    except (TipoProjetoInvalidoError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    contagem = df["tipo_projeto"].value_counts()
    print(f"OK: {len(df)} linhas, origem=agente, versão {df['versao_rubrica'].iloc[0]}")
    for tipo, n in contagem.items():
        print(f"  {tipo}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

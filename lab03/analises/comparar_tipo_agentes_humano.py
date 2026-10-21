"""Compara o `tipo_projeto` dos agentes com a referência humana (Issue #69, etapa 2).

ATENÇÃO À ORDEM: este módulo só deve ser usado **depois** do congelamento de
`dados/tipo_projeto_agentes.csv`. Ele é somente leitura: nunca altera os rótulos dos
agentes por causa da comparação.

Referência humana: `validacao/rotulos_marcela.csv` (uma só avaliadora; o kappa entre
humanos ainda não existe). `tipo_projeto` é por repositório e se repete nas 5 linhas.
Para 30 dos 60 repositórios, os rótulos foram dados sobre linhas que a PR #82 declarou
nulas (`validacao/marcela_linhas_invalidas.csv`); por isso o resultado é reportado em
separado para (a) os repositórios com linhas válidas, (b) os demais (referência mais
fraca) e (c) os 60 juntos.

Métricas: concordância simples, kappa de Cohen (agente × humana), matriz de confusão
(linhas = humana, colunas = agente) e precisão/recall/F1 por classe do agente contra a
referência humana (`sklearn.metrics`).

Execução (a partir de `lab03/`):
    uv run python -m analises.comparar_tipo_agentes_humano
    uv run python -m analises.comparar_tipo_agentes_humano --saida-divergencias /tmp/div.csv
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support

from analises.validar_tipo_projeto import TIPOS_PERMITIDOS, validar

DEFAULT_AGENTES = "dados/tipo_projeto_agentes.csv"
DEFAULT_HUMANO = "validacao/rotulos_marcela.csv"
DEFAULT_INVALIDAS = "validacao/marcela_linhas_invalidas.csv"
DEFAULT_REPOSITORIOS = "dados/repositorios.csv"


class ReferenciaHumanaInvalidaError(ValueError):
    """Rótulo humano ausente/inconsistente para algum repositório."""


@dataclass
class Metricas:
    """Resultado da comparação para um subconjunto de repositórios."""

    nome: str
    n: int
    concordancia: float
    kappa: float
    matriz: pd.DataFrame  # linhas = humana, colunas = agente
    por_classe: pd.DataFrame  # índice = classe; colunas precisao, recall, f1, suporte_humano
    divergencias: pd.DataFrame = field(default_factory=pd.DataFrame)


def carregar_tipo_humano(path: Path | str) -> dict[str, str]:
    """Lê o `tipo_projeto` humano por repositório (as 5 linhas devem concordar entre si)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for coluna in ("repo_name", "tipo_projeto"):
        if coluna not in df.columns:
            raise ReferenciaHumanaInvalidaError(f"coluna ausente em {path}: {coluna}")
    df["tipo_projeto"] = df["tipo_projeto"].str.strip()
    resultado: dict[str, str] = {}
    problemas: list[str] = []
    for repo, grupo in df.groupby("repo_name", sort=False):
        valores = set(grupo["tipo_projeto"])
        if len(valores) != 1:
            problemas.append(f"{repo}: valores divergentes entre as linhas {sorted(valores)}")
            continue
        (valor,) = valores
        if valor not in TIPOS_PERMITIDOS:
            problemas.append(f"{repo}: tipo_projeto humano inválido/vazio ({valor!r})")
            continue
        resultado[str(repo)] = valor
    if problemas:
        raise ReferenciaHumanaInvalidaError("; ".join(problemas))
    return resultado


def carregar_repos_invalidos(path: Path | str) -> set[str]:
    """Repositórios cujas linhas constam da lista de linhas inválidas."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return set(df["repo_name"])


def comparar(
    nome: str,
    agente: dict[str, str],
    humano: dict[str, str],
    repositorios: list[str],
    justificativas: dict[str, str] | None = None,
) -> Metricas:
    """Compara agente × humana nos `repositorios` dados (todos precisam ter ambos os rótulos)."""
    faltam = [r for r in repositorios if r not in agente or r not in humano]
    if faltam:
        raise ReferenciaHumanaInvalidaError(f"sem rótulo de agente ou humano: {', '.join(faltam)}")
    classes = list(TIPOS_PERMITIDOS)
    y_h = [humano[r] for r in repositorios]
    y_a = [agente[r] for r in repositorios]
    n = len(repositorios)
    concordancia = sum(h == a for h, a in zip(y_h, y_a)) / n if n else float("nan")
    # Com uma só classe observada nos dois lados o kappa é indefinido (0/0).
    if n and len(set(y_h) | set(y_a)) > 1:
        kappa = float(cohen_kappa_score(y_h, y_a, labels=classes))
    else:
        kappa = float("nan")
    matriz = pd.crosstab(
        pd.Categorical(y_h, categories=classes),
        pd.Categorical(y_a, categories=classes),
        dropna=False,
    )
    matriz.index.name = "humana"
    matriz.columns.name = "agente"
    if n:
        p, r, f, s = precision_recall_fscore_support(
            y_h, y_a, labels=classes, zero_division=0
        )
    else:
        p = r = f = [float("nan")] * len(classes)
        s = [0] * len(classes)
    por_classe = pd.DataFrame(
        {
            "precisao": p,
            "recall": r,
            "f1": f,
            "suporte_humano": s,
            "predito_agente": [y_a.count(c) for c in classes],
        },
        index=classes,
    )
    just = justificativas or {}
    div = pd.DataFrame(
        [
            {"full_name": r, "agente": agente[r], "humana": humano[r], "justificativa_agente": just.get(r, "")}
            for r in repositorios
            if agente[r] != humano[r]
        ],
        columns=["full_name", "agente", "humana", "justificativa_agente"],
    )
    return Metricas(nome, n, concordancia, kappa, matriz, por_classe, div)


def analisar(
    agentes_csv: Path | str = DEFAULT_AGENTES,
    humano_csv: Path | str = DEFAULT_HUMANO,
    invalidas_csv: Path | str = DEFAULT_INVALIDAS,
    repositorios_csv: Path | str = DEFAULT_REPOSITORIOS,
) -> list[Metricas]:
    """Retorna as métricas de (a) linhas válidas, (b) linhas nulas na PR #82 e (c) todos os 60."""
    df = validar(agentes_csv, repositorios_csv)
    agente = dict(zip(df["full_name"], df["tipo_projeto"]))
    just = dict(zip(df["full_name"], df["justificativa"]))
    humano = carregar_tipo_humano(humano_csv)
    invalidos = carregar_repos_invalidos(invalidas_csv)
    todos = [r for r in df["full_name"] if r in humano]  # ordem de repositorios.csv
    if len(todos) != len(humano):
        fora = sorted(set(humano) - set(todos))
        raise ReferenciaHumanaInvalidaError(f"repositórios humanos fora do conjunto de 330: {', '.join(fora)}")
    validos = [r for r in todos if r not in invalidos]
    nulos = [r for r in todos if r in invalidos]
    return [
        comparar("(a) 30 repositórios com linhas válidas", agente, humano, validos, just),
        comparar("(b) 30 repositórios com linhas nulas na PR #82 (referência mais fraca)", agente, humano, nulos, just),
        comparar("(c) todos os 60", agente, humano, todos, just),
    ]


def _pct(x: float) -> str:
    return "n/d" if math.isnan(x) else f"{100 * x:.1f}%"


def _num(x: float) -> str:
    return "n/d" if math.isnan(x) else f"{x:.2f}"


def formatar_markdown(resultados: list[Metricas]) -> str:
    """Tabelas em Markdown (pt-BR) prontas para colar na documentação."""
    linhas = [
        "| Subconjunto | n | Concordância | Kappa de Cohen |",
        "|---|---:|---:|---:|",
    ]
    for m in resultados:
        linhas.append(f"| {m.nome} | {m.n} | {_pct(m.concordancia)} | {_num(m.kappa)} |")
    for m in resultados:
        linhas += ["", f"### {m.nome}", "", "Matriz de confusão (linhas = humana, colunas = agente):", ""]
        cols = list(m.matriz.columns)
        linhas.append("| humana \\ agente | " + " | ".join(cols) + " |")
        linhas.append("|---|" + "---:|" * len(cols))
        for idx, row in m.matriz.iterrows():
            linhas.append(f"| {idx} | " + " | ".join(str(int(v)) for v in row) + " |")
        linhas += ["", "Precisão/recall do agente contra a referência humana:", ""]
        linhas.append("| Classe | Precisão | Recall | F1 | n humana | n agente |")
        linhas.append("|---|---:|---:|---:|---:|---:|")
        for classe, row in m.por_classe.iterrows():
            linhas.append(
                f"| {classe} | {_num(row.precisao)} | {_num(row.recall)} | {_num(row.f1)} "
                f"| {int(row.suporte_humano)} | {int(row.predito_agente)} |"
            )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--agentes", default=DEFAULT_AGENTES)
    parser.add_argument("--humano", default=DEFAULT_HUMANO)
    parser.add_argument("--invalidas", default=DEFAULT_INVALIDAS)
    parser.add_argument("--repositorios", default=DEFAULT_REPOSITORIOS)
    parser.add_argument("--saida-divergencias", help="CSV com as divergências dos 60 (não resolve nenhuma)")
    args = parser.parse_args(argv)
    try:
        resultados = analisar(args.agentes, args.humano, args.invalidas, args.repositorios)
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(formatar_markdown(resultados))
    if args.saida_divergencias:
        destino = Path(args.saida_divergencias)
        if "validacao" in destino.parts:
            print("recusando gravar em validacao/", file=sys.stderr)
            return 1
        resultados[-1].divergencias.to_csv(destino, index=False, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Auditoria dos rótulos de avaliadores IA commitados em `validacao/` (Issues #57, #61, #64, #65).

Este módulo NÃO calcula o kappa de Fleiss, o consenso nem qualquer resultado da heurística.
Ele só (1) prova que as 150 linhas humanas de `rotulos_marcela.csv` ficaram byte a byte
iguais às da versão commitada por Marcela e que as 150 linhas de IA são exatamente as da
lista histórica `historico/marcela_linhas_invalidas.csv`; (2) mede a concordância bruta entre
duas execuções de IA do mesmo slot (confiabilidade entre execuções); e (3) mede a concordância
bruta de execuções de IA com as 150 linhas humanas de Marcela (aviso de validade).

Execução (a partir de `lab03/`):
    git show origin/main:lab03/validacao/rotulos_marcela.csv > /tmp/rotulos_marcela_main.csv
    uv run python -m analises.auditoria_rotulos_ia humanas --anterior /tmp/rotulos_marcela_main.csv
    uv run python -m analises.auditoria_rotulos_ia confiabilidade
    uv run python -m analises.auditoria_rotulos_ia ia-vs-humano
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from analises.concordancia import DIMENSOES, carregar_csv

DEFAULT_VALIDACAO_DIR = "validacao"
DEFAULT_INVALIDAS = "validacao/historico/marcela_linhas_invalidas.csv"
EXTRA_GABRIEL = "extra/rotulos_gabriel_execucao2_ia.csv"
FIM_DE_LINHA = b"\r\n"  # as planilhas de rotulação usam CRLF
CHAVE = ["repo_idx", "release_idx"]


def ler_linhas_brutas(caminho: Path | str) -> list[bytes]:
    """Linhas do arquivo como bytes (sem o CRLF final), na ordem; a primeira é o cabeçalho."""
    conteudo = Path(caminho).read_bytes()
    if not conteudo.endswith(FIM_DE_LINHA):
        raise ValueError(f"{caminho}: não termina em CRLF")
    return conteudo[: -len(FIM_DE_LINHA)].split(FIM_DE_LINHA)


def _chave_da_linha(linha: bytes) -> tuple[str, str]:
    """(repo_idx, release_idx) de uma linha bruta (colunas 0 e 5 do formato dos rótulos)."""
    campos = next(csv.reader([linha.decode("utf-8-sig")]))
    return campos[0], campos[5]


def hash_linhas(linhas: Sequence[bytes]) -> str:
    """SHA-256 das linhas unidas por CRLF (cada uma terminada em CRLF)."""
    return hashlib.sha256(b"".join(linha + FIM_DE_LINHA for linha in linhas)).hexdigest()


@dataclass(frozen=True)
class ResultadoHumanas:
    n_humanas: int
    n_ia: int
    humanas_identicas: bool
    chaves_ia_igual_lista: bool
    cabecalho_igual: bool
    mesmas_chaves_e_ordem: bool
    hash_humanas: str

    @property
    def ok(self) -> bool:
        return (
            self.humanas_identicas
            and self.chaves_ia_igual_lista
            and self.cabecalho_igual
            and self.mesmas_chaves_e_ordem
        )


def verificar_linhas_humanas(
    anterior: Path | str, atual: Path | str, invalidas: Path | str
) -> ResultadoHumanas:
    """Compara `rotulos_marcela.csv` anterior (main) com o atual, linha a linha, em bytes.

    As linhas cuja chave NÃO está em `invalidas` (as humanas) devem ser idênticas; as linhas
    cuja chave está em `invalidas` são as de IA (e, por construção, devem diferir das antigas).
    """
    antes, depois = ler_linhas_brutas(anterior), ler_linhas_brutas(atual)
    lista = carregar_csv(invalidas)
    chaves_invalidas = set(zip(lista["repo_idx"], lista["release_idx"]))
    chaves_antes = [_chave_da_linha(linha) for linha in antes[1:]]
    chaves_depois = [_chave_da_linha(linha) for linha in depois[1:]]
    mesmas = chaves_antes == chaves_depois
    humanas = [i for i, k in enumerate(chaves_depois) if k not in chaves_invalidas]
    ia = [i for i, k in enumerate(chaves_depois) if k in chaves_invalidas]
    identicas = mesmas and all(antes[1:][i] == depois[1:][i] for i in humanas)
    return ResultadoHumanas(
        n_humanas=len(humanas),
        n_ia=len(ia),
        humanas_identicas=identicas,
        chaves_ia_igual_lista={chaves_depois[i] for i in ia} == chaves_invalidas and len(ia) == len(chaves_invalidas),
        cabecalho_igual=antes[0] == depois[0],
        mesmas_chaves_e_ordem=mesmas,
        hash_humanas=hash_linhas([depois[1:][i] for i in humanas]),
    )


# --------------------------------------------------------------------------- #
# Concordância bruta (não é o kappa de Fleiss entre os 3 slots)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Concordancia:
    dimensao: str
    unidade: str
    n: int
    concordancia_pct: float
    kappa_cohen: float | None


def _por_unidade(df: pd.DataFrame, dimensao: str, unidade: str) -> pd.Series:
    if unidade == "repositorio":
        return df.drop_duplicates("repo_idx").set_index("repo_idx")[dimensao]
    return df.set_index(CHAVE)[dimensao]


def comparar_rotulos(a: pd.DataFrame, b: pd.DataFrame) -> list[Concordancia]:
    """Concordância bruta e kappa de Cohen entre dois conjuntos de rótulos nas chaves em comum.

    `tipo_projeto` e `entrega_real` são por repositório (unidade = repositório) e
    `release_corretiva` por release. Quando os dois lados cobrem as mesmas 5 releases de cada
    repositório, a concordância "por linha" de `tipo_projeto` é a mesma que a por repositório.
    """
    resultados = []
    for dim in DIMENSOES:
        unidade = dim.unidade
        sa, sb = _por_unidade(a, dim.nome, unidade), _por_unidade(b, dim.nome, unidade)
        comuns = sa.index.intersection(sb.index)
        sa, sb = sa.loc[comuns], sb.loc[comuns]
        n = len(comuns)
        concordancia = float((sa == sb).mean() * 100) if n else float("nan")
        # Cohen's kappa fica indefinido (0/0) sem variabilidade nas duas séries.
        if n and len(set(sa) | set(sb)) > 1:
            kappa = float(cohen_kappa_score(sa, sb, labels=list(dim.opcoes)))
        else:
            kappa = None
        resultados.append(Concordancia(dim.nome, unidade, n, concordancia, kappa))
    return resultados


def formatar(titulo: str, resultados: Sequence[Concordancia]) -> str:
    linhas = [titulo, f"{'dimensão':<18}{'unidade':<13}{'N':>5}  {'concordância':>12}  {'kappa de Cohen':>14}"]
    for r in resultados:
        kappa = "n/d" if r.kappa_cohen is None else f"{r.kappa_cohen:.3f}"
        linhas.append(f"{r.dimensao:<18}{r.unidade:<13}{r.n:>5}  {r.concordancia_pct:>11.1f}%  {kappa:>14}")
    return "\n".join(linhas)


def confiabilidade_gabriel(validacao_dir: Path | str) -> list[Concordancia]:
    """Execução commitada de Gabriel (Claude Code) × segunda execução de IA do mesmo slot."""
    pasta = Path(validacao_dir)
    return comparar_rotulos(carregar_csv(pasta / "rotulos_gabriel.csv"), carregar_csv(pasta / EXTRA_GABRIEL))


def ia_vs_humano(validacao_dir: Path | str, invalidas: Path | str, ia: str = "joao") -> list[Concordancia]:
    """Rótulos de IA do slot `ia` × as 150 linhas HUMANAS de `rotulos_marcela.csv`."""
    pasta = Path(validacao_dir)
    lista = carregar_csv(invalidas)
    chaves_invalidas = set(zip(lista["repo_idx"], lista["release_idx"]))
    marcela = carregar_csv(pasta / "rotulos_marcela.csv")
    humanas = marcela[[k not in chaves_invalidas for k in zip(marcela["repo_idx"], marcela["release_idx"])]]
    if ia == "gabriel2":
        maquina = carregar_csv(pasta / EXTRA_GABRIEL)
    else:
        maquina = carregar_csv(pasta / f"rotulos_{ia}.csv")
    return comparar_rotulos(maquina, humanas)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m analises.auditoria_rotulos_ia", description=__doc__.splitlines()[0])
    parser.add_argument("--validacao-dir", default=DEFAULT_VALIDACAO_DIR)
    parser.add_argument("--invalidas", default=DEFAULT_INVALIDAS)
    sub = parser.add_subparsers(dest="comando", required=True)
    p_h = sub.add_parser("humanas", help="Prova que as linhas humanas de rotulos_marcela.csv não mudaram")
    p_h.add_argument("--anterior", required=True, help="rotulos_marcela.csv da main (ex.: git show <commit>:...)")
    sub.add_parser("confiabilidade", help="Gabriel (commitado) × segunda execução de IA do mesmo slot")
    sub.add_parser("ia-vs-humano", help="Rótulos de IA × 150 linhas humanas de Marcela (aviso de validade)")
    args = parser.parse_args(argv)

    if args.comando == "humanas":
        r = verificar_linhas_humanas(args.anterior, Path(args.validacao_dir) / "rotulos_marcela.csv", args.invalidas)
        print(f"linhas humanas: {r.n_humanas}; linhas de IA: {r.n_ia}")
        print(f"cabeçalho igual: {r.cabecalho_igual}; mesmas chaves e ordem: {r.mesmas_chaves_e_ordem}")
        print(f"linhas humanas byte-idênticas à main: {r.humanas_identicas}")
        print(f"chaves das linhas de IA == lista de linhas inválidas: {r.chaves_ia_igual_lista}")
        print(f"sha256 das linhas humanas (CRLF, em ordem): {r.hash_humanas}")
        print("OK" if r.ok else "FALHOU")
        return 0 if r.ok else 1
    if args.comando == "confiabilidade":
        print(formatar("Gabriel (execução commitada) × segunda execução de IA", confiabilidade_gabriel(args.validacao_dir)))
        return 0
    nomes = {"joao": "joao (IA)", "gabriel": "gabriel (commitado)", "gabriel2": "gabriel (execução 2, extra)"}
    for ia, nome in nomes.items():
        resultados = ia_vs_humano(args.validacao_dir, args.invalidas, ia)
        print(formatar(f"{nome} × Marcela humana (150 linhas, 30 repositórios)", resultados))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

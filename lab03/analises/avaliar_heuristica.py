"""Avaliação das versões da heurística de release corretiva contra o consenso (Issue #62).

Implementa o passo 5 da Seção 6 do Guia do Lab03: compara cada versão registrada em
`metricas.cfr_b.HEURISTICS` com o rótulo de consenso `release_corretiva` e calcula
precisão, recall e F1 com `sklearn.metrics.precision_recall_fscore_support`
(classe positiva = `sim`).

Fluxo:

* lê `validacao/consenso.csv` (produzido pelos humanos, Issue #65) — nunca é criado aqui;
* para cada release do consenso, procura em `dados/releases/<dono>__<repo>.parquet`
  (gerado por `analises.persistir_amostra_ouro`) o `previous_release` e os commits e aplica
  `is_corrective_release(previous_release, tag_name, commits, version=...)`;
* releases que não podem ser avaliadas são **excluídas e contadas**: arquivo de releases
  ausente, tag ausente no arquivo, `status != ok` (primeira release, tag não encontrada)
  ou `previous_release` nulo. A exclusão não depende da versão da heurística, então
  todas as versões são avaliadas sobre o mesmo conjunto;
* lista falsos positivos e falsos negativos de cada versão (análise de erros).

O módulo só grava arquivos em caminhos informados explicitamente (`--saida`,
`--saida-erros`), não sobrescreve sem `--forcar` e recusa gravar sobre o consenso.

Execução (a partir de `lab03/`):
    uv run python -m analises.avaliar_heuristica
    uv run python -m analises.avaliar_heuristica --saida dados/analises/avaliacao_heuristica.md
    uv run python -m analises.avaliar_heuristica --saida avaliacao.csv --saida-erros erros.csv
"""

from __future__ import annotations

import argparse
import inspect
import math
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import precision_recall_fscore_support

from analises.concordancia import ORIGEM_PENDENTE, carregar_csv
from metricas.cfr_b import HEURISTICS, is_corrective_release, is_fix_message, is_patch_bump
from metricas.schemas import Commit

DEFAULT_CONSENSO = "validacao/consenso.csv"
DEFAULT_RELEASES_DIR = "dados/releases"
META_F1 = 0.70

ROTULO_SIM = "sim"
ROTULO_NAO = "não"
COLUNAS_CONSENSO = ["repo_name", "tag_name", "release_corretiva"]

STATUS_OK = "ok"
MOTIVO_SEM_ARQUIVO = "sem arquivo de releases do repositório"
MOTIVO_TAG_AUSENTE = "tag ausente no arquivo de releases"
MOTIVO_SEM_ANTERIOR = "sem release anterior (previous_release nulo)"
MOTIVO_STATUS = "status != ok ({status})"

TIPO_FP = "falso_positivo"
TIPO_FN = "falso_negativo"
MAX_MENSAGENS_ERRO = 3
MAX_CHARS_MENSAGEM = 100


class AvaliacaoError(Exception):
    """Erro base da avaliação da heurística."""


class EntradaAusenteError(AvaliacaoError):
    """Consenso ou diretório de releases não encontrado."""


@dataclass(frozen=True)
class Exemplo:
    """Release do consenso que pode ser avaliada pela heurística."""

    repo_name: str
    tag_name: str
    consenso: bool
    previous_release: str
    commits: tuple[Commit, ...]
    release_url: str = ""


@dataclass(frozen=True)
class Exclusao:
    """Release do consenso que não pôde ser avaliada, com o motivo."""

    repo_name: str
    tag_name: str
    motivo: str


@dataclass(frozen=True)
class Amostra:
    """Releases avaliáveis e excluídas (independente da versão da heurística)."""

    exemplos: list[Exemplo]
    exclusoes: list[Exclusao]

    @property
    def motivos(self) -> Counter[str]:
        return Counter(e.motivo for e in self.exclusoes)


@dataclass(frozen=True)
class ResultadoVersao:
    """Métricas de uma versão da heurística. `None` = indefinida (divisão por zero)."""

    versao: str
    regra: str
    precisao: float | None
    recall: float | None
    f1: float | None
    n_avaliadas: int
    n_excluidas: int
    vp: int
    fp: int
    fn: int
    vn: int
    atinge_meta: bool


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #
def carregar_consenso(path: Path | str) -> pd.DataFrame:
    """Lê o `consenso.csv` e valida as colunas, os valores e a ausência de pendências."""
    path = Path(path)
    if not path.is_file():
        raise EntradaAusenteError(
            f"Consenso não encontrado: {path}. O arquivo é produzido pelos humanos na reunião "
            "de consenso (Issue #65, `analises.concordancia verificar-consenso`)."
        )
    try:
        df = carregar_csv(path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise AvaliacaoError(f"não foi possível ler {path}: {exc}") from exc

    faltantes = [c for c in COLUNAS_CONSENSO if c not in df.columns]
    if faltantes:
        raise AvaliacaoError(f"{path}: colunas ausentes: {', '.join(faltantes)}")

    erros: list[str] = []
    invalidos = ~df["release_corretiva"].isin([ROTULO_SIM, ROTULO_NAO])
    if invalidos.any():
        linhas = ", ".join(f"{i + 2}='{df['release_corretiva'][i]}'" for i in df.index[invalidos][:5])
        erros.append(f"release_corretiva fora de ['{ROTULO_SIM}', '{ROTULO_NAO}'] (linhas): {linhas}")
    if "release_corretiva_origem" in df.columns:
        pendentes = df["release_corretiva_origem"] == ORIGEM_PENDENTE
        if pendentes.any():
            erros.append(f"{int(pendentes.sum())} linha(s) com release_corretiva_origem pendente")
    duplicadas = df.duplicated(["repo_name", "tag_name"], keep=False)
    if duplicadas.any():
        erros.append(f"{int(duplicadas.sum())} linha(s) com (repo_name, tag_name) duplicados")
    if erros:
        raise AvaliacaoError(f"{path} inválido:\n" + "\n".join(f"  - {e}" for e in erros))
    return df


def caminho_releases(releases_dir: Path, repo_name: str) -> Path:
    """Arquivo Parquet de um repositório (`dono/repo` → `dono__repo.parquet`)."""
    return releases_dir / f"{repo_name.replace('/', '__')}.parquet"


def _carregar_releases_repo(path: Path) -> dict[str, dict[str, object]]:
    """Mapa tag → {previous_release, status, commits} de um arquivo de releases."""
    dados = pq.read_table(path).to_pydict()
    mapa: dict[str, dict[str, object]] = {}
    for i, tag in enumerate(dados["tag_name"]):
        mapa.setdefault(
            tag,
            {
                "previous_release": dados["previous_release"][i],
                "status": dados["status"][i],
                "commits": [
                    Commit(sha=c["sha"], committed_at=c["committed_at"], message=c["message"])
                    for c in dados["commits"][i] or []
                ],
            },
        )
    return mapa


def montar_amostra(consenso: pd.DataFrame, releases_dir: Path | str) -> Amostra:
    """Cruza o consenso com os dados de releases e separa avaliáveis de excluídas."""
    releases_dir = Path(releases_dir)
    if not releases_dir.is_dir():
        raise EntradaAusenteError(
            f"Diretório de releases não encontrado: {releases_dir}. Gere-o com "
            "`uv run python -m analises.persistir_amostra_ouro` (requer token e rede)."
        )
    cache: dict[str, dict[str, dict[str, object]] | None] = {}
    exemplos: list[Exemplo] = []
    exclusoes: list[Exclusao] = []
    url = consenso["release_url"] if "release_url" in consenso.columns else None

    for i, linha in consenso.iterrows():
        repo, tag = linha["repo_name"], linha["tag_name"]
        if repo not in cache:
            arquivo = caminho_releases(releases_dir, repo)
            cache[repo] = _carregar_releases_repo(arquivo) if arquivo.is_file() else None
        mapa = cache[repo]
        if mapa is None:
            exclusoes.append(Exclusao(repo, tag, MOTIVO_SEM_ARQUIVO))
        elif tag not in mapa:
            exclusoes.append(Exclusao(repo, tag, MOTIVO_TAG_AUSENTE))
        elif mapa[tag]["status"] != STATUS_OK:
            exclusoes.append(Exclusao(repo, tag, MOTIVO_STATUS.format(status=mapa[tag]["status"])))
        elif not mapa[tag]["previous_release"]:
            exclusoes.append(Exclusao(repo, tag, MOTIVO_SEM_ANTERIOR))
        else:
            registro = mapa[tag]
            exemplos.append(
                Exemplo(
                    repo_name=repo,
                    tag_name=tag,
                    consenso=linha["release_corretiva"] == ROTULO_SIM,
                    previous_release=str(registro["previous_release"]),
                    commits=tuple(registro["commits"]),  # type: ignore[arg-type]
                    release_url=str(url[i]) if url is not None else "",
                )
            )
    return Amostra(exemplos=exemplos, exclusoes=exclusoes)


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def descrever_regra(versao: str) -> str:
    """Primeira linha do docstring da heurística: é a descrição da regra da versão."""
    doc = inspect.getdoc(HEURISTICS[versao]) or ""
    return doc.splitlines()[0].strip() if doc else "(sem descrição)"


def prever(exemplo: Exemplo, versao: str) -> bool:
    """Aplica a versão `versao` da heurística a uma release."""
    return is_corrective_release(
        exemplo.previous_release, exemplo.tag_name, exemplo.commits, version=versao
    )


def _ou_none(valor: float) -> float | None:
    return None if math.isnan(float(valor)) else float(valor)


def calcular_metricas(
    verdadeiro: Sequence[bool], previsto: Sequence[bool]
) -> tuple[float | None, float | None, float | None, tuple[int, int, int, int]]:
    """Precisão, recall e F1 da classe positiva, e a matriz (VP, FP, FN, VN).

    Usa `precision_recall_fscore_support` com `zero_division=nan`: uma métrica com
    denominador zero (ex.: a heurística não marcou nenhuma release) é *indefinida*
    (`None`), e não 0.
    """
    if len(verdadeiro) != len(previsto):
        raise ValueError("verdadeiro e previsto devem ter o mesmo tamanho")
    if not len(verdadeiro):
        raise AvaliacaoError("nenhuma release avaliável: não há como calcular precisão/recall/F1")
    y_true = np.asarray(verdadeiro, dtype=int)
    y_pred = np.asarray(previsto, dtype=int)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[1], average=None, zero_division=np.nan
    )
    vp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    vn = int(((y_true == 0) & (y_pred == 0)).sum())
    return _ou_none(p[0]), _ou_none(r[0]), _ou_none(f1[0]), (vp, fp, fn, vn)


def avaliar_versao(amostra: Amostra, versao: str, meta_f1: float = META_F1) -> ResultadoVersao:
    """Avalia uma versão da heurística sobre as releases avaliáveis."""
    verdadeiro = [e.consenso for e in amostra.exemplos]
    previsto = [prever(e, versao) for e in amostra.exemplos]
    p, r, f1, (vp, fp, fn, vn) = calcular_metricas(verdadeiro, previsto)
    return ResultadoVersao(
        versao=versao,
        regra=descrever_regra(versao),
        precisao=p,
        recall=r,
        f1=f1,
        n_avaliadas=len(amostra.exemplos),
        n_excluidas=len(amostra.exclusoes),
        vp=vp,
        fp=fp,
        fn=fn,
        vn=vn,
        atinge_meta=f1 is not None and f1 >= meta_f1,
    )


def avaliar_todas(
    amostra: Amostra, versoes: Sequence[str] | None = None, meta_f1: float = META_F1
) -> list[ResultadoVersao]:
    """Avalia as versões pedidas (default: todas as de `HEURISTICS`, na ordem de registro)."""
    desconhecidas = [v for v in (versoes or []) if v not in HEURISTICS]
    if desconhecidas:
        raise AvaliacaoError(
            f"versão(ões) desconhecida(s): {', '.join(desconhecidas)}. "
            f"Registradas: {', '.join(HEURISTICS)}"
        )
    return [avaliar_versao(amostra, v, meta_f1) for v in (versoes or list(HEURISTICS))]


# --------------------------------------------------------------------------- #
# Análise de erros
# --------------------------------------------------------------------------- #
def _resumo_mensagens(commits: Sequence[Commit]) -> str:
    """Primeira linha dos primeiros commits que mencionam revert/hotfix/fix."""
    assunto = [
        (c.message.splitlines() or [""])[0][:MAX_CHARS_MENSAGEM]
        for c in commits
        if is_fix_message(c.message)
    ]
    return " | ".join(assunto[:MAX_MENSAGENS_ERRO])


def listar_erros(amostra: Amostra, versoes: Sequence[str]) -> pd.DataFrame:
    """Falsos positivos e falsos negativos de cada versão, com evidências da regra."""
    registros: list[dict[str, object]] = []
    for versao in versoes:
        for e in amostra.exemplos:
            previsto = prever(e, versao)
            if previsto == e.consenso:
                continue
            registros.append(
                {
                    "versao": versao,
                    "tipo": TIPO_FP if previsto else TIPO_FN,
                    "repo_name": e.repo_name,
                    "tag_name": e.tag_name,
                    "previous_release": e.previous_release,
                    "consenso": ROTULO_SIM if e.consenso else ROTULO_NAO,
                    "heuristica": ROTULO_SIM if previsto else ROTULO_NAO,
                    "bump_patch": _formatar_bump(is_patch_bump(e.previous_release, e.tag_name)),
                    "n_commits": len(e.commits),
                    "n_commits_fix": sum(is_fix_message(c.message) for c in e.commits),
                    "mensagens_fix": _resumo_mensagens(e.commits),
                    "release_url": e.release_url,
                }
            )
    colunas = [
        "versao", "tipo", "repo_name", "tag_name", "previous_release", "consenso", "heuristica",
        "bump_patch", "n_commits", "n_commits_fix", "mensagens_fix", "release_url",
    ]  # fmt: skip
    return pd.DataFrame(registros, columns=colunas)


def _formatar_bump(valor: bool | None) -> str:
    return "n/d" if valor is None else ("sim" if valor else "não")


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #
def _fmt(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor:.3f}"


def tabela_resultados(resultados: Sequence[ResultadoVersao]) -> pd.DataFrame:
    """Tabela (valores numéricos crus; `None` = indefinido) das versões avaliadas."""
    return pd.DataFrame(
        [
            {
                "versao": r.versao,
                "regra": r.regra,
                "precisao": r.precisao,
                "recall": r.recall,
                "f1": r.f1,
                "n_avaliadas": r.n_avaliadas,
                "n_excluidas": r.n_excluidas,
                "vp": r.vp,
                "fp": r.fp,
                "fn": r.fn,
                "vn": r.vn,
                "atinge_meta_f1": r.atinge_meta,
            }
            for r in resultados
        ]
    )


def formatar_console(resultados: Sequence[ResultadoVersao], amostra: Amostra, meta_f1: float) -> str:
    linhas = [
        f"Releases do consenso: {len(amostra.exemplos) + len(amostra.exclusoes)} | "
        f"avaliadas: {len(amostra.exemplos)} | excluídas: {len(amostra.exclusoes)}"
    ]
    for motivo, n in sorted(amostra.motivos.items()):
        linhas.append(f"  excluídas — {motivo}: {n}")
    linhas.append("")
    linhas.append(
        f"{'versão':<8}{'precisão':>9}{'recall':>8}{'F1':>7}{'N aval.':>9}{'N excl.':>9}"
        f"{'VP':>5}{'FP':>5}{'FN':>5}{'VN':>5}  F1≥{meta_f1:.2f}  regra"
    )
    for r in resultados:
        linhas.append(
            f"{r.versao:<8}{_fmt(r.precisao):>9}{_fmt(r.recall):>8}{_fmt(r.f1):>7}"
            f"{r.n_avaliadas:>9}{r.n_excluidas:>9}{r.vp:>5}{r.fp:>5}{r.fn:>5}{r.vn:>5}"
            f"  {'sim' if r.atinge_meta else 'não':<6}  {r.regra}"
        )
    return "\n".join(linhas)


def formatar_markdown(
    resultados: Sequence[ResultadoVersao], amostra: Amostra, meta_f1: float
) -> str:
    """Relatório em Markdown: tabela de versões (P/R/F1) e contagem de exclusões."""
    total = len(amostra.exemplos) + len(amostra.exclusoes)
    linhas = [
        "# Avaliação da heurística de release corretiva",
        "",
        f"Releases no consenso: **{total}** · avaliadas: **{len(amostra.exemplos)}** · "
        f"excluídas: **{len(amostra.exclusoes)}**. Classe positiva: `{ROTULO_SIM}`.",
        "",
        "| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN "
        f"| F1 ≥ {meta_f1:.2f} |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in resultados:
        regra = r.regra.replace("|", "\\|")
        linhas.append(
            f"| {r.versao} | {regra} | {_fmt(r.precisao)} | {_fmt(r.recall)} | {_fmt(r.f1)} "
            f"| {r.n_avaliadas} | {r.n_excluidas} | {r.vp} | {r.fp} | {r.fn} | {r.vn} "
            f"| {'sim' if r.atinge_meta else 'não'} |"
        )
    linhas += ["", "## Releases excluídas", ""]
    if amostra.exclusoes:
        linhas += ["| Motivo | N |", "|---|---:|"]
        linhas += [f"| {m} | {n} |" for m, n in sorted(amostra.motivos.items())]
    else:
        linhas.append("Nenhuma.")
    linhas += ["", "`n/d` = métrica indefinida (denominador zero).", ""]
    return "\n".join(linhas)


def _gravar(destino: Path, conteudo: str | pd.DataFrame, sobrescrever: bool, consenso: Path) -> None:
    if destino.resolve() == consenso.resolve():
        raise AvaliacaoError(f"{destino} é o arquivo de consenso; escolha outro caminho de saída.")
    if destino.exists() and not sobrescrever:
        raise AvaliacaoError(f"{destino} já existe; use --forcar para sobrescrever.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, pd.DataFrame):
        conteudo.to_csv(destino, index=False, encoding="utf-8-sig")
    else:
        destino.write_text(conteudo, encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analises.avaliar_heuristica",
        description="Avalia as versões da heurística de release corretiva contra o consenso (Issue #62)",
    )
    parser.add_argument("--consenso", default=DEFAULT_CONSENSO, help="Caminho do consenso.csv")
    parser.add_argument("--releases-dir", default=DEFAULT_RELEASES_DIR, help="Diretório com os Parquet de releases")
    parser.add_argument(
        "--versoes", nargs="+", default=None, metavar="V",
        help=f"Versões a avaliar (default: todas — {', '.join(HEURISTICS)})",
    )  # fmt: skip
    parser.add_argument("--meta-f1", type=float, default=META_F1, help="F1 mínimo aceitável (default: 0.70)")
    parser.add_argument("--saida", help="Grava a tabela neste caminho (.csv → CSV; senão Markdown)")
    parser.add_argument("--saida-erros", help="Grava falsos positivos/negativos (CSV) neste caminho")
    parser.add_argument("--max-erros", type=int, default=10, help="Máx. de erros por tipo/versão no console")
    parser.add_argument("--forcar", action="store_true", help="Sobrescreve saídas existentes")
    return parser


def _imprimir_erros(erros: pd.DataFrame, versoes: Sequence[str], maximo: int) -> None:
    for versao in versoes:
        for tipo, titulo in ((TIPO_FP, "Falsos positivos"), (TIPO_FN, "Falsos negativos")):
            sel = erros[(erros["versao"] == versao) & (erros["tipo"] == tipo)]
            print(f"\n{titulo} de {versao}: {len(sel)}")
            for _, e in sel.head(maximo).iterrows():
                extra = f" — {e['mensagens_fix']}" if e["mensagens_fix"] else ""
                print(f"  {e['repo_name']} {e['previous_release']} → {e['tag_name']}{extra}")
            if len(sel) > maximo:
                print(f"  (+{len(sel) - maximo}; use --saida-erros para a lista completa)")


def _executar(args: argparse.Namespace) -> int:
    consenso_path = Path(args.consenso)
    consenso = carregar_consenso(consenso_path)
    amostra = montar_amostra(consenso, args.releases_dir)
    resultados = avaliar_todas(amostra, args.versoes, args.meta_f1)
    versoes = [r.versao for r in resultados]
    erros = listar_erros(amostra, versoes)

    print(formatar_console(resultados, amostra, args.meta_f1))
    _imprimir_erros(erros, versoes, args.max_erros)

    if args.saida:
        destino = Path(args.saida)
        conteudo = (
            tabela_resultados(resultados)
            if destino.suffix.lower() == ".csv"
            else formatar_markdown(resultados, amostra, args.meta_f1)
        )
        _gravar(destino, conteudo, args.forcar, consenso_path)
        print(f"\n[*] Tabela gravada em {destino}")
    if args.saida_erros:
        _gravar(Path(args.saida_erros), erros, args.forcar, consenso_path)
        print(f"[*] Erros gravados em {args.saida_erros}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)
    try:
        return _executar(args)
    except EntradaAusenteError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except AvaliacaoError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

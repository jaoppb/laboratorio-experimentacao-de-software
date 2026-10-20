"""Concordância entre avaliadores (kappa de Fleiss) e consolidação de consenso (Issue #65).

Implementa o passo 3 e 4 da Seção 6 do Guia do Lab03:

* valida os arquivos de rótulos dos três avaliadores (`validacao/rotulos_<id>.csv`)
  contra a planilha em branco gerada pelo sorteio (`dados/amostra_ouro/`);
* calcula o kappa de Fleiss (`aggregate_raters` + `fleiss_kappa`, do statsmodels)
  em cada uma das três dimensões, com a interpretação de Landis & Koch (1977);
* lista as divergências (insumo da reunião de consenso);
* gera um *modelo* de `consenso.csv` (maioria preenchida, empates 1-1-1 em branco)
  e verifica o `consenso.csv` final depois da reunião.

Unidade de análise (importante):

* `tipo_projeto` e `entrega_real` são julgamentos **por repositório**. A planilha
  repete o valor nas 5 linhas do repositório, então a unidade é o repositório
  (60 unidades), e não a linha (300 linhas).
* `release_corretiva` é julgamento **por release** (300 unidades).

Este módulo NUNCA cria `rotulos_*.csv` nem grava `consenso.csv` por padrão: o arquivo
de consenso só é escrito quando o caminho de saída é informado explicitamente.

Execução (a partir de `lab03/`), com os três arquivos em `validacao/`:
    uv run python -m analises.concordancia validar
    uv run python -m analises.concordancia kappa
    uv run python -m analises.concordancia divergencias --saida /tmp/divergencias.csv
    uv run python -m analises.concordancia consenso --saida /tmp/consenso_modelo.csv
    uv run python -m analises.concordancia verificar-consenso
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from analises.amostra_ouro import (
    AVALIADORES,
    OPCOES_ENTREGA_REAL,
    OPCOES_RELEASE_CORRETIVA,
    OPCOES_TIPO_PROJETO,
)

DEFAULT_VALIDACAO_DIR = "validacao"
DEFAULT_PLANILHA = "dados/amostra_ouro/amostra_ouro_template.csv"
DEFAULT_CONSENSO = "validacao/consenso.csv"

UNIDADE_REPOSITORIO = "repositorio"
UNIDADE_RELEASE = "release"

COLUNAS_CHAVE_RELEASE = ["repo_idx", "release_idx"]
COLUNAS_IDENTIFICACAO = [
    "repo_idx",
    "repo_name",
    "repo_url",
    "release_idx",
    "tag_name",
    "published_at",
    "release_url",
]


@dataclass(frozen=True)
class Dimensao:
    """Uma dimensão de rotulação: coluna, categorias permitidas e unidade de análise."""

    nome: str
    opcoes: tuple[str, ...]
    unidade: str


# O mapeamento categoria -> código numérico é a posição em `opcoes` (explícito e estável).
DIMENSOES: tuple[Dimensao, ...] = (
    Dimensao("tipo_projeto", tuple(OPCOES_TIPO_PROJETO), UNIDADE_REPOSITORIO),
    Dimensao("entrega_real", tuple(OPCOES_ENTREGA_REAL), UNIDADE_REPOSITORIO),
    Dimensao("release_corretiva", tuple(OPCOES_RELEASE_CORRETIVA), UNIDADE_RELEASE),
)

COLUNAS_ROTULO = [d.nome for d in DIMENSOES]
COLUNAS_OBRIGATORIAS = COLUNAS_IDENTIFICACAO + COLUNAS_ROTULO
IDS_AVALIADORES = [a["id"] for a in AVALIADORES]

ORIGEM_UNANIMIDADE = "unanimidade"
ORIGEM_MAIORIA = "maioria"
ORIGEM_PENDENTE = "pendente"
ORIGEM_REUNIAO = "reuniao"
ORIGENS_VALIDAS = (ORIGEM_UNANIMIDADE, ORIGEM_MAIORIA, ORIGEM_REUNIAO)

MAX_ERROS_POR_TIPO = 5


class ConcordanciaError(Exception):
    """Erro base do módulo de concordância."""


class ArquivosAusentesError(ConcordanciaError):
    """Faltam arquivos de rótulos de avaliadores."""

    def __init__(self, ausentes: Sequence[str], diretorio: Path):
        self.ausentes = list(ausentes)
        self.diretorio = Path(diretorio)
        arquivos = ", ".join(f"rotulos_{a}.csv" for a in self.ausentes)
        super().__init__(
            f"Arquivos de rótulos ausentes em {self.diretorio}: {arquivos}. "
            f"São necessários os {len(IDS_AVALIADORES)} avaliadores "
            f"({', '.join(IDS_AVALIADORES)}) para calcular o kappa de Fleiss."
        )


class RotulosInvalidosError(ConcordanciaError):
    """O arquivo de rótulos não respeita o formato esperado."""

    def __init__(self, origem: str, erros: Sequence[str]):
        self.origem = origem
        self.erros = list(erros)
        corpo = "\n".join(f"  - {e}" for e in self.erros)
        super().__init__(f"Arquivo inválido ({origem}):\n{corpo}")


@dataclass(frozen=True)
class ResultadoKappa:
    dimensao: str
    unidade: str
    n_unidades: int
    n_avaliadores: int
    kappa: float | None  # None quando indefinido (sem variabilidade nas categorias)
    concordancia_unanime_pct: float
    interpretacao: str


# --------------------------------------------------------------------------- #
# Interpretação
# --------------------------------------------------------------------------- #
def interpretar_landis_koch(kappa: float | None) -> str:
    """Faixa de Landis & Koch (1977) para um valor de kappa."""
    if kappa is None or math.isnan(kappa):
        return "indefinido (sem variabilidade nas categorias)"
    if kappa < 0:
        return "pobre"
    if kappa <= 0.20:
        return "leve"
    if kappa <= 0.40:
        return "razoável"
    if kappa <= 0.60:
        return "moderada"
    if kappa <= 0.80:
        return "substancial"
    return "quase perfeita"


# --------------------------------------------------------------------------- #
# Carga e validação
# --------------------------------------------------------------------------- #
def carregar_csv(path: Path | str) -> pd.DataFrame:
    """Lê um CSV de rotulação como texto, sem converter vazios em NaN."""
    df = pd.read_csv(Path(path), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    return df.apply(lambda col: col.str.strip())


def _resumir(erros: list[str], titulo: str, itens: Sequence[str]) -> None:
    if not itens:
        return
    mostrados = ", ".join(itens[:MAX_ERROS_POR_TIPO])
    extra = f" (+{len(itens) - MAX_ERROS_POR_TIPO})" if len(itens) > MAX_ERROS_POR_TIPO else ""
    erros.append(f"{titulo}: {mostrados}{extra}")


def _chave_linha(df: pd.DataFrame) -> pd.Series:
    return df["repo_idx"] + "/" + df["release_idx"]


def validar_planilha_referencia(referencia: pd.DataFrame) -> None:
    """Garante que a planilha em branco tem as colunas e chaves necessárias."""
    faltantes = [c for c in COLUNAS_IDENTIFICACAO if c not in referencia.columns]
    erros: list[str] = []
    if faltantes:
        erros.append(f"colunas ausentes na planilha de referência: {', '.join(faltantes)}")
    elif referencia.duplicated(COLUNAS_CHAVE_RELEASE).any():
        erros.append("planilha de referência tem (repo_idx, release_idx) duplicados")
    if erros:
        raise RotulosInvalidosError("planilha de referência", erros)


def validar_rotulos(df: pd.DataFrame, referencia: pd.DataFrame) -> list[str]:
    """Valida um DataFrame de rótulos contra a planilha de referência.

    Verifica colunas, quantidade de linhas, chaves (repo_idx, release_idx) e
    identificação (repo_name, tag_name), valores permitidos em cada dimensão e
    consistência por repositório de `tipo_projeto` e `entrega_real`.
    Retorna a lista de mensagens de erro (vazia se válido).
    """
    erros: list[str] = []

    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltantes:
        return [f"colunas ausentes: {', '.join(faltantes)}"]

    if len(df) != len(referencia):
        erros.append(f"{len(df)} linhas, esperado {len(referencia)}")

    duplicadas = df.loc[df.duplicated(COLUNAS_CHAVE_RELEASE, keep=False), "repo_idx"].str.cat(
        df["release_idx"], sep="/"
    )
    _resumir(erros, "chaves (repo_idx/release_idx) duplicadas", sorted(set(duplicadas)))

    chaves_df = set(_chave_linha(df))
    chaves_ref = set(_chave_linha(referencia))
    _resumir(erros, "chaves ausentes em relação à planilha", sorted(chaves_ref - chaves_df))
    _resumir(erros, "chaves inesperadas em relação à planilha", sorted(chaves_df - chaves_ref))

    # Identificação (nome do repositório e tag) deve coincidir com a planilha sorteada.
    if not erros:
        ref_idx = referencia.set_index(COLUNAS_CHAVE_RELEASE)
        df_idx = df.set_index(COLUNAS_CHAVE_RELEASE).reindex(ref_idx.index)
        for coluna in ("repo_name", "tag_name"):
            difere = df_idx[coluna] != ref_idx[coluna]
            _resumir(
                erros,
                f"{coluna} diferente da planilha",
                [f"{r}/{i}" for r, i in ref_idx.index[difere.to_numpy()]],
            )

    for dim in DIMENSOES:
        permitidos = set(dim.opcoes)
        valores = df[dim.nome]
        vazios = valores == ""
        _resumir(
            erros,
            f"{dim.nome} em branco (linhas)",
            [str(i + 2) for i in df.index[vazios]],  # +2: cabeçalho + base 1
        )
        invalidos = ~vazios & ~valores.isin(permitidos)
        _resumir(
            erros,
            f"{dim.nome} com valor fora de {sorted(permitidos)} (linhas)",
            [f"{i + 2}='{valores[i]}'" for i in df.index[invalidos]],
        )

        if dim.unidade == UNIDADE_REPOSITORIO:
            variacao = df.groupby("repo_idx")[dim.nome].nunique()
            _resumir(
                erros,
                f"{dim.nome} diverge entre as releases do mesmo repositório (repo_idx)",
                sorted(variacao[variacao > 1].index, key=_ordem_numerica),
            )

    return erros


def _ordem_numerica(valor: str) -> tuple[int, str]:
    return (int(valor), valor) if valor.isdigit() else (10**9, valor)


def carregar_rotulos_validados(
    path: Path | str, referencia: pd.DataFrame, nome: str | None = None
) -> pd.DataFrame:
    """Carrega um arquivo de rótulos e levanta `RotulosInvalidosError` se inválido."""
    path = Path(path)
    origem = nome or str(path)
    try:
        df = carregar_csv(path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise RotulosInvalidosError(origem, [f"não foi possível ler o CSV: {exc}"]) from exc
    erros = validar_rotulos(df, referencia)
    if erros:
        raise RotulosInvalidosError(origem, erros)
    return df


def carregar_avaliadores(
    validacao_dir: Path | str,
    referencia: pd.DataFrame,
    avaliadores: Sequence[str] = tuple(IDS_AVALIADORES),
) -> dict[str, pd.DataFrame]:
    """Carrega e valida `rotulos_<id>.csv` de todos os avaliadores pedidos.

    Levanta `ArquivosAusentesError` se algum arquivo não existir (nenhum arquivo é criado).
    """
    validacao_dir = Path(validacao_dir)
    ausentes = [a for a in avaliadores if not (validacao_dir / f"rotulos_{a}.csv").is_file()]
    if ausentes:
        raise ArquivosAusentesError(ausentes, validacao_dir)
    return {
        a: carregar_rotulos_validados(
            validacao_dir / f"rotulos_{a}.csv", referencia, nome=f"rotulos_{a}.csv"
        )
        for a in avaliadores
    }


# --------------------------------------------------------------------------- #
# Unidades de análise e kappa
# --------------------------------------------------------------------------- #
def _chaves(df: pd.DataFrame, dim: Dimensao) -> pd.Series:
    """Chave textual da unidade de análise de cada linha (`repo_idx` ou `repo_idx/release_idx`)."""
    if dim.unidade == UNIDADE_REPOSITORIO:
        return df["repo_idx"]
    return _chave_linha(df)


def rotulos_por_unidade(
    rotulos: Mapping[str, pd.DataFrame], dim: Dimensao, referencia: pd.DataFrame
) -> pd.DataFrame:
    """Matriz unidades x avaliadores (valores em texto) para uma dimensão.

    Repositório: uma linha por `repo_idx` (valor repetido nas 5 releases é contado uma vez).
    Release: uma linha por (`repo_idx`, `release_idx`). A ordem segue a planilha de referência.
    """
    indice = pd.Index(_chaves(referencia, dim).drop_duplicates())
    colunas: dict[str, pd.Series] = {}
    for avaliador, df in rotulos.items():
        serie = pd.Series(df[dim.nome].to_numpy(), index=_chaves(df, dim).to_numpy())
        colunas[avaliador] = serie[~serie.index.duplicated()].reindex(indice)
    return pd.DataFrame(colunas, index=indice)


def _matriz_codigos(matriz: pd.DataFrame, dim: Dimensao) -> np.ndarray:
    codigos = {valor: i for i, valor in enumerate(dim.opcoes)}
    return matriz.apply(lambda col: col.map(codigos)).to_numpy(dtype=int)


def calcular_kappa_matriz(matriz: pd.DataFrame, dim: Dimensao) -> ResultadoKappa:
    """Kappa de Fleiss de uma matriz unidades x avaliadores (texto) para uma dimensão."""
    if matriz.empty or matriz.isna().any().any():
        raise ConcordanciaError(f"{dim.nome}: matriz de rótulos vazia ou com valores ausentes")
    codigos = _matriz_codigos(matriz, dim)
    tabela, _ = aggregate_raters(codigos, n_cat=len(dim.opcoes))
    with np.errstate(invalid="ignore", divide="ignore"):
        kappa = float(fleiss_kappa(tabela, method="fleiss"))
    kappa_valor = None if math.isnan(kappa) else kappa
    unanime = float((matriz.nunique(axis=1) == 1).mean() * 100)
    return ResultadoKappa(
        dimensao=dim.nome,
        unidade=dim.unidade,
        n_unidades=len(matriz),
        n_avaliadores=matriz.shape[1],
        kappa=kappa_valor,
        concordancia_unanime_pct=unanime,
        interpretacao=interpretar_landis_koch(kappa_valor),
    )


def calcular_kappas(
    rotulos: Mapping[str, pd.DataFrame], referencia: pd.DataFrame
) -> list[ResultadoKappa]:
    """Kappa de Fleiss nas três dimensões (cada uma na sua unidade de análise)."""
    return [
        calcular_kappa_matriz(rotulos_por_unidade(rotulos, dim, referencia), dim)
        for dim in DIMENSOES
    ]


# --------------------------------------------------------------------------- #
# Divergências e consenso
# --------------------------------------------------------------------------- #
def votar(votos: Sequence[str]) -> tuple[str | None, str]:
    """Aplica a regra de maioria simples.

    Retorna `(rótulo, origem)`: `unanimidade` (todos iguais), `maioria` (mais de
    50% dos votos) ou `(None, 'pendente')` quando não há maioria (ex.: 1-1-1).
    """
    contagem = Counter(votos).most_common()
    rotulo, n = contagem[0]
    if n == len(votos):
        return rotulo, ORIGEM_UNANIMIDADE
    if n * 2 > len(votos):
        return rotulo, ORIGEM_MAIORIA
    return None, ORIGEM_PENDENTE


def _padrao_votos(votos: Sequence[str]) -> str:
    return "-".join(str(n) for _, n in Counter(votos).most_common())


def listar_divergencias(
    rotulos: Mapping[str, pd.DataFrame], referencia: pd.DataFrame
) -> pd.DataFrame:
    """Uma linha por unidade e dimensão em que os avaliadores não concordam por unanimidade."""
    avaliadores = list(rotulos)
    registros: list[dict[str, str]] = []
    for dim in DIMENSOES:
        matriz = rotulos_por_unidade(rotulos, dim, referencia)
        ref = referencia.assign(_k=_chaves(referencia, dim)).drop_duplicates("_k").set_index("_k")
        for chave, linha in zip(matriz.index, matriz.itertuples(index=False)):
            votos = list(linha)
            if len(set(votos)) == 1:
                continue
            sugestao, origem = votar(votos)
            info = ref.loc[chave]
            registros.append(
                {
                    "dimensao": dim.nome,
                    "unidade": dim.unidade,
                    "repo_idx": info["repo_idx"],
                    "release_idx": info["release_idx"] if dim.unidade == UNIDADE_RELEASE else "",
                    "repo_name": info["repo_name"],
                    "tag_name": info["tag_name"] if dim.unidade == UNIDADE_RELEASE else "",
                    "link": info["release_url"] if dim.unidade == UNIDADE_RELEASE else info["repo_url"],
                    **{f"rotulo_{a}": v for a, v in zip(avaliadores, votos)},
                    "padrao_votos": _padrao_votos(votos),
                    "sugestao_maioria": sugestao or "",
                    "decisao": origem,
                }
            )
    colunas = [
        "dimensao", "unidade", "repo_idx", "release_idx", "repo_name", "tag_name", "link",
        *[f"rotulo_{a}" for a in avaliadores], "padrao_votos", "sugestao_maioria", "decisao",
    ]  # fmt: skip
    return pd.DataFrame(registros, columns=colunas)


def gerar_modelo_consenso(
    rotulos: Mapping[str, pd.DataFrame], referencia: pd.DataFrame
) -> pd.DataFrame:
    """Gera o modelo de `consenso.csv` no formato da planilha, com colunas de origem.

    Maioria (3-0 ou 2-1) vem preenchida; empates (1-1-1) ficam em branco com origem
    `pendente`, para serem decididos na reunião. Ao decidir, preencher o rótulo e
    trocar a origem para `reuniao`.
    """
    base = referencia[COLUNAS_IDENTIFICACAO].copy()
    for dim in DIMENSOES:
        matriz = rotulos_por_unidade(rotulos, dim, referencia)
        resultado = {
            chave: votar(list(linha)) for chave, linha in zip(matriz.index, matriz.itertuples(index=False))
        }
        chaves = _chaves(base, dim)
        base[dim.nome] = [resultado[k][0] or "" for k in chaves]
        base[f"{dim.nome}_origem"] = [resultado[k][1] for k in chaves]
    base["notas_consenso"] = ""
    ordem = [
        "repo_idx", "repo_name", "repo_url", "tipo_projeto", "tipo_projeto_origem",
        "entrega_real", "entrega_real_origem", "release_idx", "tag_name", "published_at",
        "release_url", "release_corretiva", "release_corretiva_origem", "notas_consenso",
    ]  # fmt: skip
    return base[ordem]


def validar_consenso(df: pd.DataFrame, referencia: pd.DataFrame) -> list[str]:
    """Valida o `consenso.csv` final: formato, valores permitidos e nenhuma pendência."""
    erros = validar_rotulos(df, referencia)
    faltantes = [f"{d.nome}_origem" for d in DIMENSOES if f"{d.nome}_origem" not in df.columns]
    if faltantes:
        return erros + [f"colunas ausentes: {', '.join(faltantes)}"]
    for dim in DIMENSOES:
        origem = df[f"{dim.nome}_origem"]
        pendentes = origem == ORIGEM_PENDENTE
        _resumir(erros, f"{dim.nome} ainda pendente de reunião (linhas)", [str(i + 2) for i in df.index[pendentes]])
        invalidas = ~pendentes & ~origem.isin(ORIGENS_VALIDAS)
        _resumir(
            erros,
            f"{dim.nome}_origem fora de {list(ORIGENS_VALIDAS)} (linhas)",
            [f"{i + 2}='{origem[i]}'" for i in df.index[invalidas]],
        )
    return erros


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def formatar_relatorio_kappa(resultados: Sequence[ResultadoKappa]) -> str:
    linhas = [
        f"{'dimensão':<18}{'unidade':<13}{'N':>5}  {'kappa':>7}  {'unânime %':>9}  interpretação (Landis & Koch)"
    ]
    for r in resultados:
        kappa = "n/d" if r.kappa is None else f"{r.kappa:.3f}"
        linhas.append(
            f"{r.dimensao:<18}{r.unidade:<13}{r.n_unidades:>5}  {kappa:>7}  "
            f"{r.concordancia_unanime_pct:>8.1f}%  {r.interpretacao}"
        )
    return "\n".join(linhas)


def _gravar_csv(df: pd.DataFrame, destino: Path, sobrescrever: bool) -> None:
    if destino.exists() and not sobrescrever:
        raise ConcordanciaError(
            f"{destino} já existe; use --forcar para sobrescrever (cuidado: pode apagar decisões da reunião)."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, encoding="utf-8-sig")


def _carregar_referencia(caminho: str) -> pd.DataFrame:
    path = Path(caminho)
    if not path.is_file():
        raise ConcordanciaError(f"Planilha de referência não encontrada: {path}")
    referencia = carregar_csv(path)
    validar_planilha_referencia(referencia)
    return referencia


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analises.concordancia",
        description="Concordância (kappa de Fleiss) e consenso da amostra-ouro (Issue #65)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    def comum(p: argparse.ArgumentParser, avaliadores: bool = False) -> None:
        p.add_argument("--validacao-dir", default=DEFAULT_VALIDACAO_DIR, help="Diretório com rotulos_<id>.csv")
        p.add_argument("--planilha", default=DEFAULT_PLANILHA, help="Planilha em branco de referência (chaves)")
        if avaliadores:
            p.add_argument(
                "--avaliadores", nargs="+", default=IDS_AVALIADORES, choices=IDS_AVALIADORES,
                help="Avaliadores a validar (default: todos)",
            )  # fmt: skip

    comum(sub.add_parser("validar", help="Valida o formato dos arquivos de rótulos"), avaliadores=True)

    p_kappa = sub.add_parser("kappa", help="Kappa de Fleiss nas três dimensões")
    comum(p_kappa)
    p_kappa.add_argument("--json", dest="saida_json", help="Grava o resultado também em JSON neste caminho")

    p_div = sub.add_parser("divergencias", help="Lista casos sem unanimidade (pauta da reunião)")
    comum(p_div)
    p_div.add_argument("--saida", help="Grava a lista em CSV neste caminho (opcional)")
    p_div.add_argument("--forcar", action="store_true", help="Sobrescreve a saída se existir")

    p_cons = sub.add_parser("consenso", help="Gera o modelo de consenso (maioria + pendências)")
    comum(p_cons)
    p_cons.add_argument("--saida", required=True, help="Caminho do CSV de consenso (obrigatório, sem default)")
    p_cons.add_argument("--forcar", action="store_true", help="Sobrescreve a saída se existir")

    p_ver = sub.add_parser("verificar-consenso", help="Verifica o consenso.csv final (sem pendências)")
    comum(p_ver)
    p_ver.add_argument("--consenso", default=DEFAULT_CONSENSO, help="Caminho do consenso.csv")
    return parser


def _executar(args: argparse.Namespace) -> int:
    referencia = _carregar_referencia(args.planilha)

    if args.comando == "validar":
        rotulos = carregar_avaliadores(args.validacao_dir, referencia, args.avaliadores)
        for avaliador, df in rotulos.items():
            print(f"[ok] rotulos_{avaliador}.csv: {len(df)} linhas válidas")
        return 0

    if args.comando == "verificar-consenso":
        path = Path(args.consenso)
        if not path.is_file():
            raise ConcordanciaError(f"Consenso não encontrado: {path}")
        erros = validar_consenso(carregar_csv(path), referencia)
        if erros:
            raise RotulosInvalidosError(str(path), erros)
        print(f"[ok] {path}: consenso completo e válido")
        return 0

    rotulos = carregar_avaliadores(args.validacao_dir, referencia)

    if args.comando == "kappa":
        resultados = calcular_kappas(rotulos, referencia)
        print(formatar_relatorio_kappa(resultados))
        if args.saida_json:
            destino = Path(args.saida_json)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(
                json.dumps([asdict(r) for r in resultados], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return 0

    if args.comando == "divergencias":
        div = listar_divergencias(rotulos, referencia)
        resumo = div.groupby("dimensao").size() if not div.empty else pd.Series(dtype=int)
        for dim in DIMENSOES:
            print(f"{dim.nome}: {int(resumo.get(dim.nome, 0))} divergência(s)")
        if args.saida:
            _gravar_csv(div, Path(args.saida), args.forcar)
            print(f"[*] Divergências gravadas em {args.saida}")
        return 0

    if args.comando == "consenso":
        modelo = gerar_modelo_consenso(rotulos, referencia)
        _gravar_csv(modelo, Path(args.saida), args.forcar)
        for dim in DIMENSOES:
            pend = int((modelo[f"{dim.nome}_origem"] == ORIGEM_PENDENTE).sum())
            print(f"{dim.nome}: {pend} linha(s) pendente(s) de reunião")
        print(f"[*] Modelo de consenso gravado em {args.saida}")
        return 0

    raise ConcordanciaError(f"Comando desconhecido: {args.comando}")  # pragma: no cover


def main(argv: Sequence[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)
    try:
        return _executar(args)
    except ArquivosAusentesError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except ConcordanciaError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

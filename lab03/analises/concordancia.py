"""Concordância entre avaliadores (kappa de Fleiss) e consolidação de consenso (Issue #65).

Implementa o passo 3 e 4 da Seção 6 do Guia do Lab03:

* valida os arquivos de rótulos dos três avaliadores (`validacao/rotulos_<id>.csv`)
  contra a planilha em branco gerada pelo sorteio (`dados/amostra_ouro/`);
* calcula o kappa de Fleiss (`aggregate_raters` + `fleiss_kappa`, do statsmodels)
  em cada uma das três dimensões, com a interpretação de Landis & Koch (1977);
* lista as divergências (insumo da reunião de consenso);
* rejeita linhas-placeholder (`(pendente de persistência)`) da planilha e dos rótulos;
  um avaliador cujo arquivo tem linhas void (rotuladas sobre placeholders) só é aceito
  com uma lista explícita de linhas inválidas (`validacao/<id>_linhas_invalidas.csv`), e
  nesse caso cobre apenas as linhas válidas (veja `carregar_linhas_invalidas`);
* gera um *modelo* de `consenso.csv` (maioria preenchida, empates 1-1-1 em branco)
  e verifica o `consenso.csv` final depois da reunião.

Unidade de análise (importante):

* `tipo_projeto` e `entrega_real` são julgamentos **por repositório**. A planilha
  repete o valor nas 5 linhas do repositório, então a unidade é o repositório
  (60 unidades), e não a linha (300 linhas).
* `release_corretiva` é julgamento **por release** (300 unidades).

Este módulo NUNCA cria `rotulos_*.csv` nem grava `consenso.csv` por padrão: o arquivo
de consenso só é escrito quando o caminho de saída é informado explicitamente.

Modo com avaliadores IA (desvio documentado, ver `docs/protocolo_consenso.md` seção 7):

* `--origens` carrega e valida os arquivos auxiliares `rotulos_<id>_origem.csv`
  (`repo_idx,release_idx,origem,modelo,esforco,data_utc`; `origem` ∈ {`ia`, `humano`}),
  imprime o resumo de proveniência por avaliador e, se houver linha de IA, um aviso de que o
  kappa mede a concordância entre execuções do mesmo modelo, não entre pessoas;
* `consenso --modo-automatico --origens` gera o consenso por maioria **sem reunião**
  (1-1-1 → `outro`/`incerto`), marcado com `consenso_modo=automatico_maioria`.

Execução (a partir de `lab03/`), com os três arquivos em `validacao/`:
    uv run python -m analises.concordancia validar
    uv run python -m analises.concordancia kappa
    uv run python -m analises.concordancia divergencias --saida /tmp/divergencias.csv
    uv run python -m analises.concordancia consenso --saida /tmp/consenso_modelo.csv
    uv run python -m analises.concordancia verificar-consenso
    uv run python -m analises.concordancia kappa --origens
    uv run python -m analises.concordancia consenso --modo-automatico --origens --saida /tmp/consenso.csv
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
    TAG_PLACEHOLDER,
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
SUFIXO_LINHAS_INVALIDAS = "_linhas_invalidas.csv"
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
ORIGEM_DESEMPATE_AUTOMATICO = "desempate_automatico"
ORIGENS_VALIDAS = (ORIGEM_UNANIMIDADE, ORIGEM_MAIORIA, ORIGEM_REUNIAO)

# Proveniência dos rótulos (arquivo auxiliar `rotulos_<id>_origem.csv`).
SUFIXO_ORIGEM = "_origem.csv"
FONTE_IA = "ia"
FONTE_HUMANO = "humano"
FONTES_VALIDAS = (FONTE_IA, FONTE_HUMANO)
COLUNAS_ORIGEM = ["repo_idx", "release_idx", "origem", "modelo", "esforco", "data_utc"]
# Coluna opcional: nota de independência em texto livre (ex.: independência apenas parcial);
# é repetida na saída do resumo de proveniência, para que a ressalva acompanhe os números.
COLUNA_INDEPENDENCIA = "independencia"
AVISO_ROTULOS_IA = (
    "AVISO: rótulos de IA: o kappa mede concordância entre execuções do mesmo modelo, "
    "não entre pessoas"
)

# Modo de consenso sem reunião (coluna `consenso_modo` do consenso.csv).
MODO_AUTOMATICO_MAIORIA = "automatico_maioria"
MODOS_CONSENSO = (MODO_AUTOMATICO_MAIORIA,)
# Desempate 1-1-1 sem reunião: as categorias de "não classificável" do protocolo.
DESEMPATE_AUTOMATICO = {"tipo_projeto": "outro", "entrega_real": "incerto"}

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


def _chaves_placeholder(df: pd.DataFrame) -> list[str]:
    """Chaves `repo_idx/release_idx` das linhas cuja tag é o placeholder do sorteio incompleto."""
    return sorted(_chave_linha(df[df["tag_name"] == TAG_PLACEHOLDER]), key=_ordem_chave)


def _mensagem_placeholder(chaves: Sequence[str], alvo: str) -> str:
    return (
        f"{len(chaves)} linha(s) com tag placeholder '{TAG_PLACEHOLDER}' {alvo} "
        f"(sorteio incompleto; não há release real para rotular): "
        f"{', '.join(chaves[:MAX_ERROS_POR_TIPO])}"
        + (f" (+{len(chaves) - MAX_ERROS_POR_TIPO})" if len(chaves) > MAX_ERROS_POR_TIPO else "")
    )


def validar_planilha_referencia(referencia: pd.DataFrame) -> None:
    """Garante que a planilha em branco tem as colunas e chaves necessárias."""
    faltantes = [c for c in COLUNAS_IDENTIFICACAO if c not in referencia.columns]
    erros: list[str] = []
    if faltantes:
        erros.append(f"colunas ausentes na planilha de referência: {', '.join(faltantes)}")
    elif referencia.duplicated(COLUNAS_CHAVE_RELEASE).any():
        erros.append("planilha de referência tem (repo_idx, release_idx) duplicados")
    else:
        placeholders = _chaves_placeholder(referencia)
        if placeholders:
            erros.append(
                _mensagem_placeholder(placeholders, "na planilha de referência")
                + ". Complete o sorteio com: uv run python -m analises.amostra_ouro --completar-pendentes"
            )
    if erros:
        raise RotulosInvalidosError("planilha de referência", erros)


def validar_rotulos(
    df: pd.DataFrame,
    referencia: pd.DataFrame,
    linhas_invalidas: pd.DataFrame | None = None,
) -> list[str]:
    """Valida um DataFrame de rótulos contra a planilha de referência.

    Verifica colunas, quantidade de linhas, chaves (repo_idx, release_idx) e
    identificação (repo_name, tag_name), valores permitidos em cada dimensão e
    consistência por repositório de `tipo_projeto` e `entrega_real`.

    Linhas com a tag-placeholder do sorteio incompleto são sempre rejeitadas, a menos
    que sua chave conste em `linhas_invalidas` (lista explícita, ver
    `carregar_linhas_invalidas`). Com a lista, as linhas inválidas são ignoradas se
    estiverem no arquivo e dispensadas do arquivo: ele precisa cobrir apenas as demais
    linhas da planilha de referência.
    Retorna a lista de mensagens de erro (vazia se válido).
    """
    erros: list[str] = []

    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltantes:
        return [f"colunas ausentes: {', '.join(faltantes)}"]

    if linhas_invalidas is not None and len(linhas_invalidas):
        chaves_invalidas = set(_chave_linha(linhas_invalidas))
        df = df[~_chave_linha(df).isin(chaves_invalidas)]  # mantém o índice: linhas do arquivo
        referencia = referencia[~_chave_linha(referencia).isin(chaves_invalidas)].reset_index(drop=True)

    placeholders = _chaves_placeholder(df)
    if placeholders:
        erros.append(
            _mensagem_placeholder(placeholders, "no arquivo de rótulos")
            + ". Esses rótulos não valem; para validar só as linhas válidas informe a lista "
            f"explícita de linhas inválidas (<avaliador>{SUFIXO_LINHAS_INVALIDAS})"
        )

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


def _ordem_chave(chave: str) -> tuple[tuple[int, str], ...]:
    return tuple(_ordem_numerica(parte) for parte in chave.split("/"))


def carregar_linhas_invalidas(path: Path | str, referencia: pd.DataFrame) -> pd.DataFrame:
    """Lê a lista explícita de linhas inválidas de um avaliador (`repo_idx`, `release_idx`).

    Cada chave deve existir na planilha de referência e aparecer uma única vez; outras
    colunas (ex.: a chave antiga do placeholder) são apenas informativas.
    """
    path = Path(path)
    origem = path.name
    try:
        lista = carregar_csv(path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise RotulosInvalidosError(origem, [f"não foi possível ler o CSV: {exc}"]) from exc
    faltantes = [c for c in COLUNAS_CHAVE_RELEASE if c not in lista.columns]
    if faltantes:
        raise RotulosInvalidosError(origem, [f"colunas ausentes: {', '.join(faltantes)}"])
    erros: list[str] = []
    duplicadas = _chave_linha(lista)[lista.duplicated(COLUNAS_CHAVE_RELEASE)]
    _resumir(erros, "chaves (repo_idx/release_idx) duplicadas", sorted(set(duplicadas), key=_ordem_chave))
    desconhecidas = set(_chave_linha(lista)) - set(_chave_linha(referencia))
    _resumir(erros, "chaves inexistentes na planilha de referência", sorted(desconhecidas, key=_ordem_chave))
    if erros:
        raise RotulosInvalidosError(origem, erros)
    return lista


def carregar_rotulos_validados(
    path: Path | str,
    referencia: pd.DataFrame,
    nome: str | None = None,
    linhas_invalidas: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Carrega um arquivo de rótulos e levanta `RotulosInvalidosError` se inválido.

    Com `linhas_invalidas`, retorna apenas as linhas válidas (as inválidas são descartadas).
    """
    path = Path(path)
    origem = nome or str(path)
    try:
        df = carregar_csv(path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise RotulosInvalidosError(origem, [f"não foi possível ler o CSV: {exc}"]) from exc
    erros = validar_rotulos(df, referencia, linhas_invalidas)
    if erros:
        raise RotulosInvalidosError(origem, erros)
    if linhas_invalidas is not None and len(linhas_invalidas):
        df = df[~_chave_linha(df).isin(set(_chave_linha(linhas_invalidas)))].reset_index(drop=True)
    return df


def carregar_avaliadores(
    validacao_dir: Path | str,
    referencia: pd.DataFrame,
    avaliadores: Sequence[str] = tuple(IDS_AVALIADORES),
) -> dict[str, pd.DataFrame]:
    """Carrega e valida `rotulos_<id>.csv` de todos os avaliadores pedidos.

    Levanta `ArquivosAusentesError` se algum arquivo não existir (nenhum arquivo é criado).
    Se existir `<id>_linhas_invalidas.csv` ao lado de `rotulos_<id>.csv`, ele é usado como
    lista explícita de linhas inválidas daquele avaliador, e o DataFrame retornado contém só
    as linhas válidas (o kappa só é calculável quando todas as linhas forem rotuladas).
    """
    validacao_dir = Path(validacao_dir)
    ausentes = [a for a in avaliadores if not (validacao_dir / f"rotulos_{a}.csv").is_file()]
    if ausentes:
        raise ArquivosAusentesError(ausentes, validacao_dir)
    return {
        a: carregar_rotulos_validados(
            validacao_dir / f"rotulos_{a}.csv",
            referencia,
            nome=f"rotulos_{a}.csv",
            linhas_invalidas=_linhas_invalidas_do_avaliador(validacao_dir, a, referencia),
        )
        for a in avaliadores
    }


def _linhas_invalidas_do_avaliador(
    validacao_dir: Path, avaliador: str, referencia: pd.DataFrame
) -> pd.DataFrame | None:
    caminho = validacao_dir / f"{avaliador}{SUFIXO_LINHAS_INVALIDAS}"
    return carregar_linhas_invalidas(caminho, referencia) if caminho.is_file() else None


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
    if matriz.empty:
        raise ConcordanciaError(f"{dim.nome}: matriz de rótulos vazia")
    if matriz.isna().any().any():
        ausentes = matriz.isna().sum()
        detalhe = ", ".join(f"{a}: {int(n)}" for a, n in ausentes.items() if n)
        raise ConcordanciaError(
            f"{dim.nome}: há unidades sem rótulo ({detalhe}). Um avaliador com linhas "
            "inválidas ainda precisa rotular as linhas que faltam antes de calcular o kappa."
        )
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
# Proveniência dos rótulos (avaliadores IA / humanos)
# --------------------------------------------------------------------------- #
def carregar_origem_validada(
    path: Path | str, rotulos: pd.DataFrame, nome: str | None = None
) -> pd.DataFrame:
    """Carrega e valida o arquivo auxiliar de origem de um avaliador.

    As chaves (`repo_idx`, `release_idx`) devem coincidir **exatamente** com as linhas do
    `rotulos` já validado (sem duplicadas, ausentes ou sobrando); `origem` ∈ {`ia`, `humano`};
    linhas `ia` exigem `modelo`; e, como `tipo_projeto`/`entrega_real` são por repositório,
    a `origem` não pode variar entre as releases do mesmo repositório.
    """
    path = Path(path)
    origem = nome or str(path)
    try:
        df = carregar_csv(path)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise RotulosInvalidosError(origem, [f"não foi possível ler o CSV: {exc}"]) from exc
    faltantes = [c for c in COLUNAS_ORIGEM if c not in df.columns]
    if faltantes:
        raise RotulosInvalidosError(origem, [f"colunas ausentes: {', '.join(faltantes)}"])

    erros: list[str] = []
    duplicadas = _chave_linha(df)[df.duplicated(COLUNAS_CHAVE_RELEASE)]
    _resumir(erros, "chaves (repo_idx/release_idx) duplicadas", sorted(set(duplicadas), key=_ordem_chave))
    chaves_df, chaves_rot = set(_chave_linha(df)), set(_chave_linha(rotulos))
    _resumir(erros, "linhas de rótulo sem origem (chaves ausentes)", sorted(chaves_rot - chaves_df, key=_ordem_chave))
    _resumir(erros, "origem para chaves inexistentes nos rótulos", sorted(chaves_df - chaves_rot, key=_ordem_chave))

    invalidas = ~df["origem"].isin(FONTES_VALIDAS)
    _resumir(
        erros,
        f"origem fora de {list(FONTES_VALIDAS)} (linhas)",
        [f"{i + 2}='{df.loc[i, 'origem']}'" for i in df.index[invalidas]],
    )
    sem_modelo = (df["origem"] == FONTE_IA) & (df["modelo"] == "")
    _resumir(erros, "origem=ia sem modelo (linhas)", [str(i + 2) for i in df.index[sem_modelo]])
    variacao = df[~invalidas].groupby("repo_idx")["origem"].nunique()
    _resumir(
        erros,
        "origem diverge entre as releases do mesmo repositório (repo_idx)",
        sorted(variacao[variacao > 1].index, key=_ordem_numerica),
    )
    if erros:
        raise RotulosInvalidosError(origem, erros)
    opcionais = [COLUNA_INDEPENDENCIA] if COLUNA_INDEPENDENCIA in df.columns else []
    return df[COLUNAS_ORIGEM + opcionais].reset_index(drop=True)


def carregar_origens(
    validacao_dir: Path | str, rotulos: Mapping[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """Carrega `rotulos_<id>_origem.csv` de cada avaliador de `rotulos` (nada é criado)."""
    validacao_dir = Path(validacao_dir)
    ausentes = [
        f"rotulos_{a}{SUFIXO_ORIGEM}"
        for a in rotulos
        if not (validacao_dir / f"rotulos_{a}{SUFIXO_ORIGEM}").is_file()
    ]
    if ausentes:
        raise ConcordanciaError(
            f"Arquivos de origem ausentes em {validacao_dir}: {', '.join(ausentes)}. "
            "Com --origens cada avaliador precisa do seu rotulos_<id>_origem.csv."
        )
    return {
        a: carregar_origem_validada(
            validacao_dir / f"rotulos_{a}{SUFIXO_ORIGEM}", df, nome=f"rotulos_{a}{SUFIXO_ORIGEM}"
        )
        for a, df in rotulos.items()
    }


def resumir_proveniencia(origens: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Contagem de linhas por avaliador, origem, modelo e esforço."""
    partes = [
        df.groupby(["origem", "modelo", "esforco"], dropna=False)
        .size()
        .rename("n_linhas")
        .reset_index()
        .assign(avaliador=avaliador)
        for avaliador, df in origens.items()
    ]
    colunas = ["avaliador", "origem", "modelo", "esforco", "n_linhas"]
    if not partes:
        return pd.DataFrame(columns=colunas)
    return pd.concat(partes, ignore_index=True)[colunas]


def tem_rotulos_ia(origens: Mapping[str, pd.DataFrame]) -> bool:
    return any((df["origem"] == FONTE_IA).any() for df in origens.values())


def formatar_proveniencia(origens: Mapping[str, pd.DataFrame]) -> str:
    """Resumo textual da proveniência, seguido do aviso quando há rótulos de IA."""
    linhas = ["proveniência dos rótulos (origem / modelo / esforço: nº de linhas):"]
    resumo = resumir_proveniencia(origens)
    for avaliador in origens:
        partes = [
            f"{r.origem}/{r.modelo or '-'}/{r.esforco or '-'}: {r.n_linhas}"
            for r in resumo[resumo["avaliador"] == avaliador].itertuples()
        ]
        linhas.append(f"  {avaliador}: " + "; ".join(partes))
        notas = _notas_independencia(origens[avaliador])
        linhas.extend(f"    independência ({avaliador}): {nota}" for nota in notas)
    if tem_rotulos_ia(origens):
        linhas.append(f"!!! {AVISO_ROTULOS_IA} !!!")
    return "\n".join(linhas)


def _notas_independencia(origem: pd.DataFrame) -> list[str]:
    """Valores distintos e não vazios da coluna opcional `independencia` (ordem de aparição)."""
    if COLUNA_INDEPENDENCIA not in origem.columns:
        return []
    return [n for n in origem[COLUNA_INDEPENDENCIA].drop_duplicates() if n]


def proveniencia_para_json(origens: Mapping[str, pd.DataFrame]) -> dict:
    resumo = resumir_proveniencia(origens)
    return {
        "resumo": json.loads(resumo.to_json(orient="records", force_ascii=False)),
        "independencia": {a: n for a, df in origens.items() if (n := _notas_independencia(df))},
        "aviso": AVISO_ROTULOS_IA if tem_rotulos_ia(origens) else None,
    }


def fontes_por_unidade(
    origens: Mapping[str, pd.DataFrame], dim: Dimensao, referencia: pd.DataFrame
) -> pd.DataFrame:
    """Matriz unidades x avaliadores com a origem (`ia`/`humano`) do rótulo, como em `rotulos_por_unidade`."""
    como_rotulos = {a: df.rename(columns={"origem": dim.nome}) for a, df in origens.items()}
    return rotulos_por_unidade(como_rotulos, dim, referencia)


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


def votar_automatico(votos: Sequence[str], dim: Dimensao) -> tuple[str, str]:
    """Maioria simples sem reunião: 1-1-1 vira a categoria "não classificável" da dimensão.

    Retorna `(rótulo, origem)` com origem `unanimidade`, `maioria` ou `desempate_automatico`.
    `release_corretiva` é binária e, com 3 avaliadores, nunca empata 1-1-1.
    """
    rotulo, origem = votar(votos)
    if rotulo is not None:
        return rotulo, origem
    if dim.nome not in DESEMPATE_AUTOMATICO:  # pragma: no cover - binária não empata
        raise ConcordanciaError(f"{dim.nome}: sem regra de desempate automático para {list(votos)}")
    return DESEMPATE_AUTOMATICO[dim.nome], ORIGEM_DESEMPATE_AUTOMATICO


def gerar_consenso_automatico(
    rotulos: Mapping[str, pd.DataFrame],
    origens: Mapping[str, pd.DataFrame],
    referencia: pd.DataFrame,
) -> pd.DataFrame:
    """Consenso por maioria **sem reunião** (`consenso_modo=automatico_maioria`).

    Maioria por unidade (repositório em `tipo_projeto`/`entrega_real`; release em
    `release_corretiva`); 1-1-1 → `tipo_projeto=outro` / `entrega_real=incerto` com origem
    `desempate_automatico`. Para cada dimensão acrescenta `<dim>_votos_ia` e
    `<dim>_votos_humano`: quantos dos votos da unidade vieram de execuções de IA e de pessoas.
    """
    base = referencia[COLUNAS_IDENTIFICACAO].copy()
    contagens: dict[str, list[int]] = {}
    notas = [""] * len(base)
    for dim in DIMENSOES:
        matriz = rotulos_por_unidade(rotulos, dim, referencia)
        fontes = fontes_por_unidade(origens, dim, referencia)
        if fontes.isna().any().any():
            raise ConcordanciaError(f"{dim.nome}: há unidades sem origem declarada")
        resultado = {
            chave: votar_automatico(list(linha), dim)
            for chave, linha in zip(matriz.index, matriz.itertuples(index=False))
        }
        chaves = _chaves(base, dim)
        base[dim.nome] = [resultado[k][0] for k in chaves]
        base[f"{dim.nome}_origem"] = [resultado[k][1] for k in chaves]
        for fonte in FONTES_VALIDAS:
            por_chave = (fontes == fonte).sum(axis=1)
            contagens[f"{dim.nome}_votos_{fonte}"] = [int(por_chave[k]) for k in chaves]
        for i, k in enumerate(chaves):
            if resultado[k][1] == ORIGEM_DESEMPATE_AUTOMATICO:
                notas[i] = (notas[i] + " " if notas[i] else "") + (
                    f"{dim.nome}: desempate automático 1-1-1 -> {resultado[k][0]}"
                )
    base["notas_consenso"] = notas
    base["consenso_modo"] = MODO_AUTOMATICO_MAIORIA
    for coluna, valores in contagens.items():
        base[coluna] = valores
    ordem = [
        "repo_idx", "repo_name", "repo_url", "tipo_projeto", "tipo_projeto_origem",
        "entrega_real", "entrega_real_origem", "release_idx", "tag_name", "published_at",
        "release_url", "release_corretiva", "release_corretiva_origem", "notas_consenso",
        "consenso_modo", *contagens,
    ]  # fmt: skip
    return base[ordem]


def validar_consenso(df: pd.DataFrame, referencia: pd.DataFrame) -> list[str]:
    """Valida o `consenso.csv` final: formato, valores permitidos e nenhuma pendência."""
    erros = validar_rotulos(df, referencia)
    faltantes = [f"{d.nome}_origem" for d in DIMENSOES if f"{d.nome}_origem" not in df.columns]
    if faltantes:
        return erros + [f"colunas ausentes: {', '.join(faltantes)}"]
    automatico = pd.Series(False, index=df.index)
    if "consenso_modo" in df.columns:
        modo = df["consenso_modo"]
        _resumir(
            erros,
            f"consenso_modo fora de {list(MODOS_CONSENSO)} (linhas)",
            [f"{i + 2}='{modo[i]}'" for i in df.index[~modo.isin(MODOS_CONSENSO)]],
        )
        automatico = modo == MODO_AUTOMATICO_MAIORIA
    for dim in DIMENSOES:
        origem = df[f"{dim.nome}_origem"]
        pendentes = origem == ORIGEM_PENDENTE
        _resumir(erros, f"{dim.nome} ainda pendente de reunião (linhas)", [str(i + 2) for i in df.index[pendentes]])
        # `desempate_automatico` só vale no modo sem reunião (consenso_modo=automatico_maioria)
        validas = origem.isin(ORIGENS_VALIDAS) | ((origem == ORIGEM_DESEMPATE_AUTOMATICO) & automatico)
        invalidas = ~pendentes & ~validas
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

    def comum(p: argparse.ArgumentParser, avaliadores: bool = False, origens: bool = True) -> None:
        p.add_argument("--validacao-dir", default=DEFAULT_VALIDACAO_DIR, help="Diretório com rotulos_<id>.csv")
        p.add_argument("--planilha", default=DEFAULT_PLANILHA, help="Planilha em branco de referência (chaves)")
        if origens:
            p.add_argument(
                "--origens", action="store_true",
                help="Carrega rotulos_<id>_origem.csv (proveniência ia/humano) e a reporta na saída",
            )  # fmt: skip
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
    p_cons.add_argument(
        "--modo-automatico", action="store_true",
        help="Consenso por maioria SEM reunião (1-1-1 -> outro/incerto); exige --origens",
    )  # fmt: skip

    p_ver = sub.add_parser("verificar-consenso", help="Verifica o consenso.csv final (sem pendências)")
    comum(p_ver, origens=False)
    p_ver.add_argument("--consenso", default=DEFAULT_CONSENSO, help="Caminho do consenso.csv")
    return parser


def _executar(args: argparse.Namespace) -> int:
    referencia = _carregar_referencia(args.planilha)

    if args.comando == "validar":
        rotulos = carregar_avaliadores(args.validacao_dir, referencia, args.avaliadores)
        origens = carregar_origens(args.validacao_dir, rotulos) if args.origens else None
        for avaliador, df in rotulos.items():
            n_invalidas = len(referencia) - len(df)
            extra = (
                f" (cobre apenas as linhas válidas; {n_invalidas} inválidas/faltantes "
                f"conforme {avaliador}{SUFIXO_LINHAS_INVALIDAS})"
                if n_invalidas
                else ""
            )
            print(f"[ok] rotulos_{avaliador}.csv: {len(df)} linhas válidas{extra}")
            if origens is not None:
                print(f"[ok] rotulos_{avaliador}{SUFIXO_ORIGEM}: {len(origens[avaliador])} linhas de origem")
        if origens is not None:
            print(formatar_proveniencia(origens))
        return 0

    if args.comando == "verificar-consenso":
        path = Path(args.consenso)
        if not path.is_file():
            raise ConcordanciaError(f"Consenso não encontrado: {path}")
        consenso = carregar_csv(path)
        erros = validar_consenso(consenso, referencia)
        if erros:
            raise RotulosInvalidosError(str(path), erros)
        print(f"[ok] {path}: consenso completo e válido")
        if "consenso_modo" in consenso.columns:
            print(
                f"!!! AVISO: consenso gerado sem reunião (consenso_modo={MODO_AUTOMATICO_MAIORIA}): "
                "não é um consenso deliberado entre pessoas !!!"
            )
        return 0

    if args.comando == "consenso" and args.modo_automatico and not args.origens:
        raise ConcordanciaError(
            "--modo-automatico exige --origens: sem o registro de proveniência não há como "
            "declarar quantos votos vieram de IA e de pessoas."
        )

    rotulos = carregar_avaliadores(args.validacao_dir, referencia)
    origens = carregar_origens(args.validacao_dir, rotulos) if args.origens else None
    if origens is not None:
        print(formatar_proveniencia(origens))

    if args.comando == "kappa":
        resultados = calcular_kappas(rotulos, referencia)
        print(formatar_relatorio_kappa(resultados))
        if origens is not None and tem_rotulos_ia(origens):
            print(f"!!! {AVISO_ROTULOS_IA} !!!")
        if args.saida_json:
            destino = Path(args.saida_json)
            destino.parent.mkdir(parents=True, exist_ok=True)
            dados: object = [asdict(r) for r in resultados]
            if origens is not None:  # com --origens o JSON vira objeto (resultados + proveniência)
                dados = {"resultados": dados, "proveniencia": proveniencia_para_json(origens)}
            destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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

    if args.comando == "consenso" and args.modo_automatico:
        assert origens is not None  # garantido pela checagem acima
        automatico = gerar_consenso_automatico(rotulos, origens, referencia)
        _gravar_csv(automatico, Path(args.saida), args.forcar)
        for dim in DIMENSOES:
            contagem = automatico[f"{dim.nome}_origem"].value_counts()
            print(
                f"{dim.nome}: "
                + ", ".join(f"{o}={int(contagem.get(o, 0))}" for o in (ORIGEM_UNANIMIDADE, ORIGEM_MAIORIA, ORIGEM_DESEMPATE_AUTOMATICO))
                + " (linhas)"
            )
        print(f"[*] Consenso automático (sem reunião, {MODO_AUTOMATICO_MAIORIA}) gravado em {args.saida}")
        if tem_rotulos_ia(origens):
            print(f"!!! {AVISO_ROTULOS_IA} !!!")
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

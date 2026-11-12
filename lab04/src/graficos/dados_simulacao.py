"""Leitura e rótulos dos resultados das simulações Q1, Q2 e Q3 (usados em G3 e G4).

Os CSVs são gerados por ``scripts/simular_q1.py``, ``simular_q2.py`` e
``simular_q3.py``. Aqui apenas são lidos e organizados.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pvalores import carregar as carregar_p_valores
from src.pvalores import recalcular_taxas

RAIZ = Path(__file__).resolve().parents[2]
DIR_SIMULADO = RAIZ / "dados" / "simulado"

CSV_Q1 = DIR_SIMULADO / "q1_erro_tipo1.csv"
CSV_Q2 = DIR_SIMULADO / "q2_poder.csv"
CSV_Q3_TIPO1 = DIR_SIMULADO / "q3_erro_tipo1.csv"
CSV_Q3_PODER = DIR_SIMULADO / "q3_poder.csv"

TESTES = ("welch", "mannwhitney")
NOME_TESTE = {"welch": "t de Welch", "mannwhitney": "Mann-Whitney"}

# Situações simuladas, na ordem de exibição: (chave, rótulo, origem)
SITUACOES_Q1 = ("com_bot", "sem_bot")
SITUACOES_Q3 = ("referencia", "n_pequeno", "assimetria_extrema", "outliers")
ROTULO_SITUACAO = {
    "com_bot": "Q1/Q2: com_bot (parâmetros reais)",
    "sem_bot": "Q1/Q2: sem_bot (parâmetros reais)",
    "referencia": "Q3: referência (n=30, σ=1)",
    "n_pequeno": "Q3: n pequeno (n=10)",
    "assimetria_extrema": "Q3: assimetria extrema (σ=3)",
    "outliers": "Q3: outliers (5% × 20)",
}
ORDEM_SITUACOES = SITUACOES_Q1 + SITUACOES_Q3


def _ler(caminho: Path | str, colunas: set[str]) -> pd.DataFrame:
    df = pd.read_csv(caminho)
    faltando = colunas - set(df.columns)
    if faltando:
        raise KeyError(f"{caminho} sem colunas obrigatórias: {sorted(faltando)}")
    if df.empty:
        raise ValueError(f"{caminho} está vazio")
    return df


def carregar_erro_tipo1(
    q1: Path | str = CSV_Q1, q3: Path | str = CSV_Q3_TIPO1
) -> pd.DataFrame:
    """Une Q1 e Q3 em um DataFrame ``cenario, teste, n_rep, alfa, taxa_rejeicao``."""
    cols = {"cenario", "teste", "n_rep", "alfa", "taxa_rejeicao"}
    return pd.concat([_ler(q1, cols), _ler(q3, cols)], ignore_index=True)


def carregar_poder(
    q2: Path | str = CSV_Q2, q3: Path | str = CSV_Q3_PODER
) -> pd.DataFrame:
    """Une Q2 e Q3 em ``cenario, teste, razao_medianas, n_rep, alfa, taxa_rejeicao``."""
    cols = {"cenario", "teste", "razao_medianas", "n_rep", "alfa", "taxa_rejeicao"}
    return pd.concat([_ler(q2, cols), _ler(q3, cols)], ignore_index=True)


def situacoes_presentes(df: pd.DataFrame) -> list[str]:
    """Situações do DataFrame, na ordem canônica (desconhecidas vão ao final)."""
    presentes = list(dict.fromkeys(df["cenario"]))
    conhecidas = [s for s in ORDEM_SITUACOES if s in presentes]
    return conhecidas + [s for s in presentes if s not in ORDEM_SITUACOES]


def carregar_erro_tipo1_em(alfa: float, diretorio: Path | str = DIR_SIMULADO) -> pd.DataFrame:
    """Erro tipo I de Q1 e Q3 recalculado em ``alfa`` a partir dos p-valores guardados."""
    d = Path(diretorio)
    p = {**carregar_p_valores(d / "q1_p_valores.npz"), **carregar_p_valores(d / "q3_p_valores.npz")}
    return recalcular_taxas(
        carregar_erro_tipo1(d / CSV_Q1.name, d / CSV_Q3_TIPO1.name), p, alfa
    )


def carregar_poder_em(alfa: float, diretorio: Path | str = DIR_SIMULADO) -> pd.DataFrame:
    """Poder de Q2 e Q3 recalculado em ``alfa`` a partir dos p-valores guardados."""
    d = Path(diretorio)
    p = {**carregar_p_valores(d / "q2_p_valores.npz"), **carregar_p_valores(d / "q3_p_valores.npz")}
    return recalcular_taxas(carregar_poder(d / CSV_Q2.name, d / CSV_Q3_PODER.name), p, alfa)

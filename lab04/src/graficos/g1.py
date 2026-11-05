"""G1 em Plotly — dados reais ao lado dos dados simulados por grupo.

Gera histogramas comparativos dos tempos até o merge de PRs (reais vs simulados)
para os grupos ``com_bot`` e ``sem_bot``, utilizando escala logarítmica no eixo x
devido à cauda pesada característica da distribuição lognormal.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.estilo import (
    COR_COM_BOT,
    COR_DADOS_REAIS,
    COR_DADOS_SIMULADOS,
    COR_SEM_BOT,
    LAYOUT_BASE_PLOTLY,
)
from src.simulacao import gerar_dados

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_DADOS_REAIS_PADRAO = RAIZ / "dados" / "reais" / "pr_merge_time.csv"
CAMINHO_PARAMETROS_PADRAO = RAIZ / "dados" / "parametros.json"


def carregar_dados_reais(caminho: Path | str = CAMINHO_DADOS_REAIS_PADRAO) -> pd.DataFrame:
    """Carrega o CSV dos dados reais e valida colunas obrigatórias."""
    df = pd.read_csv(caminho)
    colunas_obrigatorias = {"grupo", "tempo_merge_horas"}
    faltando = colunas_obrigatorias - set(df.columns)
    if faltando:
        raise KeyError(f"CSV de dados reais sem colunas obrigatórias: {faltando}")
    if df.empty:
        raise ValueError("CSV de dados reais está vazio")
    return df


def carregar_parametros(caminho: Path | str = CAMINHO_PARAMETROS_PADRAO) -> dict:
    """Carrega os parâmetros estimados."""
    with open(caminho, encoding="utf-8") as f:
        params = json.load(f)
    for grupo in ("com_bot", "sem_bot"):
        if grupo not in params:
            raise KeyError(f"Grupo {grupo!r} não encontrado em parametros.json")
        for k in ("n", "mediana", "sigma_log"):
            if k not in params[grupo]:
                raise KeyError(f"Chave {k!r} ausente no grupo {grupo!r}")
    return params


def figura_g1(
    dados_reais: pd.DataFrame | Path | str | None = None,
    parametros: dict | Path | str | None = None,
    semente: int = 42,
) -> go.Figure:
    """Monta a figura G1 com histogramas comparativos (Reais vs Simulados).

    Dois painéis:
    1. Grupo com_bot: dados reais vs simulados
    2. Grupo sem_bot: dados reais vs simulados

    Eixo x em escala logarítmica (log10 de horas) e eixo y com contagem de PRs.

    Args:
        dados_reais: DataFrame ou caminho para o CSV de dados reais.
        parametros: dict ou caminho para o JSON de parâmetros da simulação.
        semente: semente aleatória para a geração simulada (default: 42).

    Returns:
        plotly.graph_objects.Figure configurada.
    """
    # Resolução de dados reais
    if isinstance(dados_reais, pd.DataFrame):
        df_reais = dados_reais.copy()
    elif dados_reais is not None:
        df_reais = carregar_dados_reais(dados_reais)
    else:
        df_reais = carregar_dados_reais(CAMINHO_DADOS_REAIS_PADRAO)

    # Resolução de parâmetros
    if isinstance(parametros, dict):
        params = parametros
    elif parametros is not None:
        params = carregar_parametros(parametros)
    else:
        params = carregar_parametros(CAMINHO_PARAMETROS_PADRAO)

    reais_com = df_reais[df_reais["grupo"] == "com_bot"]["tempo_merge_horas"].to_numpy(dtype=float)
    reais_sem = df_reais[df_reais["grupo"] == "sem_bot"]["tempo_merge_horas"].to_numpy(dtype=float)

    if len(reais_com) == 0 or len(reais_sem) == 0:
        raise ValueError("Dados reais devem conter observações para com_bot e sem_bot")

    # Geração dos dados simulados com a semente solicitada
    rng = np.random.default_rng(semente)
    sim_com, sim_sem = gerar_dados(
        rng,
        n_a=len(reais_com),
        n_b=len(reais_sem),
        mediana_a=float(params["com_bot"]["mediana"]),
        mediana_b=float(params["sem_bot"]["mediana"]),
        sigma_a=float(params["com_bot"]["sigma_log"]),
        sigma_b=float(params["sem_bot"]["sigma_log"]),
    )

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Grupo: com_bot (CodeRabbit) — Real (n={len(reais_com)}) vs Simulado (n={len(sim_com)})",
            f"Grupo: sem_bot (Controle) — Real (n={len(reais_sem)}) vs Simulado (n={len(sim_sem)})",
        ),
        horizontal_spacing=0.1,
    )

    # Painel 1: com_bot
    fig.add_trace(
        go.Histogram(
            x=reais_com,
            name="Real: com_bot",
            marker=dict(color=COR_DADOS_REAIS, opacity=0.65),
            nbinsx=15,
            legendgroup="real",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Histogram(
            x=sim_com,
            name="Simulado: com_bot",
            marker=dict(color=COR_DADOS_SIMULADOS, opacity=0.65),
            nbinsx=15,
            legendgroup="simulado",
        ),
        row=1,
        col=1,
    )

    # Painel 2: sem_bot
    fig.add_trace(
        go.Histogram(
            x=reais_sem,
            name="Real: sem_bot",
            marker=dict(color=COR_DADOS_REAIS, opacity=0.65),
            nbinsx=15,
            showlegend=True,
            legendgroup="real_sem",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Histogram(
            x=sim_sem,
            name="Simulado: sem_bot",
            marker=dict(color=COR_DADOS_SIMULADOS, opacity=0.65),
            nbinsx=15,
            showlegend=True,
            legendgroup="simulado_sem",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title=dict(
            text="G1 — Comparação dos dados reais e simulados (tempo até o merge)",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        barmode="overlay",
        **LAYOUT_BASE_PLOTLY,
    )

    # Configuração dos eixos com escala logarítmica e unidades explícitas
    fig.update_xaxes(
        type="log",
        title_text="Tempo até o merge (horas, escala log10)",
        row=1,
        col=1,
    )
    fig.update_xaxes(
        type="log",
        title_text="Tempo até o merge (horas, escala log10)",
        row=1,
        col=2,
    )

    fig.update_yaxes(
        title_text="Contagem de PRs (unidade: PRs)",
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="Contagem de PRs (unidade: PRs)",
        row=1,
        col=2,
    )

    return fig


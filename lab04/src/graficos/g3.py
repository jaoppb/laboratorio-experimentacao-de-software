"""G3 — erro tipo I dos dois testes em cada situação simulada (Q1 e Q3).

Barras agrupadas por situação (parâmetros reais de Q1 e as situações de Q3),
uma barra por teste, com a proporção de rejeições de H0 (H0 verdadeira) e uma
linha em 5%. As barras de erro mostram a margem de 95% da simulação.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.estilo import COR_CRITICO, COR_MANNWHITNEY, COR_WELCH, LAYOUT_BASE_PLOTLY
from src.graficos.seletor_alfa import adicionar_seletor
from src.graficos.dados_simulacao import (
    NOME_TESTE,
    ROTULO_SITUACAO,
    TESTES,
    carregar_erro_tipo1,
    situacoes_presentes,
)

_COR_TESTE = {"welch": COR_WELCH, "mannwhitney": COR_MANNWHITNEY}
_COLUNAS = {"cenario", "teste", "n_rep", "taxa_rejeicao"}


def _validar(df: pd.DataFrame) -> None:
    faltando = _COLUNAS - set(df.columns)
    if faltando:
        raise KeyError(f"erro tipo I sem colunas obrigatórias: {sorted(faltando)}")
    if df.empty:
        raise ValueError("DataFrame de erro tipo I está vazio")
    if not df["taxa_rejeicao"].between(0.0, 1.0).all():
        raise ValueError("taxa_rejeicao deve estar em [0, 1]")
    desconhecidos = set(df["teste"]) - set(TESTES)
    if desconhecidos:
        raise ValueError(f"testes desconhecidos: {sorted(desconhecidos)}")


def _barras(df, situacoes, rotulos, visivel):
    """Uma barra por teste (com margem de 95%) para as taxas de ``df``."""
    tracos = []
    for teste in TESTES:
        sub = df[df["teste"] == teste].set_index("cenario").reindex(situacoes)
        p = sub["taxa_rejeicao"].to_numpy(dtype=float)
        n = sub["n_rep"].to_numpy(dtype=float)
        margem = 1.96 * np.sqrt(p * (1.0 - p) / n) * 100.0
        tracos.append(
            go.Bar(
                x=rotulos,
                y=p * 100.0,
                name=NOME_TESTE[teste],
                marker=dict(color=_COR_TESTE[teste]),
                error_y=dict(type="data", array=margem, visible=True),
                text=[f"{v:.1f}%" for v in p * 100.0],
                textposition="outside",
                hovertemplate="%{x}<br>%{y:.2f}%<extra>" + NOME_TESTE[teste] + "</extra>",
                visible=visivel,
                showlegend=visivel,
            )
        )
    return tracos


def _limite_y(df: pd.DataFrame) -> float:
    return max(8.0, float(df["taxa_rejeicao"].max()) * 100.0 * 1.25)


def figura_g3(
    erro_tipo1: pd.DataFrame | None = None,
    alfa: float = 0.05,
    erro_tipo1_alt: pd.DataFrame | None = None,
    alfa_alt: float | None = None,
) -> go.Figure:
    """Monta o G3.

    Args:
        erro_tipo1: DataFrame com ``cenario, teste, n_rep, taxa_rejeicao`` (H0
            verdadeira). Se ``None``, lê os CSVs de Q1 e Q3.
        alfa: nível de significância desenhado como linha de referência.
        erro_tipo1_alt, alfa_alt: as mesmas taxas recalculadas em outro α. Se
            dados, a figura ganha botões para alternar entre os dois níveis.

    Returns:
        ``plotly.graph_objects.Figure`` com barras agrupadas por situação.
    """
    if not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa deve estar em (0, 1); recebido {alfa!r}")
    if (erro_tipo1_alt is None) != (alfa_alt is None):
        raise ValueError("erro_tipo1_alt e alfa_alt devem ser dados juntos")
    if alfa_alt is not None and not 0.0 < alfa_alt < 1.0:
        raise ValueError(f"alfa_alt deve estar em (0, 1); recebido {alfa_alt!r}")
    df = carregar_erro_tipo1() if erro_tipo1 is None else erro_tipo1.copy()
    _validar(df)

    situacoes = situacoes_presentes(df)
    rotulos = [ROTULO_SITUACAO.get(s, s) for s in situacoes]
    fig = go.Figure(_barras(df, situacoes, rotulos, True))
    if erro_tipo1_alt is not None:
        _validar(erro_tipo1_alt)
        fig.add_traces(_barras(erro_tipo1_alt, situacoes, rotulos, False))

    fig.add_hline(
        y=alfa * 100.0,
        line=dict(color=COR_CRITICO, width=2, dash="dash"),
        annotation_text=_texto_linha(alfa),
        annotation_position="top right",
    )
    fig.update_layout(
        title=dict(
            text="G3 — Erro tipo I dos dois testes em cada situação simulada",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        barmode="group",
        **LAYOUT_BASE_PLOTLY,
    )
    fig.update_xaxes(title_text="Situação simulada (H₀ verdadeira)")
    fig.update_yaxes(
        title_text="Proporção de rejeições de H₀ (%)", range=[0, _limite_y(df)]
    )
    if erro_tipo1_alt is not None:
        adicionar_seletor(
            fig, len(TESTES), (alfa, alfa_alt), _texto_linha,
            (_limite_y(df), _limite_y(erro_tipo1_alt)),
        )
    return fig


def _texto_linha(alfa: float) -> str:
    return f"α = {alfa * 100:g}% (esperado)"

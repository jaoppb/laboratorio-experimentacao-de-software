"""G4 — curvas de poder dos dois testes (Q2 e Q3).

Proporção de rejeições × tamanho do efeito (razão entre as medianas), com as
curvas dos dois testes no mesmo gráfico: uma curva por situação e teste. A cor
identifica o teste (``src/estilo.py``); o traço e o marcador identificam a situação.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.estilo import COR_CRITICO, COR_MANNWHITNEY, COR_WELCH, LAYOUT_BASE_PLOTLY
from src.graficos.dados_simulacao import (
    NOME_TESTE,
    ROTULO_SITUACAO,
    TESTES,
    carregar_poder,
    situacoes_presentes,
)

_COR_TESTE = {"welch": COR_WELCH, "mannwhitney": COR_MANNWHITNEY}
_TRACOS = ("solid", "dash", "dot", "dashdot", "longdash", "longdashdot")
_MARCADORES = ("circle", "square", "diamond", "triangle-up", "x", "cross")
_COLUNAS = {"cenario", "teste", "razao_medianas", "taxa_rejeicao"}


def _validar(df: pd.DataFrame) -> None:
    faltando = _COLUNAS - set(df.columns)
    if faltando:
        raise KeyError(f"poder sem colunas obrigatórias: {sorted(faltando)}")
    if df.empty:
        raise ValueError("DataFrame de poder está vazio")
    if not df["taxa_rejeicao"].between(0.0, 1.0).all():
        raise ValueError("taxa_rejeicao deve estar em [0, 1]")
    desconhecidos = set(df["teste"]) - set(TESTES)
    if desconhecidos:
        raise ValueError(f"testes desconhecidos: {sorted(desconhecidos)}")


def figura_g4(poder: pd.DataFrame | None = None, alfa: float = 0.05) -> go.Figure:
    """Monta o G4.

    Args:
        poder: DataFrame com ``cenario, teste, razao_medianas, taxa_rejeicao``.
            Se ``None``, lê os CSVs de Q2 e Q3.
        alfa: nível de significância desenhado como linha de referência.

    Returns:
        ``plotly.graph_objects.Figure`` com uma curva por situação e teste.
    """
    if not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa deve estar em (0, 1); recebido {alfa!r}")
    df = carregar_poder() if poder is None else poder.copy()
    _validar(df)

    situacoes = situacoes_presentes(df)
    fig = go.Figure()
    for i, situacao in enumerate(situacoes):
        traco = _TRACOS[i % len(_TRACOS)]
        marcador = _MARCADORES[i % len(_MARCADORES)]
        rotulo = ROTULO_SITUACAO.get(situacao, situacao)
        for teste in TESTES:
            sub = df[(df["cenario"] == situacao) & (df["teste"] == teste)]
            sub = sub.sort_values("razao_medianas")
            fig.add_trace(
                go.Scatter(
                    x=sub["razao_medianas"],
                    y=sub["taxa_rejeicao"] * 100.0,
                    mode="lines+markers",
                    name=f"{NOME_TESTE[teste]} — {rotulo}",
                    line=dict(color=_COR_TESTE[teste], dash=traco, width=2),
                    marker=dict(color=_COR_TESTE[teste], symbol=marcador, size=7),
                    legendgroup=situacao,
                    hovertemplate=(
                        "razão %{x}<br>%{y:.1f}% de rejeições<extra>"
                        f"{NOME_TESTE[teste]} — {rotulo}</extra>"
                    ),
                )
            )

    fig.add_hline(
        y=alfa * 100.0,
        line=dict(color=COR_CRITICO, width=1.5, dash="dash"),
        annotation_text=f"α = {alfa * 100:g}%",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title=dict(
            text="G4 — Curvas de poder dos dois testes (Q2 e Q3)",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        height=620,
        **LAYOUT_BASE_PLOTLY,
    )
    fig.update_xaxes(title_text="Tamanho do efeito (razão entre as medianas, adimensional)")
    fig.update_yaxes(title_text="Proporção de rejeições de H₀ (%)", range=[0, 102])
    return fig


"""G2 em Plotly — distribuição da estatística de teste sob H0 (Welch e Mann-Whitney).

Função pura que devolve um ``plotly.graph_objects.Figure`` com dois painéis:
1. Welch: t de Student com gl de Welch-Satterthwaite.
2. Mann-Whitney: normal padrão assintótica.

Inclui curva de densidade sob H0, região de rejeição bilateral sombreada,
estatística observada e o p-valor marcado como área das duas caudas.
"""

from __future__ import annotations

import copy
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

from src.estilo import (
    COR_CURVA,
    COR_OBSERVADA,
    COR_P_VALOR,
    COR_REJEICAO,
    LAYOUT_BASE_PLOTLY,
)

_PONTOS = 1200
_COBERTURA_CAUDA = 0.9995


def _validar(resultado_welch: dict, resultado_mw: dict, alpha: float) -> None:
    """Validações idênticas ao G2 do Matplotlib."""
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha deve estar em (0, 1); recebido {alpha!r}")
    for nome, res, chaves in (
        ("resultado_welch", resultado_welch, ("estatistica", "gl", "p_valor")),
        ("resultado_mw", resultado_mw, ("estatistica", "p_valor")),
    ):
        faltando = [c for c in chaves if c not in res]
        if faltando:
            raise KeyError(f"{nome} sem as chaves obrigatórias: {faltando}")
    for nome, res in (("welch", resultado_welch), ("mannwhitney", resultado_mw)):
        if res.get("alternativa", "two-sided") != "two-sided":
            raise ValueError(
                f"a figura G2 é bilateral; {nome} usa alternativa {res['alternativa']!r}"
            )
        p = res["p_valor"]
        if not (np.isfinite(p) and 0.0 <= p <= 1.0):
            raise ValueError(f"p_valor de {nome} deve estar em [0, 1]; recebido {p!r}")
    gl = resultado_welch["gl"]
    if not np.isfinite(gl) or gl <= 0:
        raise ValueError(f"gl deve ser positivo e finito; recebido {gl!r}")
    for nome, res in (("welch", resultado_welch), ("mannwhitney", resultado_mw)):
        if not np.isfinite(res["estatistica"]):
            raise ValueError(f"estatística de {nome} não é finita")


def _adicionar_painel(
    fig: go.Figure,
    dist,
    observada: float,
    p_valor: float,
    alpha: float,
    rotulo_teste: str,
    col: int,
) -> None:
    critico = float(dist.ppf(1.0 - alpha / 2.0))
    limite = 1.15 * max(abs(observada), critico, float(dist.ppf(_COBERTURA_CAUDA)))
    x = np.linspace(-limite, limite, _PONTOS)
    y = dist.pdf(x)
    ymax = float(y.max())

    # Curva de densidade teórica
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name=f"Densidade H₀ ({rotulo_teste})",
            line=dict(color=COR_CURVA, width=2),
            legendgroup=f"dens_{col}",
            hoverinfo="x+y",
        ),
        row=1,
        col=col,
    )

    # Região de rejeição bilateral (|x| >= crítico)
    # Cauda esquerda
    x_esq_rej = x[x <= -critico]
    y_esq_rej = y[x <= -critico]
    if len(x_esq_rej) > 0:
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([[x_esq_rej[0]], x_esq_rej, [x_esq_rej[-1]]]),
                y=np.concatenate([[0], y_esq_rej, [0]]),
                fill="tozeroy",
                fillcolor="rgba(230, 159, 0, 0.45)",
                line=dict(width=0),
                mode="none",
                showlegend=False,
                legendgroup=f"rej_{col}",
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )

    # Cauda direita (com legenda)
    x_dir_rej = x[x >= critico]
    y_dir_rej = y[x >= critico]
    if len(x_dir_rej) > 0:
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([[x_dir_rej[0]], x_dir_rej, [x_dir_rej[-1]]]),
                y=np.concatenate([[0], y_dir_rej, [0]]),
                fill="tozeroy",
                fillcolor="rgba(230, 159, 0, 0.45)",
                line=dict(width=0),
                mode="none",
                name=f"Rejeição (α = {alpha:g})",
                legendgroup=f"rej_{col}",
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )

    # Área do p-valor bilateral (|x| >= |observada|)
    obs_abs = abs(observada)
    # Cauda esquerda p-valor
    x_esq_p = x[x <= -obs_abs]
    y_esq_p = y[x <= -obs_abs]
    if len(x_esq_p) > 0:
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([[x_esq_p[0]], x_esq_p, [x_esq_p[-1]]]),
                y=np.concatenate([[0], y_esq_p, [0]]),
                fill="tozeroy",
                fillcolor="rgba(86, 180, 233, 0.55)",
                line=dict(width=0),
                mode="none",
                showlegend=False,
                legendgroup=f"pval_{col}",
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )

    # Cauda direita p-valor (com legenda)
    x_dir_p = x[x >= obs_abs]
    y_dir_p = y[x >= obs_abs]
    if len(x_dir_p) > 0:
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([[x_dir_p[0]], x_dir_p, [x_dir_p[-1]]]),
                y=np.concatenate([[0], y_dir_p, [0]]),
                fill="tozeroy",
                fillcolor="rgba(86, 180, 233, 0.55)",
                line=dict(width=0),
                mode="none",
                name=f"p-valor = {p_valor:.4g} (área das duas caudas)",
                legendgroup=f"pval_{col}",
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )

    # Linhas críticas ±critico
    for c_val in (-critico, critico):
        fig.add_trace(
            go.Scatter(
                x=[c_val, c_val],
                y=[0, ymax * 0.95],
                mode="lines",
                line=dict(color=COR_REJEICAO, width=1.5, dash="dash"),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )

    # Anotação do valor crítico
    fig.add_annotation(
        x=critico,
        y=ymax * 0.5,
        text=f"±{critico:.3f}",
        showarrow=False,
        xanchor="left",
        font=dict(color=COR_REJEICAO, size=11),
        row=1,
        col=col,
    )

    # Linha da estatística observada
    fig.add_trace(
        go.Scatter(
            x=[observada, observada],
            y=[0, ymax * 1.02],
            mode="lines",
            name=f"Observada = {observada:.3f}",
            line=dict(color=COR_OBSERVADA, width=2.5),
            legendgroup=f"obs_{col}",
        ),
        row=1,
        col=col,
    )

    # Limites do eixo x e y
    fig.update_xaxes(range=[-limite, limite], row=1, col=col)
    fig.update_yaxes(range=[0, ymax * 1.08], row=1, col=col)


def figura_g2_plotly(
    resultado_welch: dict,
    resultado_mw: dict,
    alpha: float = 0.05,
) -> go.Figure:
    """Monta a figura G2 interativa com dois painéis em Plotly.

    Args:
        resultado_welch: dict com estatistica (t), gl e p_valor.
        resultado_mw: dict com estatistica (z) e p_valor.
        alpha: nível de significância bicaudal (default: 0.05).

    Returns:
        plotly.graph_objects.Figure com layout padronizado.
    """
    _validar(resultado_welch, resultado_mw, alpha)
    res_w = copy.deepcopy(resultado_welch)
    res_m = copy.deepcopy(resultado_mw)

    gl = float(res_w["gl"])
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Welch: t de Student (gl = {gl:.1f})",
            "Mann-Whitney: normal padrão",
        ),
        horizontal_spacing=0.1,
    )

    _adicionar_painel(
        fig=fig,
        dist=stats.t(gl),
        observada=float(res_w["estatistica"]),
        p_valor=float(res_w["p_valor"]),
        alpha=alpha,
        rotulo_teste="Welch",
        col=1,
    )

    _adicionar_painel(
        fig=fig,
        dist=stats.norm(),
        observada=float(res_m["estatistica"]),
        p_valor=float(res_m["p_valor"]),
        alpha=alpha,
        rotulo_teste="Mann-Whitney",
        col=2,
    )

    fig.update_layout(
        title=dict(
            text="G2 — Distribuição da estatística de teste sob H0",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        **LAYOUT_BASE_PLOTLY,
    )

    # Rótulos dos eixos com nomes e unidades
    fig.update_xaxes(title_text="Estatística t (adimensional)", row=1, col=1)
    fig.update_yaxes(title_text="Densidade de probabilidade", row=1, col=1)

    fig.update_xaxes(title_text="Estatística z (adimensional)", row=1, col=2)
    fig.update_yaxes(title_text="Densidade de probabilidade", row=1, col=2)

    return fig


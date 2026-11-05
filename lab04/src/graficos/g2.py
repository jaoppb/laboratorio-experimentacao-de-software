"""G2 — distribuição da estatística de teste sob H0 (Welch e Mann-Whitney).

Função pura: devolve uma ``Figure`` criada pela API orientada a objetos
(sem pyplot, sem estado global, sem ``show`` e sem salvar em disco).
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from scipy import stats

# Paleta de Okabe-Ito (acessível a daltonismo); meios-tons que se leem em
# fundo claro e escuro.
COR_CURVA = "#888888"
COR_REJEICAO = "#E69F00"
COR_P_VALOR = "#0072B2"
COR_OBSERVADA = "#D55E00"

_PONTOS = 1200
_COBERTURA_CAUDA = 0.9995  # a faixa cobre ao menos este quantil da distribuição


def _validar(resultado_welch: dict, resultado_mw: dict, alpha: float) -> None:
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


def _preencher_caudas(ax: Axes, x, y, corte: float, rotulo: str, gid: str, **estilo) -> None:
    """Sombreia as duas caudas |x| >= corte; só a cauda direita entra na legenda."""
    for lado, rot in ((x >= corte, rotulo), (x <= -corte, None)):
        ax.fill_between(x, y, where=lado, label=rot, gid=gid, **estilo)


def _painel(
    ax: Axes, dist, observada: float, p_valor: float, alpha: float,
    titulo: str, rotulo_x: str,
) -> None:
    critico = float(dist.ppf(1.0 - alpha / 2.0))
    limite = 1.15 * max(abs(observada), critico, float(dist.ppf(_COBERTURA_CAUDA)))
    x = np.linspace(-limite, limite, _PONTOS)
    y = dist.pdf(x)

    ax.plot(x, y, color=COR_CURVA, lw=1.8, label="Densidade sob H0")

    # Região de rejeição (|x| >= crítico): preenchimento sólido.
    _preencher_caudas(
        ax, x, y, critico, f"Rejeição (α = {alpha:g})", "area_rejeicao",
        color=COR_REJEICAO, alpha=0.45, lw=0,
    )
    # p-valor bilateral (|x| >= |observada|): apenas hachura, para se
    # distinguir da região de rejeição mesmo quando se sobrepõem.
    _preencher_caudas(
        ax, x, y, abs(observada),
        f"p-valor = {p_valor:.4g} (área das duas caudas)", "area_p_valor",
        facecolor="none", edgecolor=COR_P_VALOR, hatch="///", lw=0,
    )

    ax.axvline(observada, color=COR_OBSERVADA, lw=2, label=f"Observada = {observada:.3f}")
    for v in (-critico, critico):
        ax.axvline(v, color=COR_REJEICAO, lw=1, ls="--")
    ymax = float(y.max())
    ax.annotate(
        f"±{critico:.3f}", xy=(critico, ymax * 0.5), xytext=(4, 0),
        textcoords="offset points", color=COR_REJEICAO, fontsize=9,
    )
    ax.set_xlim(-limite, limite)
    ax.set_ylim(0, ymax * 1.05)
    ax.set_title(titulo)
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel("Densidade")
    ax.legend(loc="upper left", fontsize=8, frameon=False)


def figura_g2(
    resultado_welch: dict,
    resultado_mw: dict,
    alpha: float = 0.05,
    figsize: tuple[float, float] = (11, 4.5),
) -> Figure:
    """Monta a figura G2 com dois painéis (Welch e Mann-Whitney) sob H0.

    ``resultado_welch`` precisa de ``estatistica`` (t), ``gl`` e ``p_valor``;
    ``resultado_mw`` precisa de ``estatistica`` (z) e ``p_valor``. Os dicts
    não são alterados. A região de rejeição e a área do p-valor são bilaterais;
    resultados com ``alternativa`` unilateral são recusados (``ValueError``).
    Com ``gl`` muito baixo a faixa do eixo x fica larga (caudas pesadas).
    """
    _validar(resultado_welch, resultado_mw, alpha)
    gl = float(resultado_welch["gl"])
    fig = Figure(figsize=figsize, layout="constrained")
    ax_t, ax_z = fig.subplots(1, 2)
    _painel(
        ax_t, stats.t(gl), float(resultado_welch["estatistica"]),
        float(resultado_welch["p_valor"]), alpha,
        f"Welch: t de Student (gl = {gl:.1f})", "Estatística t",
    )
    _painel(
        ax_z, stats.norm(), float(resultado_mw["estatistica"]),
        float(resultado_mw["p_valor"]), alpha,
        "Mann-Whitney: normal padrão", "Estatística z",
    )
    fig.suptitle("G2 — Distribuição da estatística sob H0")
    return fig

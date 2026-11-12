"""Seletor de α (botões Plotly) compartilhado por G3 e G4.

A figura guarda os traços dos dois níveis (os do segundo começam ocultos) e
UMA linha horizontal de referência (``shapes[0]`` + ``annotations[0]``, criada
por ``add_hline``). O botão escolhe quais traços aparecem e move a linha.
"""

from __future__ import annotations

from collections.abc import Callable

import plotly.graph_objects as go


def adicionar_seletor(
    fig: go.Figure,
    n_por_alfa: int,
    alfas: tuple[float, float],
    texto_linha: Callable[[float], str],
    limite_y: tuple[float, float],
) -> None:
    """Liga os dois conjuntos de ``n_por_alfa`` traços a botões de α.

    Args:
        alfas: (α principal, α alternativo); os traços estão nessa ordem.
        texto_linha: rótulo da linha de referência para um α.
        limite_y: limite superior do eixo y (%) para cada α.
    """
    if len(fig.data) != 2 * n_por_alfa:
        raise ValueError("a figura deve ter n_por_alfa traços por α")
    botoes = []
    for i, alfa in enumerate(alfas):
        visivel = [j // n_por_alfa == i for j in range(len(fig.data))]
        botoes.append(
            dict(
                label=f"α = {alfa:g}".replace(".", ","),
                method="update",
                args=[
                    {"visible": visivel},
                    {
                        "shapes[0].y0": alfa * 100.0,
                        "shapes[0].y1": alfa * 100.0,
                        "annotations[0].y": alfa * 100.0,
                        "annotations[0].text": texto_linha(alfa),
                        "yaxis.range": [0, limite_y[i]],
                    },
                ],
            )
        )
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                buttons=botoes,
                x=1.0,
                xanchor="right",
                y=1.0,
                yanchor="bottom",
                pad=dict(b=6),
            )
        ],
        margin=dict(t=90),
    )

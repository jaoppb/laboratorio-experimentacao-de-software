"""Seletor de α (botões Plotly) compartilhado por G3 e G4.

A figura guarda os traços dos dois níveis (os do segundo começam ocultos) e
UMA linha horizontal de referência (criada por ``add_hline``). O botão escolhe
quais traços aparecem e move a linha.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go


def validar_alfas(alfa: float, alt: pd.DataFrame | None, alfa_alt: float | None) -> None:
    """Valida α e o par (dados alternativos, α alternativo), que vêm juntos."""
    if not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa deve estar em (0, 1); recebido {alfa!r}")
    if (alt is None) != (alfa_alt is None):
        raise ValueError("os dados alternativos e alfa_alt devem ser dados juntos")
    if alfa_alt is not None and not 0.0 < alfa_alt < 1.0:
        raise ValueError(f"alfa_alt deve estar em (0, 1); recebido {alfa_alt!r}")


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

    Raises:
        ValueError: se a figura não tiver 2 × ``n_por_alfa`` traços e exatamente
            uma linha de referência com rótulo.
    """
    if len(fig.data) != 2 * n_por_alfa:
        raise ValueError("a figura deve ter n_por_alfa traços por α")
    if len(fig.layout.shapes) != 1 or len(fig.layout.annotations) != 1:
        raise ValueError("a figura deve ter só a linha de referência (add_hline)")
    botoes = []
    for i, alfa in enumerate(alfas):
        visivel = [j // n_por_alfa == i for j in range(len(fig.data))]
        botoes.append(
            dict(
                label=f"Nível α = {alfa:g}".replace(".", ","),
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
        # Botões à esquerda, numa faixa própria acima do gráfico e abaixo do título.
        title=dict(y=0.98, yanchor="top"),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                buttons=botoes,
                x=0.0,
                xanchor="left",
                y=1.0,
                yanchor="bottom",
                pad=dict(b=6),
            )
        ],
        margin=dict(t=100),
    )

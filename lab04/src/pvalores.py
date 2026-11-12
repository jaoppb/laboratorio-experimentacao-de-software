"""p-valores das simulações Q1, Q2 e Q3, guardados em ``.npz`` (float64).

Cada arquivo tem um vetor de p-valores por (cenário, razão entre medianas,
teste). Com eles, a taxa de rejeição em qualquer α sai de ``mean(p < α)``, sem
simular de novo.
"""

from __future__ import annotations

import numbers
from pathlib import Path

import numpy as np
import pandas as pd


def chave(cenario: str, razao: float, teste: str) -> str:
    """Nome do vetor no ``.npz`` (Q1 e erro tipo I de Q3 usam razão 1,0)."""
    return f"{cenario}__{float(razao)!r}__{teste}"


def salvar(caminho: Path | str, p_valores: dict[str, np.ndarray]) -> None:
    """Grava os vetores, comprimidos, em float64."""
    np.savez_compressed(
        caminho, **{k: np.asarray(v, dtype=np.float64) for k, v in p_valores.items()}
    )


def carregar(caminho: Path | str) -> dict[str, np.ndarray]:
    """Lê todos os vetores do ``.npz``."""
    with np.load(caminho) as arq:
        return {k: arq[k] for k in arq.files}


def recalcular_taxas(
    df: pd.DataFrame, p_valores: dict[str, np.ndarray], alfa: float
) -> pd.DataFrame:
    """Cópia de ``df`` com ``taxa_rejeicao`` e ``alfa`` recalculados em ``alfa``.

    ``df`` tem ``cenario, teste, n_rep`` e, no poder, ``razao_medianas``.

    Raises:
        ValueError: ``alfa`` fora de (0, 1) ou ``n_rep`` diferente do vetor guardado.
        KeyError: linha sem p-valores guardados.
    """
    if isinstance(alfa, bool) or not isinstance(alfa, numbers.Real) or not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa deve estar em (0, 1); recebido {alfa!r}")
    razoes = df["razao_medianas"] if "razao_medianas" in df else [1.0] * len(df)
    taxas = []
    for cenario, teste, razao, n_rep in zip(df["cenario"], df["teste"], razoes, df["n_rep"]):
        p = p_valores[chave(cenario, razao, teste)]
        if len(p) != int(n_rep):
            raise ValueError(f"n_rep={n_rep} difere dos {len(p)} p-valores de {cenario}/{teste}")
        taxas.append(float(np.mean(p < alfa)))
    return df.assign(taxa_rejeicao=taxas, alfa=float(alfa))

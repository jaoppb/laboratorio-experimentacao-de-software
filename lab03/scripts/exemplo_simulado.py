"""Exemplo didático da simulação: UM conjunto lognormal com Welch e Mann-Whitney.

Uso (a partir de ``lab03/``): ``uv run python scripts/exemplo_simulado.py``.
Gera ``dados/simulado/exemplo.csv`` (formato longo) e
``dados/simulado/exemplo_resultado.json`` (entrada do gráfico G2). A saída é
determinística: duas execuções produzem arquivos idênticos byte a byte.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.simulacao import gerar_dados  # noqa: E402
from src.testes import aplicar_mannwhitney, aplicar_welch  # noqa: E402

SEMENTE = 42
N_A = 30
N_B = 30
MEDIANA_A = 10.0
MEDIANA_B = 14.0
# Sigmas distintos de propósito: com formas diferentes, médias e medianas
# divergem; o Mann-Whitney responde à dominância estocástica, não a nenhuma das duas.
SIGMA_A = 0.8
SIGMA_B = 0.5
ALPHA = 0.05

DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"


def executar(diretorio: Path = DIRETORIO_SAIDA) -> dict:
    """Gera o conjunto, aplica os dois testes e grava CSV e JSON."""
    rng = np.random.default_rng(SEMENTE)
    a, b = gerar_dados(rng, N_A, N_B, MEDIANA_A, MEDIANA_B, SIGMA_A, SIGMA_B)

    resultado = {
        "semente": SEMENTE,
        "parametros": {
            "n_a": N_A,
            "n_b": N_B,
            "mediana_a": MEDIANA_A,
            "mediana_b": MEDIANA_B,
            "sigma_a": SIGMA_A,
            "sigma_b": SIGMA_B,
            "alpha": ALPHA,
        },
        "welch": aplicar_welch(a, b),
        "mannwhitney": aplicar_mannwhitney(a, b),
        "medianas_amostrais": {"A": float(np.median(a)), "B": float(np.median(b))},
        "medias_amostrais": {"A": float(a.mean()), "B": float(b.mean())},
    }

    diretorio.mkdir(parents=True, exist_ok=True)
    with open(diretorio / "exemplo.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(["grupo", "valor"])
        for grupo, valores in (("A", a), ("B", b)):
            for v in valores:
                escritor.writerow([grupo, repr(float(v))])
    with open(diretorio / "exemplo_resultado.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    return resultado


if __name__ == "__main__":
    executar()

"""Motor Monte Carlo: repete a simulação e guarda os p-valores dos dois testes."""

from __future__ import annotations

import numbers
from dataclasses import dataclass

import numpy as np

from src.simulacao import gerar_dados
from src.testes import aplicar_mannwhitney, aplicar_welch

N_REP_PADRAO = 10_000


@dataclass(frozen=True)
class ResultadoMonteCarlo:
    """p-valores por repetição, alinhados índice a índice entre os testes."""

    p_welch: np.ndarray
    p_mannwhitney: np.ndarray

    def taxa_rejeicao(self, alfa: float = 0.05) -> dict[str, float]:
        """Fração de p-valores < ``alfa`` para cada teste."""
        if (
            isinstance(alfa, bool)
            or not isinstance(alfa, numbers.Real)
            or not 0.0 < alfa < 1.0
        ):
            raise ValueError(f"alfa deve estar em (0, 1), recebido {alfa!r}")
        return {
            "welch": float(np.mean(self.p_welch < alfa)),
            "mannwhitney": float(np.mean(self.p_mannwhitney < alfa)),
        }


def executar_montecarlo(
    rng: np.random.Generator,
    n_a: int,
    n_b: int,
    mediana_a: float,
    mediana_b: float,
    sigma_a: float,
    sigma_b: float,
    n_rep: int = N_REP_PADRAO,
    alternativa: str = "two-sided",
) -> ResultadoMonteCarlo:
    """Repete ``n_rep`` vezes: gera dados lognormais e aplica Welch e Mann-Whitney.

    O ``rng`` é o único estado consumido, então a mesma semente reproduz o
    resultado. Erros dos testes (``ValueError``) não são engolidos.

    Raises:
        ValueError: se ``n_rep`` não for inteiro >= 1 ou parâmetros inválidos.
    """
    if (
        isinstance(n_rep, bool)
        or not isinstance(n_rep, numbers.Integral)
        or n_rep < 1
    ):
        raise ValueError(f"n_rep deve ser um inteiro >= 1, recebido {n_rep!r}")
    n_rep = int(n_rep)
    p_welch = np.empty(n_rep)
    p_mw = np.empty(n_rep)
    for i in range(n_rep):
        a, b = gerar_dados(rng, n_a, n_b, mediana_a, mediana_b, sigma_a, sigma_b)
        p_welch[i] = aplicar_welch(a, b, alternativa)["p_valor"]
        p_mw[i] = aplicar_mannwhitney(a, b, alternativa)["p_valor"]
    return ResultadoMonteCarlo(p_welch=p_welch, p_mannwhitney=p_mw)

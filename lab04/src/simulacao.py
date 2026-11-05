"""Geração de dados sintéticos lognormais para a simulação (Sprint 1)."""

import math
import numbers

import numpy as np


def _validar_n(nome: str, valor) -> None:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, numbers.Integral)
        or valor < 2
    ):
        raise ValueError(f"{nome} deve ser um inteiro >= 2, recebido {valor!r}")


def _validar_positivo(nome: str, valor) -> None:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, numbers.Real)
        or not math.isfinite(valor)
        or valor <= 0
    ):
        raise ValueError(f"{nome} deve ser um número finito > 0, recebido {valor!r}")


def gerar_dados(
    rng: np.random.Generator,
    n_a: int,
    n_b: int,
    mediana_a: float,
    mediana_b: float,
    sigma_a: float,
    sigma_b: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Gera duas amostras lognormais independentes.

    Cada grupo segue LogNormal(mu, sigma), em que ``sigma`` é o desvio padrão
    do logaritmo dos dados e ``mu = ln(mediana)``, pois a mediana teórica de
    uma lognormal é ``exp(mu)``.

    Args:
        rng: gerador de números aleatórios (único estado consumido).
        n_a, n_b: tamanhos das amostras (inteiros >= 2).
        mediana_a, mediana_b: medianas teóricas (> 0 e finitas).
        sigma_a, sigma_b: desvios do log (> 0 e finitos).

    Returns:
        Tupla ``(a, b)`` de arrays float64 com tamanhos ``n_a`` e ``n_b``.

    Raises:
        ValueError: se algum parâmetro for inválido.
    """
    _validar_n("n_a", n_a)
    _validar_n("n_b", n_b)
    _validar_positivo("mediana_a", mediana_a)
    _validar_positivo("mediana_b", mediana_b)
    _validar_positivo("sigma_a", sigma_a)
    _validar_positivo("sigma_b", sigma_b)

    a = rng.lognormal(mean=np.log(mediana_a), sigma=sigma_a, size=int(n_a))
    b = rng.lognormal(mean=np.log(mediana_b), sigma=sigma_b, size=int(n_b))
    return a, b

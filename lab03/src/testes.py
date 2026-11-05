"""Testes de hipótese da simulação: t de Welch e Mann-Whitney.

Ambas as funções são vetorizadas (sem pandas, sem loops Python, sem
reamostragem) porque rodam ~10.000x na Sprint 2. Não mutam as entradas,
não imprimem e não tocam em estado global/sementes.

Ordem de grandeza medida (n = 30..200 por grupo): ~0,1 ms por chamada de
``aplicar_welch`` e ~0,3 ms por ``aplicar_mannwhitney``.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

_ALTERNATIVAS = ("two-sided", "less", "greater")


def _validar(a, b, alternativa: str) -> tuple[np.ndarray, np.ndarray]:
    """Converte para float sem copiar quando possível e valida as entradas."""
    if alternativa not in _ALTERNATIVAS:
        raise ValueError(
            f"alternativa inválida: {alternativa!r}; use uma de {_ALTERNATIVAS}"
        )
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    for nome, x in (("a", a), ("b", b)):
        if x.ndim != 1:
            raise ValueError(f"o grupo {nome} deve ser unidimensional")
        if x.size < 2:
            raise ValueError(f"o grupo {nome} precisa de ao menos 2 observações")
        if not np.isfinite(x).all():
            raise ValueError(f"o grupo {nome} contém NaN ou infinito")
    return a, b


def _p_da_normal(z: float, alternativa: str) -> float:
    """p-valor de uma estatística z padrão conforme a alternativa."""
    if alternativa == "two-sided":
        return float(2.0 * stats.norm.sf(abs(z)))
    if alternativa == "greater":
        return float(stats.norm.sf(z))
    return float(stats.norm.cdf(z))


def aplicar_welch(a, b, alternativa: str = "two-sided") -> dict:
    """Teste t de Welch (variâncias desiguais) para a diferença de médias.

    Retorna dict com:
      - ``estatistica``: t de Welch ((média_a - média_b) / erro-padrão);
      - ``p_valor``: p-valor conforme ``alternativa``;
      - ``tamanho_efeito``: d de Cohen com desvio combinado
        ``sqrt((s_a² + s_b²) / 2)``; positivo = média de ``a`` maior;
      - ``alternativa``: "two-sided", "less" ou "greater" (a vs b);
      - ``gl``: graus de liberdade de Welch-Satterthwaite.

    Levanta ``ValueError`` para menos de 2 observações por grupo, NaN/inf,
    alternativa desconhecida ou variância zero nos dois grupos (o teste
    fica indefinido).
    """
    a, b = _validar(a, b, alternativa)
    n_a, n_b = a.size, b.size
    var_a = float(a.var(ddof=1))
    var_b = float(b.var(ddof=1))
    if var_a == 0.0 and var_b == 0.0:
        raise ValueError("variância zero nos dois grupos: teste de Welch indefinido")
    ep_a, ep_b = var_a / n_a, var_b / n_b
    ep = np.sqrt(ep_a + ep_b)
    dif = float(a.mean() - b.mean())
    t = dif / ep
    gl = float((ep_a + ep_b) ** 2 / (ep_a**2 / (n_a - 1) + ep_b**2 / (n_b - 1)))
    if alternativa == "two-sided":
        p = 2.0 * stats.t.sf(abs(t), gl)
    elif alternativa == "greater":
        p = stats.t.sf(t, gl)
    else:
        p = stats.t.cdf(t, gl)
    return {
        "estatistica": float(t),
        "p_valor": float(p),
        "tamanho_efeito": float(dif / np.sqrt((var_a + var_b) / 2.0)),
        "alternativa": alternativa,
        "gl": gl,
    }


def aplicar_mannwhitney(a, b, alternativa: str = "two-sided") -> dict:
    """Teste de Mann-Whitney U (aproximação normal com correção de empates).

    ATENÇÃO: compara POSTOS, isto é, a dominância estocástica
    P(X>Y) + ½·P(X=Y); NÃO é um teste de medianas (só equivale a isso sob
    formas idênticas de distribuição).

    Retorna dict com:
      - ``estatistica``: z da aproximação normal, com correção de empates e
        de continuidade (0,5); positivo = ``a`` tende a ser maior;
      - ``p_valor``: calculado a partir desse mesmo z;
      - ``tamanho_efeito``: correlação rank-biserial
        ``r = 2·U_a/(n_a·n_b) - 1`` em [-1, 1]; positivo = ``a`` tende a
        ser maior que ``b``;
      - ``alternativa``: "two-sided", "less" ou "greater" (a vs b);
      - ``u``: estatística U de ``a``.

    Levanta ``ValueError`` para menos de 2 observações por grupo, NaN/inf,
    alternativa desconhecida ou todos os valores idênticos (variância do
    U nula).
    """
    a, b = _validar(a, b, alternativa)
    n_a, n_b = a.size, b.size
    n = n_a + n_b
    postos = stats.rankdata(np.concatenate((a, b)))
    u = float(postos[:n_a].sum() - n_a * (n_a + 1) / 2.0)
    _, contagens = np.unique(postos, return_counts=True)
    corr_empates = float((contagens**3 - contagens).sum()) / (n * (n - 1))
    var_u = n_a * n_b / 12.0 * ((n + 1) - corr_empates)
    if var_u <= 0.0:
        raise ValueError("todos os valores são idênticos: Mann-Whitney indefinido")
    dif = u - n_a * n_b / 2.0
    if alternativa == "two-sided":
        corr = -0.5 * np.sign(dif)
    elif alternativa == "greater":
        corr = -0.5
    else:
        corr = 0.5
    z = (dif + corr) / np.sqrt(var_u)
    return {
        "estatistica": float(z),
        "p_valor": _p_da_normal(float(z), alternativa),
        "tamanho_efeito": float(2.0 * u / (n_a * n_b) - 1.0),
        "alternativa": alternativa,
        "u": u,
    }

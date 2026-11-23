"""Análise dos dados do piloto (#167): checa o pipeline e a suficiência da amostra.

Aplica ao piloto a análise planejada em ``docs/plano_analise.md`` (#165):

- M1 (TTFB): só repetições ``warm`` (n = 9 por tela e versão), com mediana, IQR,
  teste U de Mann-Whitney bicaudal (p bruto e ajustado por Holm nas 4 telas), Δ de
  Cliff com IC bootstrap e razão entre medianas. A repetição ``cold`` (n = 1 por
  grupo) é só descrita, sem teste;
- suficiência da amostra: n por grupo necessário para poder de 80% (α = 0,05),
  simulado por reamostragem do piloto, comparado ao N planejado (80);
- M3 (erros HTTP): proporção com IC de Wilson e teste de Fisher (ou Z de duas
  proporções quando as contagens esperadas são >= 5);
- M4 (axe-core): contagens por severidade e Wilcoxon pareado entre as telas, quando
  houver diferenças.

Os resultados valem como verificação do pipeline e estimativa provisória: com
n = 9 e a ordem fixa 4.5 -> 5.3 (P13) o piloto não permite concluir sobre o sentido
da diferença entre as versões.

Uso::

    python scripts/analisar_piloto.py [--dir dados/piloto] [--saida ARQUIVO]

Por padrão grava ``<dir>/analise_piloto.json``.

Sai com código 0 e grava o JSON, ou 1 se os dados do piloto não passam no validador.

M3 conta apenas respostas 5xx: um timeout aborta a coleta (``ErroColeta``) e não chega
ao CSV.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import scipy
from scipy import stats

from coleta_piloto import DIR_DADOS_PILOTO, TELAS, VERSOES
from validar_piloto import ler_csv, tipar_linha, validar_diretorio

ALFA = 0.05
PODER_ALVO = 0.80
N_PLANEJADO = 80  # repetições por tela e versão previstas para a S02 (#165 §5)
GRADE_N = (10, 20, 30, 40, 60, 80, 100, 120, 160, 200)
SEMENTE_PADRAO = 167
N_BOOTSTRAP_PADRAO = 10_000
N_SIMULACOES_PADRAO = 2_000
NIVEL_IC = 0.95
VERSAO_BASE, VERSAO_NOVA = VERSOES  # 4.5 (referência) e 5.3 (tratamento)
ARQUIVO_SAIDA = "analise_piloto.json"
SEVERIDADES = ("critical", "serious", "moderate", "minor", "indefinido")


# --------------------------------------------------------------------------- #
# Estatísticas elementares
# --------------------------------------------------------------------------- #


def delta_cliff(base: Sequence[float], nova: Sequence[float]) -> float:
    """Δ de Cliff: ``(#(nova > base) - #(nova < base)) / (n_nova * n_base)``."""
    a = np.asarray(base, dtype=float)
    b = np.asarray(nova, dtype=float)
    return float(np.sign(b[:, None] - a[None, :]).mean())


def classificar_cliff(d: float) -> str:
    """Magnitude pelos limiares de Romano et al. (2006), como em #165 §4.1."""
    absoluto = abs(d)
    if absoluto < 0.147:
        return "desprezível"
    if absoluto < 0.33:
        return "pequeno"
    if absoluto < 0.474:
        return "médio"
    return "grande"


def ic_bootstrap_cliff(
    base: Sequence[float],
    nova: Sequence[float],
    rng: np.random.Generator,
    n_bootstrap: int = N_BOOTSTRAP_PADRAO,
    nivel: float = NIVEL_IC,
) -> tuple[float, float]:
    """IC percentil do Δ de Cliff, reamostrando cada grupo com reposição."""
    a = np.asarray(base, dtype=float)
    b = np.asarray(nova, dtype=float)
    sa = rng.choice(a, size=(n_bootstrap, a.size))
    sb = rng.choice(b, size=(n_bootstrap, b.size))
    deltas = np.sign(sb[:, :, None] - sa[:, None, :]).mean(axis=(1, 2))
    cauda = (1 - nivel) / 2 * 100
    inferior, superior = np.percentile(deltas, [cauda, 100 - cauda])
    return float(inferior), float(superior)


def mann_whitney(base: Sequence[float], nova: Sequence[float]) -> dict[str, float]:
    """U de Mann-Whitney bicaudal (``method='auto'``: exato sem empates e n pequeno)."""
    resultado = stats.mannwhitneyu(base, nova, alternative="two-sided", method="auto")
    return {"u": float(resultado.statistic), "p": float(resultado.pvalue)}


def ajustar_holm(pvalores: Sequence[float]) -> list[float]:
    """Ajuste de Holm-Bonferroni, na ordem original dos p-valores."""
    m = len(pvalores)
    ordem = sorted(range(m), key=lambda i: pvalores[i])
    ajustados = [0.0] * m
    maximo = 0.0
    for posicao, indice in enumerate(ordem):
        maximo = max(maximo, min(1.0, (m - posicao) * pvalores[indice]))
        ajustados[indice] = maximo
    return ajustados


def wilson(k: int, n: int, nivel: float = NIVEL_IC) -> tuple[float, float]:
    """IC de Wilson para uma proporção ``k/n``."""
    z = float(stats.norm.ppf(1 - (1 - nivel) / 2))
    p = k / n
    denominador = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denominador
    margem = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominador
    return max(0.0, centro - margem), min(1.0, centro + margem)


def comparar_proporcoes(k_base: int, n_base: int, k_nova: int, n_nova: int) -> dict[str, Any]:
    """Fisher exato se alguma contagem esperada for < 5; senão Z de duas proporções."""
    tabela = [[k_base, n_base - k_base], [k_nova, n_nova - k_nova]]
    total = n_base + n_nova
    erros = k_base + k_nova
    esperadas = [
        n_grupo * coluna / total
        for n_grupo in (n_base, n_nova)
        for coluna in (erros, total - erros)
    ]
    if min(esperadas) < 5:
        _, p = stats.fisher_exact(tabela, alternative="two-sided")
        return {"teste": "fisher_exato", "p": float(p)}
    pooled = erros / total
    erro_padrao = math.sqrt(pooled * (1 - pooled) * (1 / n_base + 1 / n_nova))
    z = (k_nova / n_nova - k_base / n_base) / erro_padrao
    return {"teste": "z_duas_proporcoes", "p": float(2 * stats.norm.sf(abs(z)))}


def p_minimo_wilcoxon(n_pares: int) -> float:
    """Menor p bicaudal exato do Wilcoxon pareado com ``n_pares`` diferenças não nulas."""
    return 2 / 2**n_pares if n_pares > 0 else 1.0


# --------------------------------------------------------------------------- #
# Suficiência da amostra
# --------------------------------------------------------------------------- #


def simular_poder(
    base: Sequence[float],
    nova: Sequence[float],
    n: int,
    rng: np.random.Generator,
    n_simulacoes: int = N_SIMULACOES_PADRAO,
    alfa: float = ALFA,
) -> float:
    """Poder do Mann-Whitney com ``n`` por grupo, reamostrando os dois grupos do piloto."""
    sa = rng.choice(np.asarray(base, dtype=float), size=(n_simulacoes, n))
    sb = rng.choice(np.asarray(nova, dtype=float), size=(n_simulacoes, n))
    p = stats.mannwhitneyu(
        sa, sb, alternative="two-sided", method="asymptotic", axis=1
    ).pvalue
    return float(np.mean(p < alfa))  # p = NaN (grupos idênticos) não rejeita H0


def estimar_n_necessario(
    base: Sequence[float],
    nova: Sequence[float],
    rng: np.random.Generator,
    n_simulacoes: int = N_SIMULACOES_PADRAO,
    grade: Sequence[int] = GRADE_N,
) -> dict[str, Any]:
    """Menor ``n`` da grade com poder >= 80%, mais a curva de poder simulada.

    O N planejado entra na grade, de modo que ``poder_no_n_planejado`` é um ponto da
    própria curva.
    """
    curva = {
        n: simular_poder(base, nova, n, rng, n_simulacoes)
        for n in sorted({*grade, N_PLANEJADO})
    }
    n_necessario = next((n for n, poder in curva.items() if poder >= PODER_ALVO), None)
    return {
        "n_necessario": n_necessario,
        "poder_por_n": {str(n): round(poder, 3) for n, poder in curva.items()},
        "poder_no_n_planejado": round(curva[N_PLANEJADO], 3),
    }


def classificar_suficiencia(n_necessario: int | None, n_planejado: int = N_PLANEJADO) -> str:
    """``folgado`` (N planejado >= 2x o necessário), ``suficiente`` ou ``insuficiente``."""
    if n_necessario is None or n_necessario > n_planejado:
        return "insuficiente"
    if 2 * n_necessario <= n_planejado:
        return "folgado"
    return "suficiente"


# --------------------------------------------------------------------------- #
# Entrada de dados
# --------------------------------------------------------------------------- #


def ler_amostras(diretorio: Path) -> list[dict[str, Any]]:
    _, linhas = ler_csv(diretorio / "amostra_piloto.csv")
    return [tipar_linha(linha) for linha in linhas]


def ler_axe(diretorio: Path) -> dict[tuple[str, str], dict[str, Any]]:
    relatorios = {}
    for versao in VERSOES:
        for tela, _ in TELAS:
            caminho = diretorio / "axe" / f"{versao}_{tela}.json"
            relatorios[(versao, tela)] = json.loads(caminho.read_text(encoding="utf-8"))
    return relatorios


def _ttfb(amostras: list[dict[str, Any]], versao: str, tela: str, cache: str) -> list[float]:
    return [
        a["ttfb_ms"]
        for a in amostras
        if a["versao"] == versao and a["tela"] == tela and a["cache"] == cache
    ]


# --------------------------------------------------------------------------- #
# Análises por métrica
# --------------------------------------------------------------------------- #


def descrever(valores: Sequence[float]) -> dict[str, float | int]:
    arr = np.asarray(valores, dtype=float)
    q1, q2, q3 = np.percentile(arr, [25, 50, 75])
    return {
        "n": int(arr.size),
        "mediana_ms": round(float(q2), 2),
        "iqr_ms": round(float(q3 - q1), 2),
        "media_ms": round(float(arr.mean()), 2),
        "desvio_padrao_ms": round(float(arr.std(ddof=1)), 2) if arr.size > 1 else 0.0,
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
    }


def comparar_tela(
    base: Sequence[float],
    nova: Sequence[float],
    cold: dict[str, float],
    semente: int,
    indice_tela: int,
    n_bootstrap: int,
    n_simulacoes: int,
) -> dict[str, Any]:
    """M1 de uma tela: descritiva, Mann-Whitney, Δ de Cliff, suficiência e cold descritivo.

    O bootstrap e a simulação de poder usam fluxos aleatórios independentes, para que
    mudar ``n_bootstrap`` não altere a suficiência.
    """
    rng_bootstrap = np.random.default_rng([semente, indice_tela, 0])
    rng_poder = np.random.default_rng([semente, indice_tela, 1])
    warm = {VERSAO_BASE: descrever(base), VERSAO_NOVA: descrever(nova)}
    mediana_base = warm[VERSAO_BASE]["mediana_ms"]
    mediana_nova = warm[VERSAO_NOVA]["mediana_ms"]
    desvio_base = warm[VERSAO_BASE]["desvio_padrao_ms"]
    razao = mediana_nova / mediana_base
    d = delta_cliff(base, nova)
    inferior, superior = ic_bootstrap_cliff(base, nova, rng_bootstrap, n_bootstrap)
    estimativa = estimar_n_necessario(base, nova, rng_poder, n_simulacoes)
    return {
        "warm": warm,
        "razao_medianas": round(razao, 3),
        "variacao_percentual": round((razao - 1) * 100, 1),
        "razao_desvios": (
            round(warm[VERSAO_NOVA]["desvio_padrao_ms"] / desvio_base, 2) if desvio_base else None
        ),
        "mann_whitney": mann_whitney(base, nova),
        "delta_cliff": {
            "d": round(d, 3),
            "magnitude": classificar_cliff(d),
            "ic95": [round(inferior, 3), round(superior, 3)],
        },
        "suficiencia": {
            **estimativa,
            "faixa": classificar_suficiencia(estimativa["n_necessario"]),
        },
        "cold": {
            versao: {
                "ttfb_ms": valor,
                "razao_a_mediana_warm": round(valor / warm[versao]["mediana_ms"], 2),
            }
            for versao, valor in cold.items()
        },
    }


def analisar_ttfb(
    amostras: list[dict[str, Any]],
    semente: int = SEMENTE_PADRAO,
    n_bootstrap: int = N_BOOTSTRAP_PADRAO,
    n_simulacoes: int = N_SIMULACOES_PADRAO,
) -> dict[str, Any]:
    """M1: comparação 4.5 x 5.3 por tela, só com repetições warm (cold só descrito)."""
    telas: dict[str, Any] = {}
    for indice, (tela, _) in enumerate(TELAS):
        # o validador garante exatamente uma repetição cold por tela e versão
        cold = {}
        for versao in VERSOES:
            (cold[versao],) = _ttfb(amostras, versao, tela, "cold")
        telas[tela] = comparar_tela(
            _ttfb(amostras, VERSAO_BASE, tela, "warm"),
            _ttfb(amostras, VERSAO_NOVA, tela, "warm"),
            cold,
            semente,
            indice,
            n_bootstrap,
            n_simulacoes,
        )
    ajustados = ajustar_holm([t["mann_whitney"]["p"] for t in telas.values()])
    for tela, p_holm in zip(telas, ajustados):
        telas[tela]["mann_whitney"]["p_holm"] = p_holm
    return telas


def analisar_erros(amostras: list[dict[str, Any]]) -> dict[str, Any]:
    """M3: erro = status 5xx (timeouts abortam a coleta). Usa as 40 requisições por versão."""
    contagens = {}
    for versao in VERSOES:
        status = [a["status_http"] for a in amostras if a["versao"] == versao]
        k = sum(1 for s in status if s >= 500)
        inferior, superior = wilson(k, len(status))
        contagens[versao] = {
            "erros": k,
            "n": len(status),
            "proporcao": round(k / len(status), 4),
            "ic95_wilson": [round(inferior, 4), round(superior, 4)],
        }
    base, nova = contagens[VERSAO_BASE], contagens[VERSAO_NOVA]
    return {
        "por_versao": contagens,
        "comparacao": comparar_proporcoes(base["erros"], base["n"], nova["erros"], nova["n"]),
    }


def analisar_acessibilidade(
    relatorios: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """M4: contagens por tela e severidade e Wilcoxon pareado entre as 4 telas."""
    por_tela = {
        tela: {versao: relatorios[(versao, tela)]["total_violacoes"] for versao in VERSOES}
        for tela, _ in TELAS
    }
    severidade = {
        versao: {
            nivel: sum(
                relatorios[(versao, tela)]["por_impacto"].get(nivel, 0) for tela, _ in TELAS
            )
            for nivel in SEVERIDADES
        }
        for versao in VERSOES
    }
    diferencas = [
        valores[VERSAO_NOVA] - valores[VERSAO_BASE] for valores in por_tela.values()
    ]
    nao_nulas = [d for d in diferencas if d != 0]
    resultado: dict[str, Any] = {
        "violacoes_por_tela": por_tela,
        "violacoes_por_severidade": severidade,
        "pares_com_diferenca": len(nao_nulas),
        "p_minimo_wilcoxon": p_minimo_wilcoxon(len(nao_nulas)),
    }
    if nao_nulas:
        # pares nulos saem antes (método de Wilcoxon), o que mantém o teste exato em n pequeno
        teste = stats.wilcoxon(nao_nulas, alternative="two-sided")
        resultado["wilcoxon"] = {"aplicavel": True, "p": float(teste.pvalue)}
    else:
        resultado["wilcoxon"] = {
            "aplicavel": False,
            "motivo": "todas as diferenças pareadas são 0 (sem violações ou sem variação)",
        }
    return resultado


# --------------------------------------------------------------------------- #
# Orquestração e saída
# --------------------------------------------------------------------------- #


def analisar(
    diretorio: Path = DIR_DADOS_PILOTO,
    semente: int = SEMENTE_PADRAO,
    n_bootstrap: int = N_BOOTSTRAP_PADRAO,
    n_simulacoes: int = N_SIMULACOES_PADRAO,
) -> dict[str, Any]:
    """Valida os dados do piloto e devolve a análise completa (levanta ValueError se inválidos)."""
    problemas = validar_diretorio(diretorio)
    if problemas:
        raise ValueError("Dados do piloto inválidos:\n" + "\n".join(problemas))
    amostras = ler_amostras(diretorio)
    return {
        "meta": {
            "fonte": "dados/piloto/ (validado por validar_piloto.py)",
            "alfa": ALFA,
            "poder_alvo": PODER_ALVO,
            "n_planejado_por_grupo": N_PLANEJADO,
            "grade_n": list(GRADE_N),
            "semente": semente,
            "n_bootstrap": n_bootstrap,
            "n_simulacoes": n_simulacoes,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "ttfb": analisar_ttfb(amostras, semente, n_bootstrap, n_simulacoes),
        "erros_http": analisar_erros(amostras),
        "acessibilidade": analisar_acessibilidade(ler_axe(diretorio)),
    }


def formatar_resumo(analise: dict[str, Any]) -> str:
    """Tabela de texto com o essencial por tela (para o terminal)."""
    linhas = [
        f"{'tela':<14}{'med 4.5':>9}{'med 5.3':>9}{'razão':>7}{'d':>7}  "
        f"{'IC95 de d':<16}{'p':>7}{'p Holm':>8}{'n nec.':>8}  faixa"
    ]
    for tela, r in analise["ttfb"].items():
        d = r["delta_cliff"]
        mw = r["mann_whitney"]
        suf = r["suficiencia"]
        n_nec = suf["n_necessario"] if suf["n_necessario"] is not None else f">{GRADE_N[-1]}"
        linhas.append(
            f"{tela:<14}{r['warm'][VERSAO_BASE]['mediana_ms']:>9.2f}"
            f"{r['warm'][VERSAO_NOVA]['mediana_ms']:>9.2f}{r['razao_medianas']:>7.3f}"
            f"{d['d']:>7.2f}  [{d['ic95'][0]:>5.2f}, {d['ic95'][1]:>5.2f}]  "
            f"{mw['p']:>7.3f}{mw['p_holm']:>8.3f}{n_nec!s:>8}  {suf['faixa']}"
        )
    return "\n".join(linhas)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", type=Path, default=DIR_DADOS_PILOTO, help="pasta dos dados do piloto")
    parser.add_argument(
        "--saida", type=Path, default=None, help=f"JSON de saída (padrão: <dir>/{ARQUIVO_SAIDA})"
    )
    parser.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    parser.add_argument("--n-bootstrap", type=int, default=N_BOOTSTRAP_PADRAO)
    parser.add_argument("--n-simulacoes", type=int, default=N_SIMULACOES_PADRAO)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        analise = analisar(args.dir, args.semente, args.n_bootstrap, args.n_simulacoes)
    except ValueError as erro:
        print(erro, file=sys.stderr)
        return 1
    saida = args.saida or args.dir / ARQUIVO_SAIDA
    saida.write_text(json.dumps(analise, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(formatar_resumo(analise))
    print(f"\nAnálise gravada em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

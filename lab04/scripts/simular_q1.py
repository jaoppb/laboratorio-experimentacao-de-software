"""Q1: erro tipo I dos dois testes quando H0 é verdadeira.

Uso (a partir de ``lab04/``): ``uv run python scripts/simular_q1.py``.
Em cada cenário os dois grupos seguem a MESMA lognormal (mesma mediana e mesmo
``sigma_log``), então H0 é verdadeira tanto para o Welch quanto para o
Mann-Whitney. Os dois cenários usam os parâmetros de ``com_bot`` e de
``sem_bot`` de ``dados/parametros.json``. Cada um roda 10.000 repetições com um
``default_rng(42)`` novo, e a saída ``dados/simulado/q1_erro_tipo1.csv`` guarda a
proporção de p-valores < 0,05 por (cenário, teste), e ``q1_p_valores.npz`` guarda os
p-valores (para recalcular em outro α sem simular de novo). O script só mede e grava:
um desvio de 5% é resultado a reportar, não erro.
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

from src.montecarlo import N_REP_PADRAO, ResultadoMonteCarlo, executar_montecarlo  # noqa: E402
from src.pvalores import chave as chave_p, salvar  # noqa: E402

SEMENTE = 42
ALFA = 0.05
CENARIOS = ("com_bot", "sem_bot")
TESTES = (("welch", "welch"), ("mannwhitney", "mannwhitney"))
ARQUIVO_PARAMETROS = RAIZ / "dados" / "parametros.json"
DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"
NOME_CSV = "q1_erro_tipo1.csv"
NOME_P_VALORES = "q1_p_valores.npz"
COLUNAS = ["cenario", "teste", "n_rep", "alfa", "taxa_rejeicao"]


def carregar_parametros(caminho: Path = ARQUIVO_PARAMETROS) -> dict:
    """Carrega os parâmetros estimados dos dados reais."""
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def p_valores_cenario(params: dict, n_rep: int) -> ResultadoMonteCarlo:
    """p-valores dos dois testes com os dois grupos iguais a ``params``."""
    n = int(params["n"])
    mediana = float(params["mediana"])
    sigma = float(params["sigma_log"])
    return executar_montecarlo(
        np.random.default_rng(SEMENTE),
        n_a=n,
        n_b=n,
        mediana_a=mediana,
        mediana_b=mediana,
        sigma_a=sigma,
        sigma_b=sigma,
        n_rep=n_rep,
    )


def simular_cenario(params: dict, n_rep: int) -> dict[str, float]:
    """Taxa de rejeição de cada teste com os dois grupos iguais a ``params``."""
    return p_valores_cenario(params, n_rep).taxa_rejeicao(ALFA)


def executar(
    diretorio: Path = DIRETORIO_SAIDA,
    arquivo_parametros: Path = ARQUIVO_PARAMETROS,
    n_rep: int = N_REP_PADRAO,
) -> list[dict]:
    """Roda os dois cenários H0 e grava ``q1_erro_tipo1.csv``."""
    parametros = carregar_parametros(arquivo_parametros)
    linhas = []
    p_valores = {}
    for cenario in CENARIOS:
        resultado = p_valores_cenario(parametros[cenario], n_rep)
        taxas = resultado.taxa_rejeicao(ALFA)
        p_valores[chave_p(cenario, 1.0, "welch")] = resultado.p_welch
        p_valores[chave_p(cenario, 1.0, "mannwhitney")] = resultado.p_mannwhitney
        for teste, chave in TESTES:
            linhas.append(
                {
                    "cenario": cenario,
                    "teste": teste,
                    "n_rep": n_rep,
                    "alfa": ALFA,
                    "taxa_rejeicao": taxas[chave],
                }
            )

    diretorio.mkdir(parents=True, exist_ok=True)
    with open(diretorio / NOME_CSV, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({**linha, "taxa_rejeicao": repr(linha["taxa_rejeicao"])})
    salvar(diretorio / NOME_P_VALORES, p_valores)
    return linhas


if __name__ == "__main__":
    executar()

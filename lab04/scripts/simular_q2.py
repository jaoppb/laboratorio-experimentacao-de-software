"""Q2: poder dos dois testes com efeitos de tamanho crescente.

Uso (a partir de ``lab04/``): ``uv run python scripts/simular_q2.py``.
O efeito é a razão entre as medianas dos grupos: o grupo A fica na mediana de
``dados/parametros.json`` e o grupo B na mediana multiplicada pela razão, com o
mesmo ``sigma_log`` nos dois (mudança de localização na escala log). Razão 1,0
é efeito zero (H0 verdadeira) e reproduz o resultado do Q1, pois cada ponto usa
um ``default_rng(42)`` novo e as mesmas chamadas do ``simular_q1``. Cada
(cenário, razão) roda 10.000 repetições; ``dados/simulado/q2_poder.csv`` guarda a
proporção de p-valores < 0,05 por (cenário, razão, teste).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.montecarlo import N_REP_PADRAO, ResultadoMonteCarlo, executar_montecarlo  # noqa: E402
from src.pvalores import chave, salvar  # noqa: E402

SEMENTE = 42
ALFA = 0.05
CENARIOS = ("com_bot", "sem_bot")
RAZOES = (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)
TESTES = ("welch", "mannwhitney")
ARQUIVO_PARAMETROS = RAIZ / "dados" / "parametros.json"
DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"
NOME_CSV = "q2_poder.csv"
NOME_P_VALORES = "q2_p_valores.npz"
COLUNAS = ["cenario", "teste", "razao_medianas", "n_rep", "alfa", "taxa_rejeicao"]


def carregar_parametros(caminho: Path = ARQUIVO_PARAMETROS) -> dict:
    """Carrega os parâmetros estimados dos dados reais."""
    import json

    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def p_valores_ponto(params: dict, razao: float, n_rep: int) -> ResultadoMonteCarlo:
    """p-valores dos dois testes com mediana do grupo B = ``razao`` × A."""
    n = int(params["n"])
    mediana = float(params["mediana"])
    sigma = float(params["sigma_log"])
    return executar_montecarlo(
        np.random.default_rng(SEMENTE),
        n_a=n,
        n_b=n,
        mediana_a=mediana,
        mediana_b=mediana * razao,
        sigma_a=sigma,
        sigma_b=sigma,
        n_rep=n_rep,
    )


def simular_ponto(params: dict, razao: float, n_rep: int) -> dict[str, float]:
    """Taxa de rejeição de cada teste com mediana do grupo B = ``razao`` × A."""
    return p_valores_ponto(params, razao, n_rep).taxa_rejeicao(ALFA)


def executar(
    diretorio: Path = DIRETORIO_SAIDA,
    arquivo_parametros: Path = ARQUIVO_PARAMETROS,
    n_rep: int = N_REP_PADRAO,
    razoes: tuple[float, ...] = RAZOES,
) -> list[dict]:
    """Roda todos os (cenário, razão) e grava ``q2_poder.csv``."""
    parametros = carregar_parametros(arquivo_parametros)
    linhas = []
    p_valores = {}
    for cenario in CENARIOS:
        for razao in razoes:
            resultado = p_valores_ponto(parametros[cenario], razao, n_rep)
            taxas = resultado.taxa_rejeicao(ALFA)
            p_valores[chave(cenario, razao, "welch")] = resultado.p_welch
            p_valores[chave(cenario, razao, "mannwhitney")] = resultado.p_mannwhitney
            for teste in TESTES:
                linhas.append(
                    {
                        "cenario": cenario,
                        "teste": teste,
                        "razao_medianas": razao,
                        "n_rep": n_rep,
                        "alfa": ALFA,
                        "taxa_rejeicao": taxas[teste],
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

"""Q3: erro tipo I e poder quando os dados violam os pressupostos do Welch.

Uso (a partir de ``lab04/``): ``uv run python scripts/simular_q3.py``.
Parte de uma situação de referência (n = 30 por grupo, lognormal com
``sigma_log`` = 1,0, mediana do ``sem_bot`` de ``dados/parametros.json``) e
muda UM fator por vez, para saber o que causou cada efeito:

- ``n_pequeno``: n = 10 por grupo;
- ``assimetria_extrema``: ``sigma_log`` = 3,0 (cauda muito pesada);
- ``outliers``: cada observação, nos dois grupos, é multiplicada por 20 com
  probabilidade 5% (contaminação); H0 continua verdadeira, pois o mecanismo é
  o mesmo nos dois grupos.

O efeito é a razão entre as medianas (grupo B = razão × grupo A). Razão 1,0 é
H0 verdadeira e gera ``q3_erro_tipo1.csv``; todas as razões geram
``q3_poder.csv``. Cada ponto usa 10.000 repetições e um ``default_rng(42)`` novo.
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

from src.montecarlo import N_REP_PADRAO, ResultadoMonteCarlo  # noqa: E402
from src.pvalores import chave, salvar  # noqa: E402
from src.simulacao import gerar_dados  # noqa: E402
from src.testes import aplicar_mannwhitney, aplicar_welch  # noqa: E402

SEMENTE = 42
ALFA = 0.05
RAZOES = (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)
TESTES = ("welch", "mannwhitney")
FATOR_OUTLIER = 20.0
PROB_OUTLIER = 0.05

# nome -> (n por grupo, sigma_log, probabilidade de contaminação)
CENARIOS = {
    "referencia": (30, 1.0, 0.0),
    "n_pequeno": (10, 1.0, 0.0),
    "assimetria_extrema": (30, 3.0, 0.0),
    "outliers": (30, 1.0, PROB_OUTLIER),
}

ARQUIVO_PARAMETROS = RAIZ / "dados" / "parametros.json"
DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"
CSV_TIPO1 = "q3_erro_tipo1.csv"
CSV_PODER = "q3_poder.csv"
NOME_P_VALORES = "q3_p_valores.npz"
COLUNAS_TIPO1 = ["cenario", "teste", "n_rep", "alfa", "taxa_rejeicao"]
COLUNAS_PODER = ["cenario", "teste", "razao_medianas", "n_rep", "alfa", "taxa_rejeicao"]


def p_valores_ponto(
    mediana: float, razao: float, n: int, sigma: float, prob_outlier: float, n_rep: int
) -> ResultadoMonteCarlo:
    """p-valores dos dois testes em um (cenário, razão)."""
    rng = np.random.default_rng(SEMENTE)
    p_welch = np.empty(n_rep)
    p_mw = np.empty(n_rep)
    for i in range(n_rep):
        a, b = gerar_dados(rng, n, n, mediana, mediana * razao, sigma, sigma)
        if prob_outlier > 0.0:
            a = np.where(rng.random(n) < prob_outlier, a * FATOR_OUTLIER, a)
            b = np.where(rng.random(n) < prob_outlier, b * FATOR_OUTLIER, b)
        p_welch[i] = aplicar_welch(a, b)["p_valor"]
        p_mw[i] = aplicar_mannwhitney(a, b)["p_valor"]
    return ResultadoMonteCarlo(p_welch, p_mw)


def simular_ponto(
    mediana: float, razao: float, n: int, sigma: float, prob_outlier: float, n_rep: int
) -> dict[str, float]:
    """Taxa de rejeição dos dois testes em um (cenário, razão)."""
    return p_valores_ponto(mediana, razao, n, sigma, prob_outlier, n_rep).taxa_rejeicao(ALFA)


def _escrever(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({**linha, "taxa_rejeicao": repr(linha["taxa_rejeicao"])})


def executar(
    diretorio: Path = DIRETORIO_SAIDA,
    arquivo_parametros: Path = ARQUIVO_PARAMETROS,
    n_rep: int = N_REP_PADRAO,
    razoes: tuple[float, ...] = RAZOES,
) -> tuple[list[dict], list[dict]]:
    """Roda todos os (cenário, razão) e grava ``q3_erro_tipo1.csv`` e ``q3_poder.csv``."""
    with open(arquivo_parametros, encoding="utf-8") as f:
        mediana = float(json.load(f)["sem_bot"]["mediana"])

    tipo1, poder = [], []
    p_valores = {}
    for cenario, (n, sigma, prob) in CENARIOS.items():
        for razao in razoes:
            resultado = p_valores_ponto(mediana, razao, n, sigma, prob, n_rep)
            taxas = resultado.taxa_rejeicao(ALFA)
            for teste in TESTES:
                p_valores[chave(cenario, razao, teste)] = (
                    resultado.p_welch if teste == "welch" else resultado.p_mannwhitney
                )
                base = {"cenario": cenario, "teste": teste, "n_rep": n_rep, "alfa": ALFA}
                poder.append({**base, "razao_medianas": razao, "taxa_rejeicao": taxas[teste]})
                if razao == 1.0:
                    tipo1.append({**base, "taxa_rejeicao": taxas[teste]})

    diretorio.mkdir(parents=True, exist_ok=True)
    _escrever(diretorio / CSV_TIPO1, COLUNAS_TIPO1, tipo1)
    _escrever(diretorio / CSV_PODER, COLUNAS_PODER, poder)
    salvar(diretorio / NOME_P_VALORES, p_valores)
    return tipo1, poder


if __name__ == "__main__":
    executar()

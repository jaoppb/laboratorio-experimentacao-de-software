"""Exemplo didático da simulação: UM conjunto lognormal com Welch e Mann-Whitney.

Uso (a partir de ``lab04/``): ``uv run python scripts/exemplo_simulado.py``.
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
ALPHA = 0.05
ARQUIVO_PARAMETROS = RAIZ / "dados" / "parametros.json"
DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"


def carregar_parametros(caminho: Path = ARQUIVO_PARAMETROS) -> dict:
    """Carrega os parâmetros estimados dos dados reais."""
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def executar(
    diretorio: Path = DIRETORIO_SAIDA,
    arquivo_parametros: Path = ARQUIVO_PARAMETROS,
) -> dict:
    """Gera o conjunto, aplica os dois testes e grava CSV e JSON."""
    parametros_fonte = carregar_parametros(arquivo_parametros)
    p_com = parametros_fonte["com_bot"]
    p_sem = parametros_fonte["sem_bot"]

    rng = np.random.default_rng(SEMENTE)
    com_bot, sem_bot = gerar_dados(
        rng,
        n_a=int(p_com["n"]),
        n_b=int(p_sem["n"]),
        mediana_a=float(p_com["mediana"]),
        mediana_b=float(p_sem["mediana"]),
        sigma_a=float(p_com["sigma_log"]),
        sigma_b=float(p_sem["sigma_log"]),
    )

    resultado = {
        "semente": SEMENTE,
        "parametros": {
            "com_bot": {
                "n": int(p_com["n"]),
                "mediana": float(p_com["mediana"]),
                "sigma_log": float(p_com["sigma_log"]),
            },
            "sem_bot": {
                "n": int(p_sem["n"]),
                "mediana": float(p_sem["mediana"]),
                "sigma_log": float(p_sem["sigma_log"]),
            },
            "alpha": ALPHA,
        },
        "welch": aplicar_welch(com_bot, sem_bot, alternativa="two-sided"),
        "mannwhitney": aplicar_mannwhitney(com_bot, sem_bot, alternativa="two-sided"),
        "medianas_amostrais": {
            "com_bot": float(np.median(com_bot)),
            "sem_bot": float(np.median(sem_bot)),
        },
        "medias_amostrais": {
            "com_bot": float(com_bot.mean()),
            "sem_bot": float(sem_bot.mean()),
        },
    }

    diretorio.mkdir(parents=True, exist_ok=True)
    with open(diretorio / "exemplo.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(["grupo", "valor"])
        for grupo, valores in (("com_bot", com_bot), ("sem_bot", sem_bot)):
            for v in valores:
                escritor.writerow([grupo, repr(float(v))])
    with open(diretorio / "exemplo_resultado.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    return resultado


if __name__ == "__main__":
    executar()

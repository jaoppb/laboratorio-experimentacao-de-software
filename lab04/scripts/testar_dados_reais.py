"""Aplica Welch e Mann-Whitney aos dados reais (com_bot × sem_bot).

Uso (a partir de ``lab04/``): ``uv run python scripts/testar_dados_reais.py``.
Lê ``dados/reais/pr_merge_time.csv`` e grava ``dados/reais/resultado_testes.json``
com estatística, p-valor, tamanho de efeito e conclusão de cada teste (bicaudal,
α = 0,05). O grupo A é ``com_bot`` e o B é ``sem_bot``: efeito positivo significa
que os PRs com bot tendem a demorar mais para o merge.
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

from src.testes import aplicar_mannwhitney, aplicar_welch  # noqa: E402

ALFA = 0.05
ARQUIVO_CSV = RAIZ / "dados" / "reais" / "pr_merge_time.csv"
ARQUIVO_SAIDA = RAIZ / "dados" / "reais" / "resultado_testes.json"


def carregar_grupos(caminho: Path = ARQUIVO_CSV) -> tuple[np.ndarray, np.ndarray]:
    """Devolve (com_bot, sem_bot) em horas."""
    grupos: dict[str, list[float]] = {"com_bot": [], "sem_bot": []}
    with open(caminho, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            grupos[linha["grupo"]].append(float(linha["tempo_merge_horas"]))
    return np.array(grupos["com_bot"]), np.array(grupos["sem_bot"])


def magnitude(valor: float, limites: tuple[float, float, float]) -> str:
    """Classifica |valor| em desprezível, pequeno, médio ou grande."""
    v = abs(valor)
    for limite, nome in zip(limites, ("desprezível", "pequeno", "médio")):
        if v < limite:
            return nome
    return "grande"


def conclusao(p_valor: float, alfa: float = ALFA) -> str:
    if p_valor < alfa:
        return "rejeita H0: há diferença entre os grupos"
    return "não rejeita H0: sem evidência de diferença entre os grupos"


def executar(
    arquivo_csv: Path = ARQUIVO_CSV, arquivo_saida: Path = ARQUIVO_SAIDA
) -> dict:
    com_bot, sem_bot = carregar_grupos(arquivo_csv)
    welch = aplicar_welch(com_bot, sem_bot)
    mw = aplicar_mannwhitney(com_bot, sem_bot)
    # d de Cohen: 0,2 / 0,5 / 0,8; r rank-biserial: 0,1 / 0,3 / 0,5
    welch["magnitude_efeito"] = magnitude(welch["tamanho_efeito"], (0.2, 0.5, 0.8))
    mw["magnitude_efeito"] = magnitude(mw["tamanho_efeito"], (0.1, 0.3, 0.5))
    for r in (welch, mw):
        r["conclusao"] = conclusao(r["p_valor"])

    resultado = {
        "alfa": ALFA,
        "alternativa": "two-sided",
        "n": {"com_bot": int(com_bot.size), "sem_bot": int(sem_bot.size)},
        "medianas_horas": {
            "com_bot": float(np.median(com_bot)),
            "sem_bot": float(np.median(sem_bot)),
        },
        "medias_horas": {
            "com_bot": float(com_bot.mean()),
            "sem_bot": float(sem_bot.mean()),
        },
        "welch": welch,
        "mannwhitney": mw,
        "concordam": (welch["p_valor"] < ALFA) == (mw["p_valor"] < ALFA),
    }
    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return resultado


if __name__ == "__main__":
    executar()

"""Roda as simulações Q1, Q2 e Q3 do Lab04 e grava os CSVs em ``dados/simulado/``.

Uso (a partir de ``lab04/``): ``uv run python scripts/rodar_simulacoes.py``.
Também é chamado por ``scripts/gerar_dashboard.py`` (comando único).

Cada simulação usa semente fixa (``default_rng(42)``) e 10.000 repetições por
ponto, então duas execuções geram CSVs idênticos:

- Q1 -> ``q1_erro_tipo1.csv``
- Q2 -> ``q2_poder.csv``
- Q3 -> ``q3_erro_tipo1.csv`` e ``q3_poder.csv``
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts import simular_q1, simular_q2, simular_q3  # noqa: E402
from src.montecarlo import N_REP_PADRAO  # noqa: E402

DIRETORIO_SAIDA = RAIZ / "dados" / "simulado"


def executar(
    diretorio: Path = DIRETORIO_SAIDA, n_rep: int = N_REP_PADRAO, verbose: bool = True
) -> dict[str, float]:
    """Roda Q1, Q2 e Q3 em sequência e devolve o tempo (s) de cada uma."""
    etapas = (
        ("Q1", simular_q1.executar),
        ("Q2", simular_q2.executar),
        ("Q3", simular_q3.executar),
    )
    tempos: dict[str, float] = {}
    for nome, executar_etapa in etapas:
        inicio = time.perf_counter()
        executar_etapa(diretorio=diretorio, n_rep=n_rep)
        tempos[nome] = time.perf_counter() - inicio
        if verbose:
            print(f"{nome} concluída em {tempos[nome]:.1f} s ({n_rep} repetições por ponto)")
    return tempos


def main() -> None:
    inicio = time.perf_counter()
    executar()
    print(f"Simulações concluídas em {time.perf_counter() - inicio:.1f} s. CSVs em {DIRETORIO_SAIDA}")


if __name__ == "__main__":
    main()

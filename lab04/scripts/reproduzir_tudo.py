"""Reprodução ponta a ponta do Lab04 (semente fixa 42).

Uso (a partir de ``lab04/``):
    uv run python scripts/reproduzir_tudo.py

Refaz, nesta ordem, tudo o que alimenta o dashboard e termina gerando-o:
1. ``testar_dados_reais.py``  -> dados/reais/resultado_testes.json
2. ``rodar_simulacoes.py``    -> dados/simulado/q1_erro_tipo1.csv, q2_poder.csv,
                                 q3_erro_tipo1.csv e q3_poder.csv (Q1, Q2 e Q3)
3. ``gerar_dashboard.py``     -> dashboard/index.html (inclui o exemplo simulado)

Como todas as simulações usam ``numpy.random.default_rng(42)``, uma segunda
execução gera arquivos idênticos (``git status`` não deve mostrar mudanças).
A coleta dos dados reais (``coletar_prs.py``) não entra aqui: ela usa a API do
GitHub e o resultado já está versionado em ``dados/reais/pr_merge_time.csv``.
"""

from __future__ import annotations

import runpy
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

ETAPAS = (
    "testar_dados_reais.py",
    "rodar_simulacoes.py",
    "gerar_dashboard.py",
)


def main() -> None:
    for nome in ETAPAS:
        inicio = time.perf_counter()
        print(f"==> {nome}", flush=True)
        runpy.run_path(str(RAIZ / "scripts" / nome), run_name="__main__")
        print(f"    ok ({time.perf_counter() - inicio:.1f} s)", flush=True)


if __name__ == "__main__":
    main()


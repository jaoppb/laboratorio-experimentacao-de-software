"""Comando único do Lab04: gera o dashboard HTML completo da Sprint 1.

Uso (a partir de ``lab04/``):
    uv run python scripts/gerar_dashboard.py

Etapas executadas:
1. Executa o exemplo simulado determinístico (semente 42), gerando exemplo.csv e exemplo_resultado.json;
2. Gera as figuras G1 e G2 em Plotly com dados lidos dos arquivos;
3. Escreve ``dashboard/index.html`` contendo os gráficos e seções do enunciado.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.dashboard.gerador import gerar_dashboard


def main() -> None:
    caminho = gerar_dashboard()
    print(f"Dashboard gerado com sucesso em: {caminho}")


if __name__ == "__main__":
    main()

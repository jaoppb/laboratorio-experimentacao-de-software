"""Comando único do Lab04: gera o dashboard HTML completo da Sprint 1.

Uso (a partir de ``lab04/``):
    uv run python scripts/gerar_dashboard.py

Etapas executadas:
1. Roda as simulações Q1, Q2 e Q3 (``scripts/rodar_simulacoes.py``, ~4 min), gravando os CSVs em ``dados/simulado/``;
2. Executa o exemplo simulado determinístico (semente 42), gerando exemplo.csv e exemplo_resultado.json;
3. Gera as figuras G1 e G2 em Plotly com dados lidos dos arquivos;
4. Escreve ``dashboard/index.html`` contendo os gráficos e seções do enunciado.

Para pular as simulações (usar os CSVs já gravados), passe ``--sem-simulacoes``.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.rodar_simulacoes import executar as rodar_simulacoes
from src.dashboard.gerador import gerar_dashboard


def main() -> None:
    if "--sem-simulacoes" not in sys.argv[1:]:
        rodar_simulacoes()
    caminho = gerar_dashboard()
    print(f"Dashboard gerado com sucesso em: {caminho}")


if __name__ == "__main__":
    main()

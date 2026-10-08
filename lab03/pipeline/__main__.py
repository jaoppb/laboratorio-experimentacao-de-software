"""Entry point for the Lab03 data collection and analysis pipeline.

Execution:
    uv run python -m pipeline --config config.yaml
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from pipeline.funnel import FunnelTracker
from pipeline.http_client import GitHubClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load and parse YAML configuration file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config or {}


def main() -> int:
    """CLI entrypoint for running the pipeline."""
    parser = argparse.ArgumentParser(
        description="Lab03 - Pipeline de Mineração de Métricas DORA"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Caminho para o arquivo de configuração YAML (default: config.yaml)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Lab03 - Pipeline de Mineração de Métricas DORA")
    print("=" * 60)

    try:
        config = load_config(args.config)
    except Exception as exc:
        logger.error("Erro ao carregar configuração: %s", exc)
        return 1

    janela = config.get("janela", {})
    amostra = config.get("amostra", {})
    dirs = config.get("diretorios", {})

    print(f"[*] Configuração carregada de: {args.config}")
    print(f"[*] Janela de observação: {janela.get('inicio')} até {janela.get('fim')}")
    print(f"[*] Amostra desejada: {amostra.get('tamanho_final', 100)} repositórios")
    print(
        f"[*] Critérios mínimos: >= {amostra.get('min_releases', 5)} releases, "
        f">= {amostra.get('min_workflow_runs', 50)} workflow runs"
    )

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("\n[!] AVISO: A variável de ambiente GITHUB_TOKEN não está definida.")
        print("[!] Para executar a coleta contra a API do GitHub sem bloqueio de cota,")
        print("[!] defina GITHUB_TOKEN no seu ambiente ou em um arquivo .env:")
        print("    No PowerShell: $env:GITHUB_TOKEN = 'seu_token_aqui'")
        print("    No Bash:       export GITHUB_TOKEN='seu_token_aqui'\n")

    dados_dir = Path(dirs.get("dados", "dados"))
    dados_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(dirs.get("cache", "cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize funnel tracker
    funnel = FunnelTracker()
    funnel.record_stage(
        etapa="Busca inicial por estrelas (Search API)",
        quantidade_restante=0,
        descartados=0,
        motivo_descarte="-",
    )
    funnel.record_stage(
        etapa="Filtro de Actions ativas",
        quantidade_restante=0,
        descartados=0,
        motivo_descarte="Workflows total_count == 0",
    )
    funnel.record_stage(
        etapa=f"Filtro de releases na janela (>= {amostra.get('min_releases', 5)})",
        quantidade_restante=0,
        descartados=0,
        motivo_descarte=f"Menos de {amostra.get('min_releases', 5)} releases na janela",
    )
    funnel.record_stage(
        etapa=f"Filtro de workflow runs na janela (>= {amostra.get('min_workflow_runs', 50)})",
        quantidade_restante=0,
        descartados=0,
        motivo_descarte=f"Menos de {amostra.get('min_workflow_runs', 50)} runs no default branch",
    )

    funil_csv_path = dados_dir / "funil.csv"
    funnel.export_csv(funil_csv_path)
    print(f"[*] Funil inicial registrado em: {funil_csv_path}")
    print("[*] Estrutura do pipeline pronta e validada com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

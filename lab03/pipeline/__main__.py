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
from pipeline.orchestrator import run_pipeline

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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de repositórios aceitos (sobrescreve tamanho_final do config.yaml)",
    )
    parser.add_argument(
        "--clean",
        "--fresh",
        action="store_true",
        help="Realiza uma execução limpa (apaga repositórios e estado anteriores)",
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

    if args.clean:
        dados_dir = Path(config.get("diretorios", {}).get("dados", "dados"))
        for fname in ["repositorios.parquet", "repositorios.csv", "funil.csv", ".pipeline_state.json"]:
            fpath = dados_dir / fname
            if fpath.exists():
                fpath.unlink(missing_ok=True)
        print("[*] Estado anterior e datasets limpos para execução homogênea (--clean).")

    janela = config.get("janela", {})
    amostra = config.get("amostra", {})
    target_limit = args.limit or amostra.get("tamanho_final", 100)

    print(f"[*] Configuração carregada de: {args.config}")
    print(f"[*] Janela de observação: {janela.get('inicio')} até {janela.get('fim')}")
    print(f"[*] Amostra desejada: {target_limit} repositórios")
    print(
        f"[*] Critérios mínimos: >= {amostra.get('min_releases', 5)} releases, "
        f">= {amostra.get('min_workflow_runs', 50)} workflow runs"
    )

    from pipeline.http_client import resolve_tokens

    tokens = resolve_tokens()
    if not tokens:
        print("\n[!] AVISO: Nenhuma chave da API GitHub configurada (GITHUB_TOKEN ou GITHUB_TOKENS).")
        print("[!] Para executar a coleta contra a API do GitHub sem bloqueio de cota,")
        print("[!] defina GITHUB_TOKENS ou GITHUB_TOKEN no seu ambiente ou em um arquivo .env:")
        print("    No .env:       GITHUB_TOKENS='tok1,tok2'\n")
    else:
        print(f"[*] Tokens configurados para rotação: {len(tokens)} token(s) ativo(s).")

    try:
        results = run_pipeline(config_path=args.config, limit=args.limit)
        print("\n" + "=" * 60)
        print("[*] Pipeline finalizado com sucesso!")
        print(f"[*] Repositórios avaliados no funil: {results['total_evaluated']}")
        print(f"[*] Repositórios aceitos na amostra: {results['accepted_count']}")
        print(f"[*] Dataset Parquet: {results['parquet_path']}")
        print(f"[*] Dataset CSV:     {results['csv_path']}")
        print(f"[*] Funil CSV:       {results['funil_csv']}")
        print("=" * 60)
        return 0
    except Exception as exc:
        logger.error("Erro durante a execução do pipeline: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

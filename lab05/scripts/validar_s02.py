"""Valida a completude, a consistência e o formato dos dados da coleta S02.

Uso::

    python scripts/validar_s02.py [--dir dados/reais] [--repeticoes 80]

Sai com código 0 quando não há problemas e 1 caso contrário (uma linha por problema).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coleta_s02 import DIR_DADOS_S02, NOME_CSV_S02, NOME_JSON_S02, TELAS_S02
from validar_piloto import validar_diretorio


def validar_diretorio_s02(
    diretorio: Path,
    repeticoes: int = 80,
    exigir_real: bool = True,
) -> list[str]:
    """Valida CSV, resumo e relatórios axe da coleta S02."""
    return validar_diretorio(
        diretorio,
        repeticoes=repeticoes,
        exigir_real=exigir_real,
        telas=TELAS_S02,
        nome_csv=NOME_CSV_S02,
        nome_json=NOME_JSON_S02,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida os dados da coleta S02")
    parser.add_argument("--dir", type=Path, default=DIR_DADOS_S02)
    parser.add_argument("--repeticoes", type=int, default=80)
    parser.add_argument(
        "--permitir-simulado",
        action="store_true",
        help="Aceita dados simulados (sem meta.origem real nem relatórios axe)",
    )
    args = parser.parse_args(argv)

    problemas = validar_diretorio_s02(args.dir, args.repeticoes, not args.permitir_simulado)
    if problemas:
        print(f"{len(problemas)} problema(s) em {args.dir}:", file=sys.stderr)
        for problema in problemas:
            print(f"- {problema}", file=sys.stderr)
        return 1
    print(f"OK: dados S02 de {args.dir} completos, consistentes e no formato esperado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

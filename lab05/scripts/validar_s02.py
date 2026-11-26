"""Valida a completude, a consistência e o formato dos dados da coleta S02.

Uso::

    python scripts/validar_s02.py [--dir dados/reais] [--repeticoes 80]

Sai com código 0 quando não há problemas e 1 caso contrário (uma linha por problema).
"""

from __future__ import annotations

import sys
from pathlib import Path

from coleta_s02 import DIR_DADOS_S02, NOME_CSV_S02, NOME_JSON_S02, TELAS_S02
from validar_piloto import main as main_piloto
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
    return main_piloto(
        argv,
        descricao="Valida os dados da coleta S02",
        default_dir=DIR_DADOS_S02,
        default_repeticoes=80,
        telas=TELAS_S02,
        nome_csv=NOME_CSV_S02,
        nome_json=NOME_JSON_S02,
        rotulo="S02",
    )


if __name__ == "__main__":
    sys.exit(main())

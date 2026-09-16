#!/usr/bin/env python3
"""
Kata 04 — Garment Groups
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Raciocínio combinatório / invariante em O(1).
"""

import sys


def main() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    g = int(input_data[1])

    # Para pendurar N camisas em G grupos contíguos de pregadores compartilhados:
    # Cada grupo de k camisas necessita de k + 1 pregadores.
    # Somando sobre todos os G grupos: sum(k_i + 1) = sum(k_i) + sum(1) = N + G.
    print(n + g)


if __name__ == "__main__":
    main()

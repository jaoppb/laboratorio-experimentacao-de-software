#!/usr/bin/env python3
"""
Kata 03 — Exploring the Terrain
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Simulação sobre matriz com resolução de conflitos temporais em O(T).
"""

import sys


def main() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    m = int(input_data[1])
    t = int(input_data[2])

    ptr = 3
    # Matriz 0-indexada de minérios
    grid: list[list[int]] = []
    for _ in range(n):
        row = [int(x) for x in input_data[ptr : ptr + m]]
        grid.append(row)
        ptr += m

    # Coordenadas de Giovana (T pares)
    giovana_coords: list[tuple[int, int]] = []
    for _ in range(t):
        r = int(input_data[ptr]) - 1
        c = int(input_data[ptr + 1]) - 1
        giovana_coords.append((r, c))
        ptr += 2

    # Coordenadas de Arthur (T pares)
    arthur_coords: list[tuple[int, int]] = []
    for _ in range(t):
        r = int(input_data[ptr]) - 1
        c = int(input_data[ptr + 1]) - 1
        arthur_coords.append((r, c))
        ptr += 2

    offsets = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]

    total_giovana = 0
    total_arthur = 0

    for step in range(t):
        gr, gc = giovana_coords[step]
        ar, ac = arthur_coords[step]

        # Células válidas no alcance de Giovana no instante step
        g_cells = set()
        for dr, dc in offsets:
            nr, nc = gr + dr, gc + dc
            if 0 <= nr < n and 0 <= nc < m:
                g_cells.add((nr, nc))

        # Células válidas no alcance de Arthur no instante step
        a_cells = set()
        for dr, dc in offsets:
            nr, nc = ar + dr, ac + dc
            if 0 <= nr < n and 0 <= nc < m:
                a_cells.add((nr, nc))

        # Células disputadas simultaneamente por ambos não são extraídas
        g_exclusive = g_cells - a_cells
        a_exclusive = a_cells - g_cells

        # Extração de Giovana
        for r, c in g_exclusive:
            val = grid[r][c]
            if val > 0:
                total_giovana += val
                grid[r][c] = 0

        # Extração de Arthur
        for r, c in a_exclusive:
            val = grid[r][c]
            if val > 0:
                total_arthur += val
                grid[r][c] = 0

    print(f"{total_giovana} {total_arthur}")


if __name__ == "__main__":
    main()

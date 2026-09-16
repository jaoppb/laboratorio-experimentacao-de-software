#!/usr/bin/env python3
"""
Kata 06 — N-Checkers
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Busca em profundidade com backtracking sobre o tabuleiro em O(ramificações).
"""

import sys


def solve() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    board_rows = input_data[1 : n + 1]
    board = [list(row) for row in board_rows]

    # Direções diagonais de captura
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def dfs(r: int, c: int) -> int:
        max_captures = 0
        for dr, dc in directions:
            mr, mc = r + dr, c + dc
            lr, lc = r + 2 * dr, c + 2 * dc

            if 0 <= lr < n and 0 <= lc < n:
                if board[mr][mc] == "P" and board[lr][lc] == ".":
                    # Efetua o salto e captura
                    board[mr][mc] = "."
                    board[r][c] = "."
                    board[lr][lc] = "B"

                    captures = 1 + dfs(lr, lc)
                    if captures > max_captures:
                        max_captures = captures

                    # Desfaz o movimento (backtracking)
                    board[lr][lc] = "."
                    board[r][c] = "B"
                    board[mr][mc] = "P"

        return max_captures

    # Identifica todas as peças brancas ('B') de Bob
    white_pieces: list[tuple[int, int]] = []
    for r in range(n):
        for c in range(n):
            if board[r][c] == "B":
                white_pieces.append((r, c))

    overall_max = 0
    for r, c in white_pieces:
        captures = dfs(r, c)
        if captures > overall_max:
            overall_max = captures

    print(overall_max)


if __name__ == "__main__":
    solve()

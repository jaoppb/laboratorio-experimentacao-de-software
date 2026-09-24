"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 06-n-checkers."""

import sys


def max_captured_pieces() -> None:
    raw = sys.stdin.read().split()
    if not raw:
        return
    board_size = int(raw[0])
    board = [list(line) for line in raw[1 : 1 + board_size]]

    move_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    record_captures = 0

    def search_jumps(r: int, c: int, current_score: int) -> None:
        nonlocal record_captures
        if current_score > record_captures:
            record_captures = current_score

        for dr, dc in move_offsets:
            enemy_r, enemy_c = r + dr, c + dc
            dest_r, dest_c = r + 2 * dr, c + 2 * dc
            if 0 <= dest_r < board_size and 0 <= dest_c < board_size:
                if board[enemy_r][enemy_c] == "P" and board[dest_r][dest_c] == ".":
                    board[enemy_r][enemy_c] = "."
                    board[r][c] = "."
                    board[dest_r][dest_c] = "B"
                    search_jumps(dest_r, dest_c, current_score + 1)
                    board[dest_r][dest_c] = "."
                    board[r][c] = "B"
                    board[enemy_r][enemy_c] = "P"

    for i in range(board_size):
        for j in range(board_size):
            if board[i][j] == "B":
                search_jumps(i, j, 0)

    print(record_captures)


if __name__ == "__main__":
    max_captured_pieces()

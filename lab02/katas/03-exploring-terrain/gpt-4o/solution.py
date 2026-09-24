"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 03-exploring-terrain."""

import sys


def simulate_exploration() -> None:
    tokens = sys.stdin.buffer.read().split()
    if not tokens:
        return

    rows = int(tokens[0])
    cols = int(tokens[1])
    turns = int(tokens[2])

    ptr = 3
    matrix = []
    for _ in range(rows):
        matrix.append([int(v) for v in tokens[ptr : ptr + cols]])
        ptr += cols

    guilherme_moves = []
    for _ in range(turns):
        guilherme_moves.append((int(tokens[ptr]), int(tokens[ptr + 1])))
        ptr += 2

    arthur_moves = []
    for _ in range(turns):
        arthur_moves.append((int(tokens[ptr]), int(tokens[ptr + 1])))
        ptr += 2

    def adjacent_positions(row: int, col: int) -> list[tuple[int, int]]:
        positions = [(row, col)]
        if row > 1:
            positions.append((row - 1, col))
        if row < rows:
            positions.append((row + 1, col))
        if col > 1:
            positions.append((row, col - 1))
        if col < cols:
            positions.append((row, col + 1))
        return positions

    score_guilherme = 0
    score_arthur = 0

    for round_idx in range(turns):
        scope_g = adjacent_positions(*guilherme_moves[round_idx])
        scope_a = adjacent_positions(*arthur_moves[round_idx])
        conflict = set(scope_g) & set(scope_a)

        for r, c in scope_g:
            if (r, c) not in conflict:
                score_guilherme += matrix[r - 1][c - 1]
                matrix[r - 1][c - 1] = 0

        for r, c in scope_a:
            if (r, c) not in conflict:
                score_arthur += matrix[r - 1][c - 1]
                matrix[r - 1][c - 1] = 0

    print(score_guilherme, score_arthur)


if __name__ == "__main__":
    simulate_exploration()

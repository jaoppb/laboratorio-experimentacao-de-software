import sys


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    board = [list(row) for row in input_data[1 : n + 1]]

    dirs = ((-1, -1), (-1, 1), (1, -1), (1, 1))

    max_c = 0

    def dfs(r, c, captured):
        nonlocal max_c
        if captured > max_c:
            max_c = captured

        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            nnr, nnc = r + 2 * dr, c + 2 * dc
            if 0 <= nnr < n and 0 <= nnc < n:
                if board[nr][nc] == "P" and board[nnr][nnc] == ".":
                    # Realiza o salto e remove temporariamente a peça adversária
                    board[r][c] = "."
                    board[nr][nc] = "."
                    board[nnr][nnc] = "B"

                    dfs(nnr, nnc, captured + 1)

                    # Backtracking
                    board[nnr][nnc] = "."
                    board[nr][nc] = "P"
                    board[r][c] = "B"

    ans = 0
    for r in range(n):
        for c in range(n):
            if board[r][c] == "B":
                max_c = 0
                dfs(r, c, 0)
                if max_c > ans:
                    ans = max_c

    sys.stdout.write(f"{ans}\n")


if __name__ == "__main__":
    solve()

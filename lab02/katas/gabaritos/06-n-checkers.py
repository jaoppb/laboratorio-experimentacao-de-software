import sys


def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    board = [list(row) for row in data[1 : 1 + n]]

    dirs = ((-1, -1), (-1, 1), (1, -1), (1, 1))
    best = 0

    def dfs(r, c, taken):
        nonlocal best
        if taken > best:
            best = taken
        for dr, dc in dirs:
            mr, mc = r + dr, c + dc
            lr, lc = r + 2 * dr, c + 2 * dc
            if not (0 <= lr < n and 0 <= lc < n):
                continue
            if board[mr][mc] != "P" or board[lr][lc] != ".":
                continue
            board[mr][mc] = "."
            board[r][c] = "."
            board[lr][lc] = "B"
            dfs(lr, lc, taken + 1)
            board[lr][lc] = "."
            board[r][c] = "B"
            board[mr][mc] = "P"

    for r in range(n):
        for c in range(n):
            if board[r][c] == "B":
                dfs(r, c, 0)

    print(best)


main()

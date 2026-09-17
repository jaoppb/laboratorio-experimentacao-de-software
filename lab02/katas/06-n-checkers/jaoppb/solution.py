N = int(input())
board = [list(input()) for _ in range(N)]

DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def dfs(r, c):
    piece = board[r][c]
    best = 0

    for dr, dc in DIRECTIONS:
        mr, mc = r + dr, c + dc
        lr, lc = r + 2 * dr, c + 2 * dc

        if 0 <= lr < N and 0 <= lc < N and board[mr][mc] == 'P' and board[lr][lc] == '.':
            board[r][c] = '.'
            board[mr][mc] = '.'
            board[lr][lc] = piece

            best = max(best, 1 + dfs(lr, lc))

            board[lr][lc] = '.'
            board[mr][mc] = 'P'
            board[r][c] = piece

    return best


best_total = 0
for r in range(N):
    for c in range(N):
        if board[r][c] == 'B':
            best_total = max(best_total, dfs(r, c))

print(best_total)

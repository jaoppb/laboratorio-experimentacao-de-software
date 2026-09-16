import sys


def main():
    data = sys.stdin.read().split('\n')
    n = int(data[0].strip())
    board = [list(data[i + 1]) for i in range(n)]

    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def dfs(r, c):
        piece = board[r][c]
        best = 0
        for dr, dc in directions:
            mr, mc = r + dr, c + dc
            lr, lc = r + 2 * dr, c + 2 * dc
            if 0 <= lr < n and 0 <= lc < n:
                if board[mr][mc] == 'P' and board[lr][lc] == '.':
                    board[r][c] = '.'
                    board[mr][mc] = '.'
                    board[lr][lc] = piece
                    result = 1 + dfs(lr, lc)
                    if result > best:
                        best = result
                    board[lr][lc] = '.'
                    board[mr][mc] = 'P'
                    board[r][c] = piece
        return best

    best_total = 0
    for r in range(n):
        for c in range(n):
            if board[r][c] == 'B':
                result = dfs(r, c)
                if result > best_total:
                    best_total = result

    print(best_total)


if __name__ == '__main__':
    main()

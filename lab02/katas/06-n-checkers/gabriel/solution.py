def main():
    n = int(input())
    board = [list(input()) for _ in range(n)]

    direcoes = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    melhor = [0]

    def buscar(r, c, capturas):
        if capturas > melhor[0]:
            melhor[0] = capturas

        for dr, dc in direcoes:
            mr, mc = r + dr, c + dc
            fr, fc = r + 2 * dr, c + 2 * dc
            if not (0 <= fr < n and 0 <= fc < n):
                continue
            if board[mr][mc] != "P" or board[fr][fc] != ".":
                continue

            board[mr][mc] = "."
            board[r][c] = "."
            board[fr][fc] = "B"

            buscar(fr, fc, capturas + 1)

            board[fr][fc] = "."
            board[r][c] = "B"
            board[mr][mc] = "P"

    for r in range(n):
        for c in range(n):
            if board[r][c] == "B":
                buscar(r, c, 0)

    print(melhor[0])


main()

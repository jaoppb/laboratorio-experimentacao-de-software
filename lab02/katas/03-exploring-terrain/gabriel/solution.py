import sys


def vizinhas(i, j, n, m):
    cels = [(i, j)]
    if i > 1:
        cels.append((i - 1, j))
    if i < n:
        cels.append((i + 1, j))
    if j > 1:
        cels.append((i, j - 1))
    if j < m:
        cels.append((i, j + 1))
    return cels


def main():
    data = sys.stdin.read().split()
    pos = 0
    n = int(data[pos]); pos += 1
    m = int(data[pos]); pos += 1
    t = int(data[pos]); pos += 1

    minerio = []
    for _ in range(n):
        linha = [int(x) for x in data[pos:pos + m]]
        pos += m
        minerio.append(linha)

    plano_g = []
    for _ in range(t):
        plano_g.append((int(data[pos]), int(data[pos + 1])))
        pos += 2

    plano_a = []
    for _ in range(t):
        plano_a.append((int(data[pos]), int(data[pos + 1])))
        pos += 2

    total_g = 0
    total_a = 0

    for k in range(t):
        gi, gj = plano_g[k]
        ai, aj = plano_a[k]

        cels_g = vizinhas(gi, gj, n, m)
        cels_a = vizinhas(ai, aj, n, m)
        compartilhadas = set(cels_g) & set(cels_a)

        for (i, j) in cels_g:
            if (i, j) not in compartilhadas:
                total_g += minerio[i - 1][j - 1]
                minerio[i - 1][j - 1] = 0

        for (i, j) in cels_a:
            if (i, j) not in compartilhadas:
                total_a += minerio[i - 1][j - 1]
                minerio[i - 1][j - 1] = 0

    print(total_g, total_a)


main()

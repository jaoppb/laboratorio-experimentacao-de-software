import sys


def main() -> None:
    data = sys.stdin.buffer.read().split()
    idx = 0

    n = int(data[idx]); idx += 1
    m = int(data[idx]); idx += 1
    t = int(data[idx]); idx += 1

    grid = [[0] * (m + 2) for _ in range(n + 2)]
    for i in range(1, n + 1):
        row = grid[i]
        for j in range(1, m + 1):
            row[j] = int(data[idx]); idx += 1

    g_plan = []
    for _ in range(t):
        gi = int(data[idx]); idx += 1
        gj = int(data[idx]); idx += 1
        g_plan.append((gi, gj))

    a_plan = []
    for _ in range(t):
        ai = int(data[idx]); idx += 1
        aj = int(data[idx]); idx += 1
        a_plan.append((ai, aj))

    def footprint(i, j):
        cells = [(i, j)]
        if i - 1 >= 1:
            cells.append((i - 1, j))
        if i + 1 <= n:
            cells.append((i + 1, j))
        if j - 1 >= 1:
            cells.append((i, j - 1))
        if j + 1 <= m:
            cells.append((i, j + 1))
        return cells

    total_g = 0
    total_a = 0

    for k in range(t):
        gi, gj = g_plan[k]
        ai, aj = a_plan[k]

        g_cells = footprint(gi, gj)
        a_cells = footprint(ai, aj)

        a_set = set(a_cells)
        g_set = set(g_cells)

        for (i, j) in g_cells:
            if (i, j) not in a_set:
                total_g += grid[i][j]
                grid[i][j] = 0

        for (i, j) in a_cells:
            if (i, j) not in g_set:
                total_a += grid[i][j]
                grid[i][j] = 0

    sys.stdout.write(f"{total_g} {total_a}\n")


if __name__ == "__main__":
    main()

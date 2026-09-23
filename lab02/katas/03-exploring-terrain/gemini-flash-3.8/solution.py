import sys


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    iterator = iter(input_data)
    n = int(next(iterator))
    m = int(next(iterator))
    t = int(next(iterator))

    grid = []
    for _ in range(n):
        row = [int(next(iterator)) for _ in range(m)]
        grid.append(row)

    gio_coords = []
    for _ in range(t):
        r = int(next(iterator)) - 1
        c = int(next(iterator)) - 1
        gio_coords.append((r, c))

    art_coords = []
    for _ in range(t):
        r = int(next(iterator)) - 1
        c = int(next(iterator)) - 1
        art_coords.append((r, c))

    g_total = 0
    a_total = 0

    deltas = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))

    for step in range(t):
        gr, gc = gio_coords[step]
        ar, ac = art_coords[step]

        # Giovana extrai células do seu alcance que não estão no alcance de Arthur
        for dr, dc in deltas:
            r, c = gr + dr, gc + dc
            if 0 <= r < n and 0 <= c < m:
                if abs(r - ar) + abs(c - ac) > 1:
                    val = grid[r][c]
                    if val:
                        g_total += val
                        grid[r][c] = 0

        # Arthur extrai células do seu alcance que não estão no alcance de Giovana
        for dr, dc in deltas:
            r, c = ar + dr, ac + dc
            if 0 <= r < n and 0 <= c < m:
                if abs(r - gr) + abs(c - gc) > 1:
                    val = grid[r][c]
                    if val:
                        a_total += val
                        grid[r][c] = 0

    sys.stdout.write(f"{g_total} {a_total}\n")


if __name__ == "__main__":
    solve()

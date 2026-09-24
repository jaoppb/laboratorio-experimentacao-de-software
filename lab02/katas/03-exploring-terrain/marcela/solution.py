import sys


def solve() -> None:
    raw = sys.stdin.buffer.read().split()
    if not raw:
        return
    n, m, t = int(raw[0]), int(raw[1]), int(raw[2])
    idx = 3

    grid = []
    for _ in range(n):
        grid.append([int(x) for x in raw[idx : idx + m]])
        idx += m

    g_coords = []
    for _ in range(t):
        g_coords.append((int(raw[idx]), int(raw[idx + 1])))
        idx += 2

    a_coords = []
    for _ in range(t):
        a_coords.append((int(raw[idx]), int(raw[idx + 1])))
        idx += 2

    def get_reach(r: int, c: int) -> list[tuple[int, int]]:
        cells = [(r, c)]
        if r > 1:
            cells.append((r - 1, c))
        if r < n:
            cells.append((r + 1, c))
        if c > 1:
            cells.append((r, c - 1))
        if c < m:
            cells.append((r, c + 1))
        return cells

    points_g = 0
    points_a = 0

    for step in range(t):
        cells_g = get_reach(*g_coords[step])
        cells_a = get_reach(*a_coords[step])
        both = set(cells_g) & set(cells_a)

        for r, c in cells_g:
            if (r, c) not in both:
                points_g += grid[r - 1][c - 1]
                grid[r - 1][c - 1] = 0

        for r, c in cells_a:
            if (r, c) not in both:
                points_a += grid[r - 1][c - 1]
                grid[r - 1][c - 1] = 0

    print(points_g, points_a)


if __name__ == "__main__":
    solve()

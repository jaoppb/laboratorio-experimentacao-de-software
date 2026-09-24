import sys


def main() -> None:
    tokens = sys.stdin.read().split()
    if not tokens:
        return
    n = int(tokens[0])
    grid = [list(r) for r in tokens[1 : n + 1]]

    deltas = ((-1, -1), (-1, 1), (1, -1), (1, 1))
    max_captures = 0

    def backtrack(r: int, c: int, count: int) -> None:
        nonlocal max_captures
        if count > max_captures:
            max_captures = count

        for dr, dc in deltas:
            mid_r, mid_c = r + dr, c + dc
            land_r, land_c = r + 2 * dr, c + 2 * dc
            if 0 <= land_r < n and 0 <= land_c < n:
                if grid[mid_r][mid_c] == "P" and grid[land_r][land_c] == ".":
                    grid[mid_r][mid_c] = "."
                    grid[r][c] = "."
                    grid[land_r][land_c] = "B"
                    backtrack(land_r, land_c, count + 1)
                    grid[land_r][land_c] = "."
                    grid[r][c] = "B"
                    grid[mid_r][mid_c] = "P"

    for row in range(n):
        for col in range(n):
            if grid[row][col] == "B":
                backtrack(row, col, 0)

    print(max_captures)


if __name__ == "__main__":
    main()

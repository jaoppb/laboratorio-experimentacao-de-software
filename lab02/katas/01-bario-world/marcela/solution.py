import sys


def solve_case(n: int, s: str) -> int:
    if n <= 1:
        return 0

    run = [0] * (n + 1)
    for j in range(n - 1, -1, -1):
        if s[j] == "x":
            run[j] = run[j + 1] + 1
        else:
            run[j] = 0

    jumps = 0
    cur_limit = 0
    max_reach = 0

    for i in range(n):
        if i > cur_limit:
            break
        if s[i] == "x":
            k = run[i + 1] if i + 1 < n else 0
            if i + k >= n - 1:
                return jumps
            reach = i + 2 * k + 1
            if reach > max_reach:
                max_reach = reach
        if i == cur_limit:
            if max_reach <= cur_limit:
                return -1
            jumps += 1
            cur_limit = max_reach

    return -1


def main() -> None:
    data = sys.stdin.read().split()
    if not data:
        return
    t = int(data[0])
    idx = 1
    results = []
    for _ in range(t):
        n = int(data[idx])
        s = data[idx + 1]
        idx += 2
        results.append(str(solve_case(n, s)))
    print("\n".join(results))


if __name__ == "__main__":
    main()

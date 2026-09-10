import sys


def solve(n, s):
    if n == 1:
        return 0
    run = [0] * (n + 1)
    for j in range(n - 1, -1, -1):
        run[j] = run[j + 1] + 1 if s[j] == "x" else 0

    jumps = 0
    cur_end = 0
    farthest = 0
    for i in range(n):
        if i > cur_end:
            break
        if s[i] == "x":
            k = run[i + 1] if i + 1 < n else 0
            if i + k >= n - 1:
                return jumps
            reach = i + 2 * k + 1
            if reach > farthest:
                farthest = reach
        if i == cur_end:
            if farthest <= cur_end:
                return -1
            jumps += 1
            cur_end = farthest
    return -1


def main():
    data = sys.stdin.read().split()
    t = int(data[0])
    idx = 1
    out = []
    for _ in range(t):
        n = int(data[idx])
        s = data[idx + 1]
        idx += 2
        out.append(str(solve(n, s)))
    print("\n".join(out))


main()

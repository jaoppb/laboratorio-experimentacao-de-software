def solve(n, s):
    if n == 1:
        return 0

    run_end = [0] * n
    i = 0
    while i < n:
        if s[i] == "x":
            j = i
            while j < n and s[j] == "x":
                j += 1
            for k in range(i, j):
                run_end[k] = j - 1
            i = j
        else:
            i += 1

    jumps = 0
    cur_end = 0
    farthest = 0
    pos = 0
    while pos < n and pos <= cur_end:
        if s[pos] == "x":
            if run_end[pos] >= n - 1:
                return jumps
            charge = 1 + (run_end[pos] - pos)
            reach = run_end[pos] + charge
            if reach > farthest:
                farthest = reach
        if pos == cur_end:
            if farthest <= cur_end:
                return -1
            jumps += 1
            cur_end = farthest
        pos += 1

    return -1


def main():
    t = int(input())
    out = []
    for _ in range(t):
        n = int(input())
        s = input().strip()
        out.append(str(solve(n, s)))
    print("\n".join(out))


main()

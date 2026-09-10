import sys


def main():
    data = sys.stdin.buffer.read().split()
    pos = 0
    n, m, t = int(data[0]), int(data[1]), int(data[2])
    pos = 3
    ore = []
    for _ in range(n):
        ore.append([int(x) for x in data[pos : pos + m]])
        pos += m
    g_plan = []
    for _ in range(t):
        g_plan.append((int(data[pos]), int(data[pos + 1])))
        pos += 2
    a_plan = []
    for _ in range(t):
        a_plan.append((int(data[pos]), int(data[pos + 1])))
        pos += 2

    def cells(i, j):
        out = [(i, j)]
        if i > 1:
            out.append((i - 1, j))
        if i < n:
            out.append((i + 1, j))
        if j > 1:
            out.append((i, j - 1))
        if j < m:
            out.append((i, j + 1))
        return out

    total_g = 0
    total_a = 0
    for step in range(t):
        gc = cells(*g_plan[step])
        ac = cells(*a_plan[step])
        shared = set(gc) & set(ac)
        for i, j in gc:
            if (i, j) not in shared:
                total_g += ore[i - 1][j - 1]
                ore[i - 1][j - 1] = 0
        for i, j in ac:
            if (i, j) not in shared:
                total_a += ore[i - 1][j - 1]
                ore[i - 1][j - 1] = 0

    print(total_g, total_a)


main()

def rvi(n):
    return [list(map(int, input().split())) for _ in range(n)]

def in_range(pos):
    return 0 <= pos[0] < N and 0 <= pos[1] < M

N, M, T = map(int, input().split())

ores = rvi(N)
g_extracts = [[x - 1, y - 1] for x, y in rvi(T)]
a_extracts = [[x - 1, y - 1] for x, y in rvi(T)]

G = 0
A = 0

for i in range(T):
    g_pos = set()
    a_pos = set()

    for ox, oy in [[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1]]:
        gp = (g_extracts[i][0] + ox, g_extracts[i][1] + oy)
        if in_range(gp):
            g_pos.add(gp)

        ap = (a_extracts[i][0] + ox, a_extracts[i][1] + oy)
        if in_range(ap):
            a_pos.add(ap)

    contested = g_pos & a_pos
    g_pos -= contested
    a_pos -= contested

    for p in g_pos:
        G += ores[p[0]][p[1]]
        ores[p[0]][p[1]] = 0

    for p in a_pos:
        A += ores[p[0]][p[1]]
        ores[p[0]][p[1]] = 0

print(G, A)

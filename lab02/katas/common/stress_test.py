"""Stress test: compara cada gabarito com uma implementacao independente
(forca bruta) em milhares de entradas pequenas aleatorias."""

import random
import subprocess
import sys
from pathlib import Path
from collections import deque

GAB = Path(__file__).resolve().parent.parent / "gabaritos"


def run_gab(kata, stdin_text):
    p = subprocess.run(
        [sys.executable, str(GAB / f"{kata}.py")],
        input=stdin_text,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"{kata} falhou: {p.stderr}")
    return p.stdout.strip()


# ---------------------------------------------------------------- 01 Bario
def brute_bario(n, s):
    run = [0] * (n + 1)
    for j in range(n - 1, -1, -1):
        run[j] = run[j + 1] + 1 if s[j] == "x" else 0

    def covered(p):
        return p + (run[p + 1] if p + 1 < n else 0)

    if covered(0) >= n - 1:
        return 0
    dist = {0: 0}
    q = deque([0])
    while q:
        p = q.popleft()
        k = run[p + 1] if p + 1 < n else 0
        targets = set()
        for r in range(k + 1):
            for t in range(p + r + 1, min(p + 2 * r + 1, n - 1) + 1):
                if s[t] == "x":
                    targets.add(t)
        for t in sorted(targets):
            if t not in dist:
                dist[t] = dist[p] + 1
                if covered(t) >= n - 1:
                    return dist[t]
                q.append(t)
    return -1


def stress_bario(rounds=400):
    for _ in range(rounds):
        cases = []
        for _ in range(random.randint(1, 4)):
            n = random.randint(2, 12)
            s = "x" + "".join(random.choice("x.") for _ in range(n - 2)) + "x"
            cases.append((n, s))
        stdin = f"{len(cases)}\n" + "".join(f"{n}\n{s}\n" for n, s in cases)
        got = run_gab("01-bario-world", stdin).split("\n")
        exp = [str(brute_bario(n, s)) for n, s in cases]
        if got != exp:
            return f"BARIO divergiu\nentrada:\n{stdin}got={got}\nexp={exp}"
    return None


# ---------------------------------------------------------------- 02 Cards
def brute_cards(n, cards):
    table = []
    out = []
    for i, c in enumerate(cards, start=1):
        vals = [v for v, _ in table]
        if c in vals:
            pos = vals.index(c)
            table = table[pos + 1 :]
        table.append((c, i))
        best = max(table)
        out.append(f"{best[0]} {best[1]}")
    return out


def stress_cards(rounds=400):
    for _ in range(rounds):
        n = random.randint(1, 12)
        cards = [random.randint(1, n) for _ in range(n)]
        stdin = f"{n}\n{' '.join(map(str, cards))}\n"
        got = run_gab("02-cards", stdin).split("\n")
        exp = brute_cards(n, cards)
        if got != exp:
            return f"CARDS divergiu\nentrada:\n{stdin}got={got}\nexp={exp}"
    return None


# ---------------------------------------------------- 03 Exploring the Terrain
def brute_terrain(n, m, grid, gp, ap):
    ore = {(i + 1, j + 1): grid[i][j] for i in range(n) for j in range(m)}
    tg = ta = 0
    for (gi, gj), (ai, aj) in zip(gp, ap):
        want_g, want_a = set(), set()
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if abs(i - gi) + abs(j - gj) <= 1:
                    want_g.add((i, j))
                if abs(i - ai) + abs(j - aj) <= 1:
                    want_a.add((i, j))
        both = want_g & want_a
        for cell in want_g - both:
            tg += ore[cell]
            ore[cell] = 0
        for cell in want_a - both:
            ta += ore[cell]
            ore[cell] = 0
    return f"{tg} {ta}"


def stress_terrain(rounds=300):
    for _ in range(rounds):
        n = random.randint(1, 5)
        m = random.randint(1, 5)
        t = random.randint(1, min(6, n * m))
        grid = [[random.randint(1, 20) for _ in range(m)] for _ in range(n)]
        gp = [(random.randint(1, n), random.randint(1, m)) for _ in range(t)]
        ap = [(random.randint(1, n), random.randint(1, m)) for _ in range(t)]
        stdin = f"{n} {m} {t}\n"
        stdin += "".join(" ".join(map(str, row)) + "\n" for row in grid)
        stdin += "".join(f"{i} {j}\n" for i, j in gp)
        stdin += "".join(f"{i} {j}\n" for i, j in ap)
        got = run_gab("03-exploring-terrain", stdin)
        exp = brute_terrain(n, m, grid, gp, ap)
        if got != exp:
            return f"TERRAIN divergiu\nentrada:\n{stdin}got={got}\nexp={exp}"
    return None


# ------------------------------------------------------------ 04 Garment
def brute_garment(n, g):
    """Enumera todas as composicoes de n camisas em g grupos e pega o minimo."""
    best = None
    def rec(restante, grupos, acc):
        nonlocal best
        if grupos == 0:
            if restante == 0 and (best is None or acc < best):
                best = acc
            return
        for tam in range(1, restante - grupos + 2):
            rec(restante - tam, grupos - 1, acc + tam + 1)
    rec(n, g, 0)
    return str(best)


def stress_garment(rounds=60):
    for _ in range(rounds):
        n = random.randint(1, 9)
        g = random.randint(1, n)
        stdin = f"{n} {g}\n"
        got = run_gab("04-garment-groups", stdin)
        exp = brute_garment(n, g)
        if got != exp:
            return f"GARMENT divergiu\nentrada: {stdin}got={got}\nexp={exp}"
    return None


# ------------------------------------------------------------ 05 Dish Rack
def brute_dish(n, c):
    """DP exaustiva sobre mascaras de ocupacao: custo minimo real."""
    INF = float("inf")
    dp = [INF] * (1 << n)
    dp[0] = 0
    best = INF
    for mask in range(1 << n):
        if dp[mask] == INF:
            continue
        if bin(mask).count("1") == c:
            best = min(best, dp[mask])
            continue
        for p in range(n):
            if mask & (1 << p):
                continue
            left = 0
            q = p - 1
            while q >= 0 and mask & (1 << q):
                left += 1
                q -= 1
            right = 0
            q = p + 1
            while q < n and mask & (1 << q):
                right += 1
                q += 1
            nm = mask | (1 << p)
            if dp[mask] + left + right < dp[nm]:
                dp[nm] = dp[mask] + left + right
    return best


def stress_dish(rounds=1):
    for n in range(2, 15):
        for c in range(1, n + 1):
            stdin = f"{n} {c}\n"
            got = int(run_gab("05-dish-rack", stdin).split("\n")[0])
            exp = brute_dish(n, c)
            if got != exp:
                return f"DISH divergiu em n={n} c={c}: got={got} exp={exp}"
    return None


# ------------------------------------------------------------ 06 N-Checkers
def brute_checkers(n, board):
    """Mesma regra, implementacao independente: BFS sobre estados completos."""
    grid = [list(r) for r in board]
    best = 0
    start_states = []
    for r in range(n):
        for c in range(n):
            if grid[r][c] == "B":
                start_states.append((tuple(tuple(x) for x in grid), r, c, 0))
    stack = list(start_states)
    seen = set()
    while stack:
        state, r, c, taken = stack.pop()
        if taken > best:
            best = taken
        key = (state, r, c)
        if key in seen:
            continue
        seen.add(key)
        for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            mr, mc, lr, lc = r + dr, c + dc, r + 2 * dr, c + 2 * dc
            if not (0 <= lr < n and 0 <= lc < n):
                continue
            if state[mr][mc] != "P" or state[lr][lc] != ".":
                continue
            g = [list(x) for x in state]
            g[mr][mc] = "."
            g[r][c] = "."
            g[lr][lc] = "B"
            stack.append((tuple(tuple(x) for x in g), lr, lc, taken + 1))
    return str(best)


def stress_checkers(rounds=200):
    for _ in range(rounds):
        n = random.choice([4, 6, 8])
        grid = [["." for _ in range(n)] for _ in range(n)]
        blacks = [(r, c) for r in range(n) for c in range(n) if (r + c) % 2 == 1]
        random.shuffle(blacks)
        npieces = random.randint(2, max(2, len(blacks) // 3))
        chosen = blacks[:npieces]
        grid[chosen[0][0]][chosen[0][1]] = "B"
        grid[chosen[1][0]][chosen[1][1]] = "P"
        for r, c in chosen[2:]:
            grid[r][c] = random.choice("BP")
        board = ["".join(row) for row in grid]
        stdin = f"{n}\n" + "\n".join(board) + "\n"
        got = run_gab("06-n-checkers", stdin)
        exp = brute_checkers(n, board)
        if got != exp:
            return f"CHECKERS divergiu\nentrada:\n{stdin}got={got}\nexp={exp}"
    return None


if __name__ == "__main__":
    random.seed(20260909)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    checks = {
        "bario": stress_bario,
        "cards": stress_cards,
        "terrain": stress_terrain,
        "garment": stress_garment,
        "dish": stress_dish,
        "checkers": stress_checkers,
    }
    for name, fn in checks.items():
        if which not in ("all", name):
            continue
        err = fn()
        print(f"{name}: {'OK' if err is None else err}")

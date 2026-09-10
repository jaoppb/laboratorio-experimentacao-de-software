import sys

sys.setrecursionlimit(10000)

_memo = {0: 0, 1: 0}


def cost(m):
    if m in _memo:
        return _memo[m]
    stack = [m]
    while stack:
        cur = stack[-1]
        if cur in _memo:
            stack.pop()
            continue
        left = (cur - 1) // 2
        right = cur - 1 - left
        missing = [x for x in (left, right) if x not in _memo]
        if missing:
            stack.extend(missing)
            continue
        _memo[cur] = _memo[left] + _memo[right] + (cur - 1)
        stack.pop()
    return _memo[m]


def build(l, r, out):
    """Ordem de insercao de um bloco contiguo [l, r]: sub-blocos primeiro, raiz
    por ultimo (a ultima insercao e a que funde os dois lados)."""
    stack = [(l, r, False)]
    while stack:
        lo, hi, emit = stack.pop()
        if lo > hi:
            continue
        size = hi - lo + 1
        root = lo + (size - 1) // 2
        if emit:
            out.append(root)
            continue
        stack.append((lo, hi, True))
        stack.append((root + 1, hi, False))
        stack.append((lo, root - 1, False))


def main():
    n, c = map(int, sys.stdin.read().split())

    blocks = min(c, n - c + 1)
    base, extra = divmod(c, blocks)
    sizes = [base + 1] * extra + [base] * (blocks - extra)

    total = sum(cost(s) for s in sizes)

    order = []
    pos = 1
    for s in sizes:
        build(pos, pos + s - 1, order)
        pos += s + 1

    print(total)
    print(" ".join(map(str, order)))


main()

def build_block(l, r, seq):
    size = r - l + 1
    if size <= 0:
        return 0
    if size == 1:
        seq.append(l)
        return 0

    remaining = size - 1
    left_size = remaining // 2
    right_size = remaining - left_size
    root = l + left_size

    cost = build_block(l, root - 1, seq)
    cost += build_block(root + 1, r, seq)
    seq.append(root)
    cost += left_size + right_size
    return cost


N, C = map(int, input().split())

if N >= 2 * C - 1:
    seq = list(range(1, 2 * C, 2))
    total_cost = 0
else:
    m = N - C + 1
    base = C // m
    extra = C % m
    sizes = [base + 1] * extra + [base] * (m - extra)

    seq = []
    total_cost = 0
    cur = 1
    for size in sizes:
        total_cost += build_block(cur, cur + size - 1, seq)
        cur += size + 1

print(total_cost)
print(' '.join(map(str, seq)))

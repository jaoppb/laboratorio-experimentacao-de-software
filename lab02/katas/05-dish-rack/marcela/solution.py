import sys

sys.setrecursionlimit(200000)


def calculate_component_cost(s: int) -> int:
    if s <= 1:
        return 0
    total = 0
    depth = 0
    rem = s
    count = 1
    while rem > 0:
        take = min(rem, count)
        total += take * depth
        rem -= take
        depth += 1
        count *= 2
    return total


def build_post_order(l: int, r: int, out: list[int]) -> None:
    if l > r:
        return
    if l == r:
        out.append(l)
        return
    m = (l + r) // 2
    build_post_order(l, m - 1, out)
    build_post_order(m + 1, r, out)
    out.append(m)


def main() -> None:
    data = sys.stdin.read().split()
    if not data:
        return
    n = int(data[0])
    c = int(data[1])

    k = min(c, n - c + 1)
    q, r = divmod(c, k)

    total_cost = r * calculate_component_cost(q + 1) + (k - r) * calculate_component_cost(q)

    order = []
    curr = 1
    for i in range(k):
        sz = q + 1 if i < r else q
        build_post_order(curr, curr + sz - 1, order)
        curr += sz + 1

    sys.stdout.write(f"{total_cost}\n")
    sys.stdout.write(" ".join(map(str, order)) + "\n")


if __name__ == "__main__":
    main()

import sys


def build_block(L, R, seq_out):
    """Iteratively build the minimal-cost insertion sequence for a single
    contiguous block occupying positions [L, R] (inclusive).

    The optimal strategy for filling one isolated block of size s (no
    interaction with other blocks) is equivalent to constructing a balanced
    binary-search-tree over the s positions, where a node is physically
    "placed" only after both of its children's subtrees are fully placed
    (post-order). Placing a node then costs (left subtree size + right
    subtree size), because at that moment those subtrees form two
    contiguous runs immediately adjacent to the node's position.

    Returns the total cost contributed by this block.
    """
    total_cost = 0
    # Stack holds either ('E', l, r) meaning "expand/process this range"
    # or ('R', root, leftSize, rightSize) meaning "emit this root now".
    stack = [('E', L, R)]
    while stack:
        op = stack.pop()
        if op[0] == 'E':
            _, l, r = op
            size = r - l + 1
            if size <= 0:
                continue
            if size == 1:
                seq_out.append(l)
                continue
            remaining = size - 1
            left_size = remaining // 2
            right_size = remaining - left_size
            root = l + left_size
            stack.append(('R', root, left_size, right_size))
            stack.append(('E', root + 1, r))
            stack.append(('E', l, root - 1))
        else:
            _, root, ls, rs = op
            seq_out.append(root)
            total_cost += ls + rs
    return total_cost


def solve():
    data = sys.stdin.read().split()
    n, c = int(data[0]), int(data[1])

    seq = []

    if n >= 2 * c - 1:
        # Enough room to place every cup with empty neighbors on both
        # sides: zero cost is achievable and clearly optimal.
        seq = list(range(1, 2 * c, 2))
        total_cost = 0
    else:
        # Not enough room to keep every cup isolated. Use as many
        # separate blocks as the available space allows (more, smaller
        # blocks are never worse than fewer, larger ones), and split the
        # cups across those blocks as evenly as possible.
        m = n - c + 1
        base = c // m
        extra = c % m
        sizes = [base + 1] * extra + [base] * (m - extra)

        total_cost = 0
        cur = 1
        for s in sizes:
            left = cur
            right = cur + s - 1
            total_cost += build_block(left, right, seq)
            cur = right + 2  # skip exactly one gap position

    out = []
    out.append(str(total_cost))
    out.append(' '.join(map(str, seq)))
    sys.stdout.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    solve()

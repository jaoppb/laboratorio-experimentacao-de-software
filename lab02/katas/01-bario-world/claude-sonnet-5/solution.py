import sys


def solve(n, s):
    if n <= 1:
        return 0
    target = n - 1

    # Index of the last hole in the whole strip. Once the reachable frontier
    # passes this point, the rest of the way to the finish is solid ground,
    # so Bario can just run there for free (no extra jump needed).
    last_hole = s.rfind('.')
    if last_hole == -1:
        return 0

    # run[i] = length of the maximal run of solid blocks starting at index i
    # (0 if s[i] is a hole). Sentinel run[n] = 0.
    run = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        if s[i] == 'x':
            run[i] = run[i + 1] + 1
        else:
            run[i] = 0

    jumps = 0
    cur_end = 0
    i = 0
    while True:
        if cur_end >= target or cur_end > last_hole:
            return jumps

        layer_farthest = -1
        j = i
        while j <= cur_end:
            if s[j] == 'x':
                r = run[j + 1]
                if r > 0:
                    reach = j + 2 * r + 1
                    if reach > layer_farthest:
                        layer_farthest = reach
            j += 1
        i = cur_end + 1
        if layer_farthest <= cur_end:
            return -1
        jumps += 1
        cur_end = layer_farthest if layer_farthest < target else target


def main():
    data = sys.stdin.buffer.read().split()
    idx = 0
    t = int(data[idx])
    idx += 1
    out = []
    for _ in range(t):
        n = int(data[idx])
        idx += 1
        s = data[idx].decode()
        idx += 1
        out.append(str(solve(n, s)))
    sys.stdout.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()

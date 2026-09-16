import sys
from collections import deque


def main() -> None:
    data = sys.stdin.read().split()
    idx = 0
    n = int(data[idx]); idx += 1
    cards = data[idx:idx + n]

    last_seen = [0] * (n + 1)  # 1-indexed value -> last position seen (0 = never)
    start = 1  # start of current window (1-indexed position)

    # monotonic deque of (value, position), decreasing values front->back
    dq = deque()

    out = []
    for t in range(1, n + 1):
        value = int(cards[t - 1])

        if last_seen[value] >= start:
            start = last_seen[value] + 1
        last_seen[value] = t

        while dq and dq[-1][0] < value:
            dq.pop()
        dq.append((value, t))

        while dq and dq[0][1] < start:
            dq.popleft()

        out.append(f"{dq[0][0]} {dq[0][1]}")

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()

import heapq
import sys
from collections import deque


def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    cards = list(map(int, data[1 : 1 + n]))

    present = [False] * (n + 2)
    holder = [0] * (n + 2)
    table = deque()
    heap = []
    out = []

    for i, c in enumerate(cards, start=1):
        if present[c]:
            while True:
                v, _ = table.popleft()
                present[v] = False
                if v == c:
                    break
        table.append((c, i))
        present[c] = True
        holder[c] = i
        heapq.heappush(heap, -c)
        while not present[-heap[0]]:
            heapq.heappop(heap)
        top = -heap[0]
        out.append(f"{top} {holder[top]}")

    print("\n".join(out))


main()

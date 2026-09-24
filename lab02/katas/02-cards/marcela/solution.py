import heapq
import sys
from collections import deque


def main() -> None:
    tokens = sys.stdin.read().split()
    if not tokens:
        return
    n = int(tokens[0])
    cards = [int(x) for x in tokens[1 : n + 1]]

    in_table = [False] * (n + 2)
    pos_map = [0] * (n + 2)
    queue = deque()
    max_heap = []
    res = []

    for idx, card in enumerate(cards, start=1):
        if in_table[card]:
            while True:
                elem, _ = queue.popleft()
                in_table[elem] = False
                if elem == card:
                    break
        queue.append((card, idx))
        in_table[card] = True
        pos_map[card] = idx
        heapq.heappush(max_heap, -card)

        while not in_table[-max_heap[0]]:
            heapq.heappop(max_heap)

        top_val = -max_heap[0]
        res.append(f"{top_val} {pos_map[top_val]}")

    print("\n".join(res))


if __name__ == "__main__":
    main()

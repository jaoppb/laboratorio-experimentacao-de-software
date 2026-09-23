import heapq
import sys


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    cards = [int(x) for x in input_data[1 : n + 1]]

    # active_player[val] guarda o índice do jogador que jogou a carta val atualmente na mesa
    # 0 indica que a carta val não está na mesa
    active_player = [0] * (n + 1)

    q = []
    head = 0
    max_heap = []
    out = []

    for player_idx, c in enumerate(cards, 1):
        if active_player[c] != 0:
            # A carta já está na mesa: remove do início até (e incluindo) a carta c
            while head < len(q):
                val, p = q[head]
                head += 1
                active_player[val] = 0
                if val == c:
                    break

        # Adiciona a nova carta à mesa
        q.append((c, player_idx))
        active_player[c] = player_idx
        heapq.heappush(max_heap, (-c, player_idx))

        # Lazy deletion no heap
        while max_heap and active_player[-max_heap[0][0]] != max_heap[0][1]:
            heapq.heappop(max_heap)

        top_c, top_player = -max_heap[0][0], max_heap[0][1]
        out.append(f"{top_c} {top_player}")

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    solve()

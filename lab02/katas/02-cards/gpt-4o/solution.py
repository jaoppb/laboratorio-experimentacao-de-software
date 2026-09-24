"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 02-cards."""

import heapq
import sys
from collections import deque


def simulate_card_game() -> None:
    raw_input = sys.stdin.read().split()
    if not raw_input:
        return
    n = int(raw_input[0])
    sequence = [int(v) for v in raw_input[1 : n + 1]]

    on_board = [False] * (n + 2)
    turn_placed = [0] * (n + 2)
    board_queue = deque()
    max_heap = []
    output_lines = []

    for turn, card in enumerate(sequence, start=1):
        if on_board[card]:
            while True:
                removed_card, _ = board_queue.popleft()
                on_board[removed_card] = False
                if removed_card == card:
                    break

        board_queue.append((card, turn))
        on_board[card] = True
        turn_placed[card] = turn
        heapq.heappush(max_heap, -card)

        while max_heap and not on_board[-max_heap[0]]:
            heapq.heappop(max_heap)

        strongest = -max_heap[0]
        output_lines.append(f"{strongest} {turn_placed[strongest]}")

    print("\n".join(output_lines))


if __name__ == "__main__":
    simulate_card_game()

#!/usr/bin/env python3
"""
Kata 02 — Cards
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Simulação com deque + max-heap (lazy deletion) em O(N log N).
"""

import heapq
import sys
from collections import deque


def main() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    cards = [int(x) for x in input_data[1 : n + 1]]

    table_q: deque[tuple[int, int]] = deque()
    in_table: dict[int, int] = {}
    max_heap: list[tuple[int, int]] = []
    output_lines: list[str] = []

    for i in range(1, n + 1):
        card_val = cards[i - 1]

        if card_val in in_table:
            # Elimina todas as cartas do início até (e incluindo) a carta com esse valor
            while table_q:
                old_val, old_player = table_q.popleft()
                del in_table[old_val]
                if old_val == card_val:
                    break

        # Adiciona a nova carta ao final
        table_q.append((card_val, i))
        in_table[card_val] = i
        heapq.heappush(max_heap, (-card_val, i))

        # Consulta a carta de maior valor na mesa (remoção preguiçosa no heap)
        while max_heap:
            neg_val, player_idx = max_heap[0]
            val = -neg_val
            if in_table.get(val) == player_idx:
                output_lines.append(f"{val} {player_idx}")
                break
            heapq.heappop(max_heap)

    sys.stdout.write("\n".join(output_lines) + "\n")


if __name__ == "__main__":
    main()

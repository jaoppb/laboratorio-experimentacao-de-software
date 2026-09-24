"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 05-dish-rack."""

import sys

sys.setrecursionlimit(200000)


def compute_minimum_effort(size: int) -> int:
    """Calcula o esforço mínimo para preencher uma componente contígua de tamanho size."""
    if size <= 1:
        return 0
    total_cost = 0
    tree_depth = 0
    remaining = size
    capacity = 1
    while remaining > 0:
        allocated = min(remaining, capacity)
        total_cost += allocated * tree_depth
        remaining -= allocated
        tree_depth += 1
        capacity *= 2
    return total_cost


def construct_traversal(start_idx: int, end_idx: int, sequence: list[int]) -> None:
    """Monta a ordem pós-ordem de colocação dos copos no intervalo."""
    if start_idx > end_idx:
        return
    if start_idx == end_idx:
        sequence.append(start_idx)
        return
    mid = (start_idx + end_idx) // 2
    construct_traversal(start_idx, mid - 1, sequence)
    construct_traversal(mid + 1, end_idx, sequence)
    sequence.append(mid)


def solve_dish_rack_problem() -> None:
    tokens = sys.stdin.read().split()
    if not tokens:
        return
    total_slots = int(tokens[0])
    num_cups = int(tokens[1])

    max_blocks = min(num_cups, total_slots - num_cups + 1)
    base_len, extra = divmod(num_cups, max_blocks)

    minimal_effort = extra * compute_minimum_effort(base_len + 1) + (max_blocks - extra) * compute_minimum_effort(base_len)

    cup_placement_order = []
    pointer = 1
    for block_idx in range(max_blocks):
        block_len = base_len + 1 if block_idx < extra else base_len
        construct_traversal(pointer, pointer + block_len - 1, cup_placement_order)
        pointer += block_len + 1

    sys.stdout.write(f"{minimal_effort}\n")
    sys.stdout.write(" ".join(map(str, cup_placement_order)) + "\n")


if __name__ == "__main__":
    solve_dish_rack_problem()

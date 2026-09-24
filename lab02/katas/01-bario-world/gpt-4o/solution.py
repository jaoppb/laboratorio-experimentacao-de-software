"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 01-bario-world."""

import sys


def compute_min_jumps(n: int, track: str) -> int:
    """Calcula a quantidade mínima de pulos para alcançar o final do percurso."""
    if n <= 1:
        return 0

    streak = [0] * (n + 1)
    for idx in range(n - 1, -1, -1):
        streak[idx] = streak[idx + 1] + 1 if track[idx] == "x" else 0

    total_jumps = 0
    current_frontier = 0
    farthest_reach = 0

    for pos in range(n):
        if pos > current_frontier:
            break
        if track[pos] == "x":
            extra_speed = streak[pos + 1] if pos + 1 < n else 0
            if pos + extra_speed >= n - 1:
                return total_jumps
            jump_dest = pos + 2 * extra_speed + 1
            if jump_dest > farthest_reach:
                farthest_reach = jump_dest

        if pos == current_frontier:
            if farthest_reach <= current_frontier:
                return -1
            total_jumps += 1
            current_frontier = farthest_reach

    return -1


def main() -> None:
    tokens = sys.stdin.read().split()
    if not tokens:
        return
    num_tests = int(tokens[0])
    cursor = 1
    outputs = []
    for _ in range(num_tests):
        size = int(tokens[cursor])
        track = tokens[cursor + 1]
        cursor += 2
        outputs.append(str(compute_min_jumps(size, track)))
    print("\n".join(outputs))


if __name__ == "__main__":
    main()

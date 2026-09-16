#!/usr/bin/env python3
"""
Kata 01 — Bario World
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Algoritmo Guloso (BFS / Jump Game) em O(N).
"""

import sys


def solve_case(n: int, s: str) -> int:
    segments: list[tuple[int, int]] = []
    in_segment = False
    start = 0

    for i, ch in enumerate(s):
        if ch == "x":
            if not in_segment:
                start = i
                in_segment = True
        else:
            if in_segment:
                segments.append((start, i - 1))
                in_segment = False
    if in_segment:
        segments.append((start, n - 1))

    if not segments or segments[0][0] != 0 or segments[-1][1] != n - 1:
        return -1

    if segments[0][1] == n - 1:
        return 0

    curr_reach = 2 * segments[0][1] - segments[0][0] + 1
    next_reach = curr_reach
    jumps = 1
    idx = 1
    m = len(segments)

    while idx < m:
        advanced = False
        while idx < m and segments[idx][0] <= curr_reach:
            advanced = True
            seg_start, seg_end = segments[idx]
            if seg_end == n - 1:
                return jumps
            reach = 2 * seg_end - seg_start + 1
            if reach > next_reach:
                next_reach = reach
            idx += 1

        if not advanced:
            return -1

        if next_reach <= curr_reach:
            return -1

        curr_reach = next_reach
        jumps += 1

    return -1


def main() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    t = int(input_data[0])
    ptr = 1
    results = []

    for _ in range(t):
        n = int(input_data[ptr])
        s = input_data[ptr + 1]
        ptr += 2
        results.append(str(solve_case(n, s)))

    sys.stdout.write("\n".join(results) + "\n")


if __name__ == "__main__":
    main()

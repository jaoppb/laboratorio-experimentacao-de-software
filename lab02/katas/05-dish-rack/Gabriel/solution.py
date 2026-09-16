#!/usr/bin/env python3
"""
Kata 05 — Loading the Dish Rack
Solução com IA (Gemini 3.8 Flash) para Gabriel Assis.
Divisão e conquista / árvore binária de fusões ótimas em O(C).
"""

import sys

# Aumenta limite de recursão por segurança, embora a profundidade da árvore seja O(log S) <= 25
sys.setrecursionlimit(200000)


def get_cost(s: int, memo: dict[int, int]) -> int:
    if s <= 1:
        return 0
    if s in memo:
        return memo[s]
    left = (s - 1) // 2
    right = s - 1 - left
    res = (s - 1) + get_cost(left, memo) + get_cost(right, memo)
    memo[s] = res
    return res


def generate_order(start: int, s: int, out: list[int]) -> None:
    if s <= 0:
        return
    if s == 1:
        out.append(start)
        return
    left_size = (s - 1) // 2
    right_size = s - 1 - left_size
    mid_pos = start + left_size

    # Preenche primeiro o sub-bloco esquerdo
    generate_order(start, left_size, out)
    # Preenche o sub-bloco direito
    generate_order(mid_pos + 1, right_size, out)
    # Por fim, insere o copo central unindo os dois sub-blocos
    out.append(mid_pos)


def main() -> None:
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    c = int(input_data[1])

    # K é o número máximo de blocos contíguos de copos separados por pelo menos 1 vazio
    # Cada vazio separa 2 blocos: C + K - 1 <= N => K <= N - C + 1
    k = min(c, n - c + 1)

    # Distribui os copos o mais uniformemente possível entre os K blocos
    q = c // k
    r = c % k

    memo: dict[int, int] = {}
    total_effort = r * get_cost(q + 1, memo) + (k - r) * get_cost(q, memo)

    block_sizes = [q + 1] * r + [q] * (k - r)

    positions: list[int] = []
    curr_start = 1
    for s in block_sizes:
        generate_order(curr_start, s, positions)
        curr_start += s + 1

    sys.stdout.write(f"{total_effort}\n")
    sys.stdout.write(" ".join(str(p) for p in positions) + "\n")


if __name__ == "__main__":
    main()

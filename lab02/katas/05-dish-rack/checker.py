#!/usr/bin/env python3
"""Checker do kata 05 - Loading the Dish Rack.

O kata aceita mais de uma resposta valida: o esforco minimo e unico, mas a
sequencia de insercao que o atinge nao e. Por isso a comparacao direta com o
.out oficial nao serve.

Este checker valida:
  1. a primeira linha da saida e igual ao esforco minimo esperado;
  2. a segunda linha tem C posicoes distintas dentro de [1, N];
  3. simular a sequencia informada, pela definicao do enunciado, produz
     exatamente o esforco declarado na primeira linha.

Uso: checker.py <arquivo.in> <arquivo.out esperado> <saida da solucao>
Codigo de saida 0 = passou.
"""

import sys


def fail(message):
    print(message)
    sys.exit(1)


def simulate(n, positions):
    """Esforco total da sequencia, pela definicao: soma dos comprimentos das
    sequencias de copos imediatamente a esquerda e a direita no momento da
    insercao. run[p] so e mantido nas pontas de cada bloco contiguo."""
    run = {}
    total = 0
    for p in positions:
        left = run.get(p - 1, 0)
        right = run.get(p + 1, 0)
        total += left + right
        size = left + right + 1
        run[p - left] = size
        run[p + right] = size
    return total


def main():
    if len(sys.argv) != 4:
        fail(f"uso: {sys.argv[0]} <in> <expected> <actual>")

    in_file, expected_file, actual_file = sys.argv[1:4]

    n, c = map(int, open(in_file).read().split())
    expected_effort = int(open(expected_file).read().split()[0])

    tokens = open(actual_file).read().split()
    if not tokens:
        fail("saida vazia")

    try:
        claimed_effort = int(tokens[0])
        positions = [int(t) for t in tokens[1:]]
    except ValueError:
        fail("saida contem valores nao inteiros")

    if len(positions) != c:
        fail(f"esperava {c} posicoes na segunda linha, recebi {len(positions)}")

    if any(p < 1 or p > n for p in positions):
        fail(f"ha posicoes fora do intervalo [1, {n}]")

    if len(set(positions)) != c:
        fail("ha posicoes repetidas: cada copo deve ir para uma posicao vazia")

    actual_effort = simulate(n, positions)
    if actual_effort != claimed_effort:
        fail(f"a sequencia informada custa {actual_effort}, mas a saida declara {claimed_effort}")

    if claimed_effort != expected_effort:
        fail(f"esforco {claimed_effort} nao e o minimo: o minimo e {expected_effort}")

    sys.exit(0)


if __name__ == "__main__":
    main()

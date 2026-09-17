import heapq
from collections import deque


def main():
    n = int(input())
    cards = list(map(int, input().split()))

    mesa = deque()
    na_mesa = [False] * (n + 2)
    dono = [0] * (n + 2)
    heap = []
    out = []

    for jogador, valor in enumerate(cards, start=1):
        if na_mesa[valor]:
            while mesa:
                v, _ = mesa.popleft()
                na_mesa[v] = False
                if v == valor:
                    break

        mesa.append((valor, jogador))
        na_mesa[valor] = True
        dono[valor] = jogador
        heapq.heappush(heap, -valor)

        while not na_mesa[-heap[0]]:
            heapq.heappop(heap)

        maior = -heap[0]
        out.append(f"{maior} {dono[maior]}")

    print("\n".join(out))


main()

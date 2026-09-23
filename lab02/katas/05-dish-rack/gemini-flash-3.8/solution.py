import sys

# Aumenta limite de recursão para árvore balanceada (profundidade <= 30)
sys.setrecursionlimit(200000)


def calc_cost(s):
    """Calcula o esforço mínimo para preencher um bloco contíguo de tamanho s.

    Corresponde à soma das profundidades em uma árvore binária quase completa de s nós.
    """
    if s <= 1:
        return 0
    total = 0
    depth = 0
    rem = s
    count = 1
    while rem > 0:
        take = min(rem, count)
        total += take * depth
        rem -= take
        depth += 1
        count *= 2
    return total


def generate_order(l, r, out):
    """Gera a ordem pós-ordem de inserção para o intervalo contíguo [l, r]."""
    if l > r:
        return
    if l == r:
        out.append(l)
        return
    m = (l + r) // 2
    generate_order(l, m - 1, out)
    generate_order(m + 1, r, out)
    out.append(m)


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    c = int(input_data[1])

    # Número máximo de componentes conexas que podemos formar com as posições vazias restantes
    # Cada componente é separada por pelo menos 1 posição vazia
    max_k = min(c, n - c + 1)

    # Dividimos C copos em max_k componentes com tamanhos o mais equilibrados possível
    q = c // max_k
    r = c % max_k

    # r componentes de tamanho q + 1, e (max_k - r) componentes de tamanho q
    total_effort = r * calc_cost(q + 1) + (max_k - r) * calc_cost(q)

    # Constrói os intervalos de cada componente no escorredor [1, N]
    positions_order = []
    curr_pos = 1

    for i in range(max_k):
        size = q + 1 if i < r else q
        comp_l = curr_pos
        comp_r = curr_pos + size - 1
        generate_order(comp_l, comp_r, positions_order)
        # Deixa 1 espaço vazio entre componentes consecutivas
        curr_pos = comp_r + 2

    sys.stdout.write(f"{total_effort}\n")
    sys.stdout.write(" ".join(map(str, positions_order)) + "\n")


if __name__ == "__main__":
    solve()

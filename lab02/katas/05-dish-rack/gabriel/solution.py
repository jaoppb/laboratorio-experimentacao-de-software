def custo_bloco(tamanho):
    if tamanho <= 1:
        return 0
    esquerda = (tamanho - 1) // 2
    direita = tamanho - 1 - esquerda
    return custo_bloco(esquerda) + custo_bloco(direita) + (tamanho - 1)


def ordem_bloco(inicio, fim, seq):
    tamanho = fim - inicio + 1
    if tamanho <= 0:
        return
    if tamanho == 1:
        seq.append(inicio)
        return
    esquerda = (tamanho - 1) // 2
    raiz = inicio + esquerda
    ordem_bloco(inicio, raiz - 1, seq)
    ordem_bloco(raiz + 1, fim, seq)
    seq.append(raiz)


def main():
    n, c = map(int, input().split())

    num_blocos = min(c, n - c + 1)
    base = c // num_blocos
    extra = c % num_blocos
    tamanhos = [base + 1] * extra + [base] * (num_blocos - extra)

    custo_total = sum(custo_bloco(t) for t in tamanhos)

    seq = []
    pos = 1
    for t in tamanhos:
        ordem_bloco(pos, pos + t - 1, seq)
        pos += t + 1

    print(custo_total)
    print(" ".join(map(str, seq)))


main()

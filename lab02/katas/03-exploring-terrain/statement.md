# Kata 03 — Exploring the Terrain

**Origem:** Problema E, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par B (junto com o Kata 02 — Cards).
**Técnica esperada:** simulação sobre matriz, com detecção de conflito entre as
duas máquinas no mesmo instante.

## Descrição

Uma mina é representada por uma matriz `N × M`, em que cada célula contém a
quantidade de minério obtida se aquela posição for perfurada. Giovana e Arthur
têm, cada um, uma perfuratriz e um plano de exploração de `T` minutos: o plano é
uma lista de `T` coordenadas, onde `(iₜ, jₜ)` é a posição da máquina no instante
`t`. Os dois planos são executados **simultaneamente** e têm a mesma duração.

Quando uma perfuratriz está na posição `(i, j)`, ela extrai minério da célula
`(i, j)` e das células `(i−1, j)`, `(i, j−1)`, `(i, j+1)`, `(i+1, j)` — mas
**somente se a outra perfuratriz não fosse extrair daquela mesma célula naquele
mesmo instante**. Se as duas fossem extrair a mesma célula no mesmo instante,
nenhuma das duas extrai, e o minério permanece intacto.

A extração é 100% eficiente: depois de extraído, o minério da célula é zero.

Imprima o total de minério extraído por cada perfuratriz.

## Entrada

A primeira linha contém três inteiros `N`, `M` e `T`
(1 ≤ N, M ≤ 500, 1 ≤ T ≤ N × M).

As `N` linhas seguintes contêm `M` inteiros cada (1 ≤ v ≤ 1000): o `j`-ésimo
número da `i`-ésima linha é o minério na posição `(i, j)`.

As `T` linhas seguintes contêm dois inteiros cada: a posição da perfuratriz de
**Giovana** no instante `t`.

As últimas `T` linhas contêm dois inteiros cada: a posição da perfuratriz de
**Arthur** no instante `t`.

## Saída

Dois números `G` e `A` separados por espaço — o total extraído por Giovana e por
Arthur, respectivamente.

## Exemplo

Entrada (`tests/test01.in`):

```
2 3 2
3 1 4
5 6 2
1 1
1 2
1 3
1 3
```

Saída (`tests/test01.out`):

```
14 6
```

No instante 1, Giovana está em `(1,1)` e Arthur em `(1,3)`: as duas disputariam a
célula `(1,2)`, então nenhuma a extrai.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

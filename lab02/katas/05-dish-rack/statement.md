# Kata 05 — Loading the Dish Rack

**Origem:** Problema L, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par C (junto com o Kata 06 — N-Checkers).
**Técnica esperada:** modelar o custo total como uma sequência de fusões de
blocos e construir a ordem de inserção ótima.

## Descrição

Beto precisa colocar `C` copos num escorredor linear com `N` posições
(numeradas de 1 a `N`). O **esforço** para colocar um copo numa posição é igual à
soma do número de copos consecutivos imediatamente à esquerda e do número de
copos consecutivos imediatamente à direita daquela posição **no momento da
colocação**.

Cada copo deve ir para uma posição vazia. Nem todas as posições precisam ser
usadas.

Calcule o esforço total mínimo para colocar todos os copos e forneça uma sequência
de inserção que atinja esse mínimo.

## Entrada

Uma única linha com dois inteiros `N` (2 ≤ N ≤ 10⁶) e `C` (1 ≤ C ≤ N), o tamanho
do escorredor e o número de copos.

## Saída

A primeira linha deve conter um único inteiro: o esforço total mínimo.

A segunda linha deve conter `C` inteiros separados por espaço, onde o `i`-ésimo
inteiro é a posição do escorredor em que o `i`-ésimo copo deve ser colocado.

**Se houver mais de uma sequência que atinja o mínimo, qualquer uma é aceita** —
por isso este kata tem um `checker.py` próprio, que valida a sequência em vez de
comparar a saída caractere a caractere.

## Exemplos

Entrada (`tests/test02.in`):

```
7 5
```

Saída (`tests/test02.out`, uma das válidas):

```
2
1 2 4 6 7
```

Uma forma de colocar os copos é `[1 2 _ 3 _ 4 5]`. Os copos 1, 3 e 4 têm custo 0;
os copos 2 e 5 têm custo 1 — esforço total 2.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

O `checker.py` verifica três coisas: que as `C` posições são distintas e válidas,
que simular a sequência informada produz exatamente o esforço declarado na
primeira linha, e que esse esforço é de fato o mínimo.

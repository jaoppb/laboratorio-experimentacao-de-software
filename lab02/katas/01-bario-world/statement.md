# Kata 01 — Bario World

**Origem:** Problema B, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par A (junto com o Kata 04 — Garment Groups).
**Técnica esperada:** greedy / alcance máximo em uma passada (`O(N)`).

## Descrição

Bario atravessa uma fase formada por `N` blocos, cada um sólido ou um buraco.
Ele começa no bloco 1 e precisa chegar ao bloco `N` sem cair em nenhum buraco.

As botas de Bario têm uma carga de energia, inicialmente igual a **1**. Enquanto
corre, ele carrega as botas: **cada bloco sólido percorrido correndo adiciona uma
unidade de carga**. Um pulo com carga `v` leva Bario do bloco `b` para qualquer
bloco de `b + 1` até `b + v`; ao aterrissar, as botas perdem a energia e voltam à
carga inicial 1.

Bario corre apenas sobre blocos sólidos — para passar por um buraco, ele precisa
pulá-lo. Correr não custa pulo: se o caminho até o fim for todo sólido, Bario
chega à posição `N` correndo, sem pular nenhuma vez.

Calcule o número mínimo de pulos para Bario chegar à posição `N`, ou informe que
é impossível.

## Entrada

A primeira linha contém um inteiro `T` (1 ≤ T ≤ 5×10⁵), o número de casos de
teste. A soma dos valores de `N` é menor que 5×10⁵.

Em seguida vêm `T` pares de linhas. A primeira linha de cada par contém `N`
(2 ≤ N ≤ 5×10⁵), o comprimento da fase; a segunda contém uma string de `N`
caracteres representando os blocos: `x` para bloco sólido e `.` para buraco. É
garantido que os blocos 1 e `N` são sólidos.

## Saída

Para cada caso de teste, imprima o número mínimo de pulos necessários para chegar
ao fim da fase, ou `-1` se for impossível.

## Exemplo

Entrada (`tests/test01.in`):

```
2
16
xxxxxxx.xxxx.x.x
3
x.x
```

Saída (`tests/test01.out`):

```
2
-1
```

No primeiro caso, uma solução com dois pulos: correr da posição 1 até a 5
(carregando as botas até energia 5) e pular até a posição 9; depois correr da
posição 9 até a 12 (energia 4) e pular até o fim.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

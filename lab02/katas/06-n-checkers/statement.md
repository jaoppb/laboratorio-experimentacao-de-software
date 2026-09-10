# Kata 06 — N-Checkers

**Origem:** Problema N, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par C (junto com o Kata 05 — Loading the Dish Rack).
**Técnica esperada:** busca em profundidade com backtracking sobre o tabuleiro.

## Descrição

O tabuleiro de `n`-damas é `n × n`, com casas alternando entre brancas e pretas, e
a casa do canto superior esquerdo é branca. Uma casa pode estar vazia ou, se for
preta, conter uma peça.

Na sua vez, o jogador escolhe uma de suas peças para mover. A peça escolhida pode
capturar uma peça adversária se essa peça estiver numa casa **diagonalmente
adjacente** e a casa seguinte na mesma direção diagonal estiver vazia. Nesse caso
a peça "pula" por cima da adversária, vai para a casa vazia imediatamente
seguinte, e a peça adversária é removida do tabuleiro. **Após uma captura, o
jogador pode continuar o movimento com a mesma peça.**

Pela regra da maioria, o jogador precisa realizar a sequência de movimentos que
resulte no maior número possível de peças capturadas.

Bob joga com as peças brancas. Determine o número máximo de peças que Bob pode
capturar em uma sequência de movimentos.

## Entrada

A primeira linha contém um inteiro `n` (4 ≤ n ≤ 14), a dimensão do tabuleiro.

Seguem `n` linhas com `n` caracteres cada, representando o tabuleiro. Cada linha
contém apenas os caracteres `B`, `P` e `.`, representando peças brancas (de Bob),
peças pretas (da adversária) e casas vazias, respectivamente.

O tabuleiro contém ao menos uma peça de cada cor, e nenhuma peça está em casa
branca.

## Saída

Um único inteiro: o número máximo de peças que Bob pode capturar.

## Exemplo

Entrada (`tests/test02.in`):

```
8
........
..P.P.P.
........
..P.P.P.
.......B
....P...
...B....
........
```

Saída (`tests/test02.out`):

```
6
```

Uma das peças de Bob consegue capturar seis peças adversárias numa única
sequência.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

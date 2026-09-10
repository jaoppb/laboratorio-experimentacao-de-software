# Kata 02 — Cards

**Origem:** Problema C, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par B (junto com o Kata 03 — Exploring the Terrain).
**Técnica esperada:** simulação com fila + estrutura para consultar o máximo
corrente.

## Descrição

Uma sequência de cartas numeradas fica sobre a mesa, inicialmente vazia. Os
jogadores jogam em turnos, adicionando cartas ao fim da sequência; o `i`-ésimo
jogador joga a carta de valor `Cᵢ`.

A regra principal: **não pode haver cartas com números repetidos na mesa**.

- Se o número jogado não aparece na sequência atual, a carta é simplesmente
  adicionada ao fim.
- Se o número já está na mesa, ocorre uma eliminação: **todas as cartas do início
  da sequência até (e incluindo) a carta anterior com esse valor são removidas**.
  Só então a carta recém-jogada é colocada no fim da sequência.

Após esse processo nunca restam valores repetidos, e a sequência nunca fica
vazia.

Após cada jogada, reporte a carta de maior valor ainda na mesa e o índice do
jogador que a jogou.

## Entrada

A primeira linha contém `N` (1 ≤ N ≤ 2×10⁵), o número de jogadores. A segunda
linha contém os valores das cartas `Cᵢ` (1 ≤ Cᵢ ≤ N).

## Saída

`N` linhas, cada uma com dois valores separados por espaço: o valor `C` da maior
carta ainda na mesa e o índice `i` do jogador que jogou essa carta.

## Exemplo

Entrada (`tests/test01.in`):

```
6
3 1 4 1 6 6
```

Saída (`tests/test01.out`):

```
3 1
3 1
4 3
4 3
6 5
6 6
```

Na 4ª jogada, o jogador 4 joga `1`, que já estava na mesa: o prefixo até o `1`
anterior é removido, restando `[4, 1]` — a maior carta passa a ser 4, jogada pelo
jogador 3.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

# Kata 04 — Garment Groups

**Origem:** Problema G, XIII Maratona Mineira de Programação (2026) — Codeforces
Gym 106552.
**Par de dificuldade:** Par A (junto com o Kata 01 — Bario World).
**Técnica esperada:** raciocínio combinatório — código curto, a dificuldade está
em enxergar a invariante.

## Descrição

Para pendurar uma camisa no varal são necessários dois pregadores (um em cada
ponta). Com duas camisas, porém, é possível usar apenas três pregadores,
prendendo as pontas de duas camisas consecutivas com o mesmo pregador. Quando
isso acontece, dizemos que foi formado um **grupo** de camisas, e que as camisas
presas pelo mesmo pregador pertencem ao mesmo grupo.

Pertencer a um grupo é transitivo: se a camisa A está no mesmo grupo que a B, e a
B no mesmo grupo que a C, então A e C também estão no mesmo grupo. Uma camisa que
não compartilha pregador com nenhuma outra forma um grupo sozinha.

Dilson quer pendurar `N` camisas formando exatamente `G` grupos. Qual é o número
mínimo de pregadores necessário?

## Entrada

Uma única linha com dois inteiros `N` (1 ≤ N ≤ 10⁶) e `G` (1 ≤ G ≤ N), o número
de camisas e o número de grupos desejado.

## Saída

Um único inteiro: o número de pregadores necessários para pendurar `N` camisas em
`G` grupos.

## Exemplos

Entrada (`tests/test01.in`) → saída (`tests/test01.out`):

```
4 3   ->   7
```

Entrada (`tests/test02.in`) → saída (`tests/test02.out`):

```
2 1   ->   3
```

No segundo exemplo: um pregador numa ponta da primeira camisa, um prendendo a
outra ponta dela junto com uma ponta da segunda camisa, e um na outra ponta da
segunda — formando um grupo de duas camisas com três pregadores.

## Como rodar os testes

```bash
python3 ../common/run_tests.py . -- python3 solution.py
```

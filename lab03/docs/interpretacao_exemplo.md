# Interpretação do exemplo simulado

Script: `scripts/exemplo_simulado.py` · Saídas: `dados/simulado/exemplo.csv` e `dados/simulado/exemplo_resultado.json`.

## Parâmetros

Semente `42` (`np.random.default_rng(42)`); dois grupos lognormais independentes com
n_A = n_B = 30, medianas teóricas 10 (A) e 14 (B), α = 0,05. Os sigmas (desvio do log)
são distintos de propósito: σ_A = 0,8 e σ_B = 0,5. Com formas diferentes, médias e medianas
divergem, e o Mann-Whitney responde à dominância, não a nenhuma das duas.

Amostralmente: medianas A = 10,81 e B = 15,23; médias A = 11,95 e B = 16,08.

## Welch (compara MÉDIAS)

t = −2,344 com gl = 57,48 (Welch-Satterthwaite, que admite variâncias desiguais),
p = 0,0226 < 0,05, bilateral. O d de Cohen (desvio combinado) é −0,605, um efeito médio:
a média de A é menor que a de B. O teste olha só a diferença de médias, ponderada pelo
erro-padrão de cada grupo.

## Mann-Whitney (compara POSTOS)

U_A = 292, z = −2,329 (com correção de continuidade e de empates), p = 0,0199 < 0,05.

O teste **não compara medianas**. Ele testa dominância estocástica: se
P(X>Y) + ½·P(X=Y) ≠ ½, com X de A e Y de B. Só equivale a comparar medianas se as
distribuições tiverem a mesma forma e escala, o que não vale aqui (σ_A ≠ σ_B numa lognormal).

O `tamanho_efeito` é a correlação rank-biserial r = 2·P(A>B) − 1, com P(A>B) = U_A/(n_A·n_B)
(sem empates em dados contínuos). Aqui P(A>B) = 292/900 = 0,324, logo r = 2·0,324 − 1 = −0,351:
em um par sorteado, o valor de A supera o de B em cerca de 32% das vezes, e B supera A em
cerca de 68%. r = 0 seria dominância nula; r = ±1, separação total dos grupos.

## O que o exemplo ilustra e o que não permite concluir

- Ilustra o fluxo da simulação (gerar → testar → medir efeito) e as leituras distintas dos
  dois testes: médias (Welch, d) versus postos/dominância (Mann-Whitney, r).
- É **uma única amostra**: os dois testes rejeitarem H₀ aqui não diz nada sobre a taxa de
  rejeição em geral. Não é estimativa de poder nem de erro tipo I.
- Poder e erro tipo I de cada teste só vêm das 10.000 repetições da Sprint 2.

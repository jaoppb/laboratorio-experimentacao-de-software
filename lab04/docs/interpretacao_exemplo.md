# Interpretação do exemplo simulado

Script: `scripts/exemplo_simulado.py` · Saídas: `dados/simulado/exemplo.csv` e `dados/simulado/exemplo_resultado.json`.

## Parâmetros

Semente `42` (`np.random.default_rng(42)`); dois grupos lognormais independentes gerados a partir dos parâmetros estimados dos dados reais (`dados/parametros.json`):
- `com_bot`: n = 30, mediana teórica = 7,6029 h, σ_log = 3,2203;
- `sem_bot`: n = 30, mediana teórica = 2,7308 h, σ_log = 2,5018;
- Nível de significância α = 0,05 (teste bicaudal).

Os sigmas (desvios-padrão do logaritmo) são distintos porque refletem a dispersão empírica de cada grupo real. Com formas e escalas distintas sob uma distribuição lognormal de cauda pesada, médias e medianas teóricas se afastam significativamente das observações amostrais.

Neste conjunto gerado:
- Medianas amostrais: `com_bot` = 10,44 h; `sem_bot` = 4,19 h.
- Médias amostrais: `com_bot` = 50,94 h; `sem_bot` = 30,51 h.

## Welch (compara MÉDIAS)

- Estatística t = 0,803 com gl = 56,57 (graus de liberdade de Welch-Satterthwaite, que acomodam variâncias desiguais).
- p-valor = 0,4253 > 0,05 (bilateral).
- Tamanho do efeito (d de Cohen com desvio combinado): d = 0,2074.

O teste t de Welch avalia exclusivamente a diferença entre as médias populacionais ponderada pelo erro-padrão. Devido à altíssima assimetria da lognormal com σ_log > 2,5, a variabilidade das médias amostrais é enorme (erro-padrão inflado por valores extremos na cauda longa), resultando em um t reduzido e incapacidade de rejeitar H₀ mesmo com as médias amostrais sendo 50,94 h vs 30,51 h.

## Mann-Whitney (compara POSTOS)

- Estatística U (`com_bot`) = 553,0, z = 1,515 (com correção de continuidade e de empates).
- p-valor = 0,1297 > 0,05 (bilateral).
- Tamanho do efeito (correlação rank-biserial): r = 0,2289.

O teste **não compara medianas**. Ele testa a dominância estocástica: se P(X_com > X_sem) + ½·P(X_com = X_sem) ≠ 0,5. Como as distribuições possuem parâmetros de escala distintos (σ_log de 3,22 vs 2,50), o teste não pode ser interpretado como um teste estrito de igualdade de medianas.

Com U = 553 em um total de 30 × 30 = 900 pares, a probabilidade amostral de dominância P(com_bot > sem_bot) é 553 / 900 = 0,6144 (61,4%), fornecendo a correlação rank-biserial r = 2 · 0,6144 − 1 = 0,2289. Em termos práticos, em 61,4% dos pares comparados, o tempo do grupo com bot foi superior ao sem bot. Contudo, sob α = 0,05, o p-valor obtido (0,1297) não permite rejeitar H₀.

## Comparação entre os testes no exemplo

Nesta amostra simulada específica, **ambos os testes concordam na decisão estatística de não rejeitar H₀** ao nível de α = 0,05 (Welch p = 0,4253; Mann-Whitney p = 0,1297). Contudo, o Mann-Whitney produziu um p-valor consideravelmente menor e mais sensível ao efeito presente na população (7,60 h vs 2,73 h), confirmando a expectativa inicial de que o teste não paramétrico baseado em postos sofre menos com a instabilidade provocada pela cauda pesada.

## O que o exemplo ilustra e o que não permite concluir

- Ilustra o fluxo da simulação (geração lognormal via parâmetros reais → execução dos testes → apuração dos tamanhos de efeito) e evidencia as naturezas distintas das hipóteses estatísticas: diferença de médias ponderada por variância (Welch) vs dominância estocástica ordinal (Mann-Whitney).
- É **uma única amostra**: o fato de ambos não rejeitarem H₀ neste sorteio isolado de 30 observações não diz nada sobre a probabilidade sistemática de rejeição. Não constitui estimativa de poder nem de erro tipo I.
- A estimativa precisa de poder estatístico (Q2) e controle da taxa de erro tipo I (Q1) exige as 10.000 repetições da simulação de Monte Carlo que serão desenvolvidas na Sprint 2.

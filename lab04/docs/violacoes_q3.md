# Q3 — Violações dos pressupostos do Welch

`scripts/simular_q3.py` repete Q1 (erro tipo I) e Q2 (poder) em situações que violam os pressupostos do t de Welch (médias aproximadamente normais, o que exige dados pouco assimétricos, sem valores extremos e amostra não pequena). Parte de uma **referência** (n = 30 por grupo, lognormal com σ_log = 1,0) e muda **um fator por vez**, para atribuir cada efeito a uma causa. Todas usam a mediana do grupo `sem_bot` (2,73 h), 10.000 repetições, α = 0,05 e `default_rng(42)`. O efeito é a razão entre as medianas (1,0 = H₀ verdadeira).

| Cenário | O que muda em relação à referência |
|---|---|
| `referencia` | nada (n = 30, σ_log = 1,0) |
| `n_pequeno` | n = 10 por grupo |
| `assimetria_extrema` | σ_log = 3,0 (cauda muito pesada; os dados reais ficam entre 2,5 e 3,2) |
| `outliers` | cada observação, nos dois grupos, tem 5% de chance de ser multiplicada por 20 |

Saídas: `dados/simulado/q3_erro_tipo1.csv` e `dados/simulado/q3_poder.csv`.

## Resultados

Erro tipo I (razão 1,0; o esperado é 5%):

| Cenário | Welch | Mann-Whitney |
|---|---|---|
| referencia | 3,7% | 4,6% |
| n_pequeno | 2,7% | 4,3% |
| assimetria_extrema | 0,85% | 4,6% |
| outliers | 1,7% | 4,8% |

Poder (proporção de rejeições) para razão de medianas 2,0 e 4,0:

| Cenário | Welch (2,0 / 4,0) | Mann-Whitney (2,0 / 4,0) |
|---|---|---|
| referencia | 55% / 97% | 72% / 99,9% |
| n_pequeno | 16% / 52% | 27% / 79% |
| assimetria_extrema | 1,9% / 4,5% | 13% / 40% |
| outliers | 14% / 42% | 64% / 99,6% |

## Por que a violação afeta mais o Welch (pergunta 11)

- O Welch compara **médias**, e a média e o desvio-padrão são muito sensíveis a poucos valores grandes. Numa lognormal com σ_log alto ou com outliers, um ou dois PRs de milhares de horas dominam a média e inflam o erro-padrão. A estatística t fica "grande" por acaso em poucas amostras e "pequena demais" nas demais, e a aproximação pela distribuição t deixa de valer. O resultado é um teste **conservador**: rejeita bem menos que 5% sob H₀ (0,85% a 2,7%) e quase não detecta efeito real.
- O Mann-Whitney usa **postos**: um PR de 3.000 h vale o mesmo que um de 100 h. Por isso o erro tipo I se mantém perto de 5% em todos os cenários (4,3% a 4,8%) e o poder cai pouco com outliers. Ele só perde poder com n pequeno (menos informação) e com σ_log muito alto, em que a sobreposição entre os grupos aumenta.
- Mesmo na referência (σ_log = 1,0) o Welch já fica um pouco conservador (3,7%), e o Mann-Whitney tem mais poder. Em nenhuma das situações simuladas o Welch superou o Mann-Whitney.

## Limitações

- A contaminação é simétrica (mesma probabilidade nos dois grupos). Outliers só em um grupo mudariam a média daquele grupo e poderiam fazer o Welch rejeitar H₀ sem que a localização típica tenha mudado.
- O Mann-Whitney testa dominância estocástica, não medianas. A razão de medianas é só uma forma de definir o tamanho do efeito na simulação.

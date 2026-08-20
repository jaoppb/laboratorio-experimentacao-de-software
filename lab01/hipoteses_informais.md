# Lab01 - Hipóteses Informais (Primeira Versão do Relatório)

Documento consolidado com as hipóteses informais de cada integrante, com base
na validação dos dados na amostra de 1000 repositórios (Sprint S02).

---

## RQ01 + RQ02 (Marcela)

**Metodologia:** validação via testes automatizados (pytest), amostra de 1000
repositórios extraída aleatoriamente (seed fixa) da base completa, checando
valores ausentes, distribuição e outliers (método IQR).

**RQ01 - Idade do repositório (age_days)**
- Nenhum outlier identificado na amostra (0 de 1000 repositórios).
- A distribuição da idade dos repositórios populares é relativamente
  homogênea, sem concentração atípica em repositórios "muito antigos" ou
  "muito novos".
- **Hipótese informal:** a popularidade de um repositório não está fortemente
  relacionada à sua idade — repositórios populares surgem e se mantêm
  populares em diferentes momentos, não só os mais antigos.

**RQ02 - Pull requests aceitas (merged_pull_requests)**
- 157 outliers identificados na amostra (15,7% dos 1000 repositórios), todos
  com volume de contribuição muito acima da média (ex.: 358, 600, 610, 551,
  991 PRs aceitas).
- **Hipótese informal:** a contribuição externa entre repositórios populares
  é distribuída de forma desigual — uma minoria de repositórios (frameworks e
  bibliotecas amplamente utilizadas) concentra a maior parte das
  contribuições externas aceitas, enquanto a maioria recebe um volume mais
  modesto.

---

## RQ03 + RQ04 (João)

**Metodologia:** A validação foi realizada a partir do arquivo
`dados/unified_sample.csv`, contendo uma amostra consolidada de 99984
repositórios. Por meio da biblioteca `pandas`, foram calculadas métricas de
tendência central (média e mediana), dispersão (desvio padrão) e extremos
(mínimo e máximo) para os atributos `total_releases` (RQ03) e
`time_since_update_days` (RQ04).

**RQ03 - Total de releases**

- **Estatísticas encontradas:**
  - Média: 28.58 releases (Desvio Padrão: 87.11)
  - Mediana: 2.00 releases
  - Variação: de 0 a 1000 releases
- **Hipótese informal:** Repositórios populares e com ciclo de desenvolvimento
  maduro tendem a adotar entregas frequentes, resultando em um volume expressivo
  de releases acumuladas.

**RQ04 - Tempo desde a última atualização**

- **Estatísticas encontradas:**
  - Média: 9.25 dias (Desvio Padrão: 20.48)
  - Mediana: 2.00 dias
  - Variação: de 0 a 773 dias
- **Hipótese informal:** Repositórios com grande base de usuários e
  colaboradores recebem manutenção ativa constante, portanto a maioria
  expressiva possui atualizações muito recentes.

---

## RQ05 + RQ06 (Gabriel)

**Metodologia:** Análise recalculada sobre o dataset completo `dados/unified_sample.csv` contendo 99984 repositórios. Embora os testes de validação em [lab01/tests/test_validacao_rq05_rq06.py](lab01/tests/test_validacao_rq05_rq06.py#L1-L100) façam uma amostra de 1000 quando aplicados, aqui extraímos estatísticas para todo o conjunto para obter medidas mais representativas. Foram computadas contagens por `primary_language`, verificados valores ausentes e calculadas estatísticas descritivas de `closed_issues_ratio` (média, mediana, quartis, desvio padrão) e detecção de outliers via IQR.

**RQ05 - Linguagem primária**
- Top 10 linguagens observadas no dataset completo (n=99984):
  - Python: 18089
  - JavaScript: 11858
  - TypeScript: 9083
  - Java: 6021
  - Go: 5750
  - C++: 5306
  - C: 3927
  - Rust: 3307
  - C#: 2975
  - Shell: 2495
- Valores ausentes em `primary_language`: 8180 de 99984 (≈8.18%). Muitos registros sem linguagem identificada correspondem a coleções, documentação ou repositórios onde não foi possível inferir uma linguagem primária; portanto recomenda-se tratar explicitamente uma categoria "missing/other" nas análises por linguagem.
- **Hipótese informal:** a distribuição de popularidade continua concentrada em algumas linguagens dominantes — Python, JavaScript e TypeScript lideram com folga —, mas existe uma fração relevante de repositórios sem linguagem bem definida. Isso reforça a necessidade de incluir uma categoria "missing/other" para evitar viés em análises por linguagem.

**RQ06 - Razão de issues fechadas/total**
- Estatísticas (dataset completo, após remover valores ausentes):
  - Observações não-nulas: 95153
  - Média: 0.688900
  - Mediana: 0.750000
  - Mínimo: 0.000000
  - Máximo: 1.000000
  - Desvio padrão (populacional): 0.264522
  - Valores ausentes em `closed_issues_ratio`: 4831 de 99984 (≈4.83%) — tipicamente associados a repositórios com `total_issues == 0` (razão indefinida).
  - Outliers (IQR): 0 observados com limites IQR ≈ [-0.0799, 1.5085], portanto não há valores além dos limites esperados pelo critério IQR.
- **Hipótese informal:** na base completa a maioria dos repositórios fecha uma fração substancial das issues (mediana = 0.75), indicando manutenção ativa em muitos projetos. A dispersão (pstdev ≈ 0.2645) sugere variação por tipo de projeto e ecossistema; além disso, a presença de ~4.8% de valores ausentes mostra que parte da base não possui issues, exigindo tratamento explícito (ex.: filtrar ou agrupar como "sem issues") nas análises que envolvem `closed_issues_ratio`.

---

## Próximos passos
Este documento será expandido na Sprint S03 com análise e visualização de
dados para as 7 RQs (incluindo RQ07, que cruza os resultados de RQ02, RQ03 e
RQ04 por linguagem)

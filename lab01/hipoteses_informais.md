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

**Metodologia:** _(descrever brevemente como foi feita a validação)_

**RQ05 - Linguagem primária**
- _(distribuição por categoria/linguagem)_
- **Hipótese informal:** _(preencher)_

**RQ06 - Razão de issues fechadas/total**
- _(estatísticas encontradas)_
- **Hipótese informal:** _(preencher)_

---

## Próximos passos
Este documento será expandido na Sprint S03 com análise e visualização de
dados para as 7 RQs (incluindo RQ07, que cruza os resultados de RQ02, RQ03 e
RQ04 por linguagem)

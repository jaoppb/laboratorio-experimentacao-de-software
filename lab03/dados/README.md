# Dicionário de Dados - Lab03 (Métricas DORA)

Este diretório contém os artefatos de dados gerados pelo pipeline de mineração do **Lab03** (*DevOps Research and Assessment*).

---

## 1. Visão Geral dos Arquivos

| Arquivo | Formato | Descrição |
|---|---|---|
| `repositorios.parquet` | Apache Parquet (Snappy) | Dataset consolidado com metadados e métricas DORA calculadas com tipagem estrita. |
| `repositorios.csv` | CSV (UTF-8) | Cópia tabular para replicação cruzada e análises estatísticas. |
| `funil.csv` | CSV (UTF-8) | Registro das etapas de filtragem do funil de seleção com contagens e descartes. |
| `runs/{owner}__{repo}.parquet` | Apache Parquet (Snappy) | Execuções brutas de workflow do default branch (evento `push`) de cada repositório aceito. |

---

## 2. Dicionário de Dados: `repositorios.parquet` e `repositorios.csv`

| Coluna | Tipo | Unidade | Descrição / Origem |
|---|---|---|---|
| `owner` | String | - | Proprietário ou organização mantenedora no GitHub (`GET /repos/{owner}/{repo}`). |
| `name` | String | - | Nome do repositório. |
| `full_name` | String | - | Identificador único no formato `owner/name`. |
| `stars` | Inteiro | estrelas | Contagem de estrelas (`stargazers_count`) obtida via Search API. |
| `language` | String | - | Linguagem primária identificada pelo GitHub. |
| `default_branch` | String | - | Branch principal do repositório (`main`, `master`, etc.). |
| `created_at` | String (ISO 8601 UTC) | timestamp | Data e hora de criação do repositório no GitHub. |
| `contributors_count` | Inteiro | pessoas | Total de contribuidores inferido pelo último número de página do cabeçalho `Link` de `GET /repos/.../contributors?per_page=1&anon=true`. |
| `releases_count_window` | Inteiro | releases | Total de releases publicadas (`draft = false` e `prerelease = false`) dentro da janela de 12 meses. |
| `total_releases` | Inteiro | releases | Total de releases publicadas e rascunhos coletados no histórico. |
| `workflow_runs_count_window` | Inteiro | runs | Quantidade de workflow runs válidos (`event = push`, default branch, status `success` ou `failure`) dentro da janela. |
| `total_workflow_runs` | Inteiro | runs | Total de workflow runs recuperados na janela de observação. |
| `deployment_frequency` | Float | releases/semana | Frequência de entrega: `releases_count_window / 52.1 semanas`. |
| `deployment_tier` | String | faixa | Nível DORA de frequência (`Elite`: $\ge 7$/sem, `High`: $1 \le x < 7$/sem, `Medium`: $\ge 12/52.1$/sem, `Low`: $< 12/52.1$/sem). |
| `lead_time_a_hours` | Float | horas | Mediana do lead time por release (variante a): tempo decorrido entre o commit mais antigo da release e sua publicação. |
| `lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b): mediana de todos os commits em todas as releases avaliadas. |
| `lead_time_tier` | String | faixa | Nível DORA de lead time baseado na variante (a) em dias (`Elite`: $< 1$ dia, `High`: $1 \le x < 7$ dias, `Medium`: $7 \le x < 30$ dias, `Low`: $\ge 30$ dias). |
| `cfr_a` | Float | proporção (0.0 a 1.0) | Change Failure Rate da esteira de CI: `falhas / (falhas + sucessos)` dos workflow runs no default branch. |
| `cfr_tier` | String | faixa | Nível DORA de CFR (`Elite`: $\le 15\%$, `High`: $15\% < x \le 30\%$, `Medium`: $30\% < x \le 45\%$, `Low`: $> 45\%$). |
| `recovery_hours` | Float | horas | Mediana do tempo de recuperação de falhas de CI (`success.updated_at - first_failure.run_started_at`) agrupado por workflow. |
| `recovery_tier` | String | faixa | Nível DORA de recuperação (`Elite`: $< 1$h, `High`: $1 \le x < 24$h, `Medium`: $24 \le x < 168$h, `Low`: $\ge 168$h). |
| `censored_episodes_ratio` | Float | proporção (0.0 a 1.0) | Proporção de episódios de falha que não obtiveram sucesso de recuperação antes do fim da janela (dados censurados). |
| `overall_dora_score` | Inteiro | pontos (1 a 4) | Nota consolidada DORA (Elite=4, High=3, Medium=2, Low=1): mediana das notas das 4 métricas, arredondada para baixo. |
| `overall_dora_tier` | String | faixa | Classificação geral consolidada do repositório (`Elite`, `High`, `Medium`, `Low`). |

---

## 3. Dicionário de Dados: `funil.csv`

| Coluna | Tipo | Descrição |
|---|---|---|
| `etapa` | String | Descrição da fase sequencial do funil de amostragem. |
| `quantidade_restante` | Inteiro | Total de repositórios que avançaram para a próxima fase. |
| `descartados` | Inteiro | Quantidade de repositórios excluídos na respectiva etapa. |
| `motivo_descarte` | String | Regra operacional ou critério de exclusão aplicado. |

---

## 4. Dicionário de Dados: `runs/{owner}__{repo}.parquet`

| Coluna | Tipo PyArrow | Descrição |
|---|---|---|
| `id` | `int64` | Identificador único da execução do workflow na API do GitHub Actions. |
| `repo` | `string` | Repositório no formato `owner/repo`. |
| `workflow_id` | `string` | Identificador do workflow associado. |
| `name` | `string` | Nome descritivo do workflow. |
| `event` | `string` | Evento acionador da execução (`push`). |
| `branch` | `string` | Nome do branch executado (`default_branch`). |
| `conclusion` | `string` | Conclusão da execução (`success`, `failure`, `timed_out`, etc.). |
| `run_started_at` | `timestamp[us, UTC]` | Data e hora de início da execução. |
| `updated_at` | `timestamp[us, UTC]` | Data e hora de encerramento da execução. |
| `is_valid` | `bool` | Indicador se a execução é válida para cálculo de CFR e tempo de recuperação (`True` para `success` ou `failure`). |

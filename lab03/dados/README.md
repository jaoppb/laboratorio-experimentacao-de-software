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
| `releases/{owner}__{repo}.parquet` | Apache Parquet (Snappy) | Releases da definição principal (C1: publicadas, sem pré-releases) da janela, com a release anterior, o status da comparação e os commits com mensagens (Issue #58). Base do lead time, do CFR (b) e da amostra-ouro. |
| `releases_c2/{owner}__{repo}.parquet` | Apache Parquet (Snappy) | Mesmo esquema de `releases/`, para a combinação C2 da RQ 07 (releases + pré-releases). |
| `analises/lead_time_diagnostico.csv` | CSV (UTF-8) | Diagnóstico por repositório dos motivos de lead time nulo e dos casos LT(b) > LT(a), gerado por `analises/investigar_lead_time.py` (Issue #60; ver `docs/investigacao_lead_time.md`). |
| `tags/{owner}__{repo}.parquet` | Apache Parquet (Snappy) | Tags Git avaliadas na janela (+ âncora) com datas de autor, commits e SHAs (Issue #54). |

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
| `prereleases_count_window` | Inteiro | releases | Total de pré-releases (`prerelease = true`) dentro da janela de 12 meses. |
| `total_prereleases` | Inteiro | releases | Total de pré-releases coletadas no histórico do repositório. |
| `tags_count_window` | Inteiro | tags | Total de Git tags apontando para commits dentro da janela de 12 meses. |
| `total_tags` | Inteiro | tags | Total de Git tags encontradas no repositório. |
| `c2_deployment_frequency` | Float | deploys/semana | Frequência de deploy sob a combinação C2: `(releases + pré-releases na janela) / 52.1 semanas`. |
| `c2_lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b) para todos os commits entregues em releases e pré-releases da janela. |
| `c3_deployment_frequency` | Float | tags/semana | Frequência de deploy sob a combinação C3: `tags na janela / 52.1 semanas`. |
| `c3_lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b) para commits entregues entre tags consecutivas da janela. |

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

---

## 5. Dicionário de Dados: `releases/{owner}__{repo}.parquet` e `releases_c2/{owner}__{repo}.parquet`

Uma linha por release publicada **dentro** da janela de observação, em ordem cronológica. A release âncora (última antes da janela) não vira linha: ela só aparece como `previous_release` da primeira release da janela. Os commits vêm de `git log {previous_release}..{tag_name}` no clone local *blobless* (equivalente ao `compare/{base}...{head}` da API).

- `releases/` usa a definição principal (C1): releases publicadas, `prerelease = false`.
- `releases_c2/` usa a combinação C2 da RQ 07: releases publicadas e pré-releases.

Os dois diretórios são gravados pelo orquestrador para cada repositório aceito. Para gerar `releases/` de uma amostra coletada antes desse arquivo existir, rode `uv run python -m pipeline.persist_releases --config config.yaml` (pula os repositórios que já têm arquivo). Os dois diretórios **não são versionados** (cerca de 320 MB na amostra de 330 repositórios, com um arquivo acima do limite de 100 MB do GitHub): regenere-os com esse comando, que leva cerca de 10 minutos e usa uma consulta GraphQL por repositório.

| Coluna | Tipo PyArrow | Unidade | Descrição |
|---|---|---|---|
| `tag_name` | `string` | - | Nome da tag associada à release no GitHub (`tag_name`). |
| `published_at` | `timestamp[us, UTC]` | timestamp | Data de publicação da release (`published_at`). |
| `prerelease` | `bool` | - | `True` se a release é pré-release (só ocorre em `releases_c2/`). |
| `previous_release` | `string` | - | Tag da release anterior na ordem cronológica (pode ser a âncora, fora da janela). Nulo quando a release é a primeira da história do repositório. |
| `status` | `string` | - | Resultado da comparação com a release anterior: `ok` (commits coletados), `first_release` (não há release anterior; ignorada no lead time) ou `not_found` (tag inexistente no clone, equivalente ao 404 do `compare`; ignorada no lead time). |
| `commits_count` | `int64` | commits | Número de commits em `previous_release..tag_name`. `0` significa release sem commits novos; nulo quando `status ≠ ok`. |
| `commits` | `list<struct<sha: string, committed_at: string, message: string>>` | - | Commits incluídos na release: SHA, data do autor (`commit.author.date`, ISO 8601) e **assunto** da mensagem (primeira linha, `git log --format=%s`). Lista vazia quando `status ≠ ok`. |

---

## 6. Dicionário de Dados: `tags/{owner}__{repo}.parquet`

Armazena as tags Git do repositório mapeadas na janela de observação (mais a âncora anterior), com datação direta pelo commit apontado e commits intermediários.

| Coluna | Tipo PyArrow | Descrição |
|---|---|---|
| `tag_name` | `string` | Identificador da tag no Git (`refs/tags/{tag_name}`). |
| `published_at` | `timestamp[us, UTC]` | Data e hora de autoria do commit para o qual a tag aponta (`commit.author.date`). |
| `commit_sha` | `string` | SHA-1 completo do commit apontado pela tag. |
| `previous_tag` | `string` | Nome da tag anterior na ordem cronológica de deploy (nulo para a primeira). |
| `commits_count` | `int64` | Quantidade de commits entre a tag anterior e a atual. |
| `commits` | `list<struct<sha: string, committed_at: string, message: string>>` | Lista estruturada de commits entre as tags consecutivas com SHA, data e mensagem. |


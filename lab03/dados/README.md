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
| `amostra_ouro/` | CSV / XLSX / JSON | Planilhas em branco de rotulação por avaliador, template e `sorteio_info.json` da amostra-ouro de 60 repositórios, gerados por `analises/amostra_ouro.py` (Issue #63); 300 linhas reais, com o sorteio dos 30 repositórios antes pendentes concluído (`--completar-pendentes`; ver `docs/amostra_ouro.md`). Não faz parte do dataset de métricas. |

---

### Janela de observação

`janela.inicio` e `janela.fim` (`config.yaml`) definem a janela. Regras (Issue #56, decisão do grupo):

- `inicio` só com data (`"2025-10-01"`) vale `2025-10-01T00:00:00Z`.
- `fim` só com data (`"2026-09-30"`) vale o **fim do dia**: o último instante é `2026-09-30T23:59:59.999999Z` (equivale ao limite exclusivo `2026-10-01T00:00:00Z`). Releases e runs de todo o dia 30/09 entram na janela. Um `fim` com horário (`"2026-09-30T00:00:00Z"`) é usado como está.
- A interpretação de `fim` está em um único ponto, `metricas/schemas.py::parse_window_end`, usado pelo filtro de releases (`pipeline/releases.py::filter_window`), pela coleta de runs (`created=início..fim`), pelo corte de censura do CFR (b) (`fim − 7 dias` = `2026-09-23T23:59:59.999999Z`) e pelas amostras-ouro.
- A janela tem **365 dias = 365/7 ≈ 52,14 semanas** (antes: 364 dias, divisor 52,1). Esse é o denominador das frequências de deploy (`deployment_frequency`, `c2_`, `c3_`) e do limiar mensal (12/(365/7) ≈ 0,230 deploys/semana).
- Os 330 repositórios (seleção) e a amostra-ouro foram escolhidos com a janela antiga (`fim` = 30/09 00:00Z); isso é um desvio documentado: a regeneração recoleta os mesmos 330 com a janela nova.

---

## 2. Dicionário de Dados: `repositorios.parquet` e `repositorios.csv`

| Coluna | Tipo | Unidade | Descrição / Origem |
|---|---|---|---|
| `owner` | String | - | Proprietário ou organização mantenedora no GitHub, extraído de `full_name` (candidato da Search API). |
| `name` | String | - | Nome do repositório. |
| `full_name` | String | - | Identificador único no formato `owner/name`. |
| `stars` | Inteiro | estrelas | Contagem de estrelas na coleta: `stargazerCount` da consulta GraphQL de detalhes do repositório (na rota de contingência REST, `stargazers_count` do candidato da Search API). |
| `language` | String | - | Linguagem primária identificada pelo GitHub (`primaryLanguage.name`). Nulo quando o GitHub não identifica linguagem. |
| `default_branch` | String | - | Branch principal do repositório (`defaultBranchRef.name`; `main` se ausente). |
| `created_at` | String (ISO 8601 UTC) | timestamp | Data e hora de criação do repositório no GitHub. |
| `contributors_count` | Inteiro | pessoas | Total de contribuidores inferido pelo último número de página do cabeçalho `Link` de `GET /repos/.../contributors?per_page=1&anon=true` (sem `Link`, usa o tamanho da página; `0` se a requisição falhar). |
| `releases_count_window` | Inteiro | releases | Total de releases publicadas (`draft = false` e `prerelease = false`) com `published_at` dentro da janela de 12 meses (`janela.inicio` a `janela.fim` do `config.yaml`, limites inclusivos; `fim` só com data vale até o **fim do dia**, ver subseção "Janela de observação"). |
| `total_releases` | Inteiro | releases | Total de releases publicadas coletadas, **incluindo pré-releases e excluindo rascunhos** (`isDraft` e releases sem `publishedAt` são descartadas na coleta). A coleta pagina da mais recente para a mais antiga e para na página que contém a release âncora (última release estável anterior à janela); portanto **não é o histórico completo** do repositório. |
| `workflow_runs_count_window` | Inteiro | runs | Quantidade de workflow runs válidos dentro da janela (`event = push`, default branch). Run válido é o de conclusão `success` ou de falha, onde falha = `failure`, `timed_out` ou `startup_failure` (`metricas/stability.py::classify_conclusion`). Conclusões `cancelled`, `skipped`, `neutral`, `action_required`, `stale` e nulas (em andamento) não contam. |
| `total_workflow_runs` | Inteiro | runs | Total de workflow runs (`event = push`, default branch) recuperados na janela, de qualquer conclusão, deduplicados por `id`. Sempre `>= workflow_runs_count_window`. |
| `deployment_frequency` | Float | releases/semana | Frequência de entrega: `releases_count_window / (365/7) semanas` (≈ 52,14; a janela tem 365 dias). |
| `deployment_tier` | String | faixa | Nível DORA de frequência (`Elite`: $\ge 7$/sem, `High`: $1 \le x < 7$/sem, `Medium`: $\ge 12/(365/7)$/sem ≈ 0,230, `Low`: abaixo disso). |
| `lead_time_a_hours` | Float | horas | Mediana do lead time por release (variante a): tempo decorrido entre o commit mais antigo da release (data de autor) e sua publicação. Valores negativos por relógio adiantado são limitados a 0. Releases sem commits novos ou sem comparação (`first_release`, `not_found`) não entram. Nulo quando nenhuma release da janela pôde ser avaliada. |
| `lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b): mediana de `publicação da release − data de autor do commit` sobre todos os commits de todas as releases avaliadas (mesmas regras de exclusão e limite em 0 da variante a). Nulo quando nenhuma release foi avaliada. |
| `lead_time_tier` | String | faixa | Nível DORA de lead time baseado na variante (a) em dias (`Elite`: $< 1$ dia, `High`: $1 \le x < 7$ dias, `Medium`: $7 \le x < 30$ dias, `Low`: $\ge 30$ dias). Quando `lead_time_a_hours` é nulo (falta de dado), a faixa também é **nula** (não é `Low` nem `Elite`) e a métrica sai da nota geral (regra de nulos, decisão Q18b). |
| `cfr_a` | Float | proporção (0.0 a 1.0) | Change Failure Rate da esteira de CI: `falhas / (falhas + sucessos)` dos workflow runs no default branch, onde falha = `failure`, `timed_out` ou `startup_failure` e sucesso = `success`; runs ignorados ficam fora do denominador. Nulo se não houver run válido. |
| `cfr_tier` | String | faixa | Nível DORA de CFR calculado sobre `cfr_a` (`Elite`: $\le 15\%$, `High`: $15\% < x \le 30\%$, `Medium`: $30\% < x \le 45\%$, `Low`: $> 45\%$). Quando `cfr_a` é nulo, a faixa é `Low`. |
| `recovery_hours` | Float | horas | Mediana do tempo de recuperação de falhas de CI (`success.updated_at - first_failure.run_started_at`) agrupado por workflow; falhas consecutivas formam um mesmo episódio e runs ignorados não o interrompem. Nulo quando nenhum episódio foi resolvido. |
| `recovery_tier` | String | faixa | Nível DORA de recuperação (`Elite`: $< 1$h, `High`: $1 \le x < 24$h, `Medium`: $24 \le x < 168$h, `Low`: $\ge 168$h). Quando `recovery_hours` é nulo, a faixa depende do motivo, distinguido por `censored_episodes_ratio`: sem nenhum episódio de falha (`censored_episodes_ratio = 0.0`) → `Elite`; só episódios censurados (`censored_episodes_ratio > 0`) → `Low`. |
| `censored_episodes_ratio` | Float | proporção (0.0 a 1.0) | Proporção de episódios de falha que não obtiveram sucesso de recuperação antes do fim do histórico coletado (dados censurados). É `0.0` quando não há episódios; por isso, com `recovery_hours` nulo, `0.0` indica ausência de episódios e `> 0` indica que todos foram censurados. |
| `overall_dora_score` | Inteiro | pontos (1 a 4) | Nota consolidada DORA (Elite=4, High=3, Medium=2, Low=1): mediana das notas de `deployment_tier`, `lead_time_tier`, `cfr_tier` e `recovery_tier`, arredondada para baixo. Quando `lead_time_tier` é nulo, a mediana é calculada com as 3 notas disponíveis (valor central; sem média de duas notas) em vez de 4. O CFR (b) **não** entra no cálculo. |
| `overall_dora_tier` | String | faixa | Classificação geral consolidada do repositório (`Elite`, `High`, `Medium`, `Low`). |
| `prereleases_count_window` | Inteiro | releases | Total de pré-releases (`prerelease = true`) dentro da janela de 12 meses. |
| `total_prereleases` | Inteiro | releases | Total de pré-releases (não rascunho) entre as releases coletadas; está contido em `total_releases` e sujeito ao mesmo limite de coleta (até a release âncora). |
| `tags_count_window` | Inteiro | tags | Total de Git tags apontando para commits dentro da janela de 12 meses. |
| `total_tags` | Inteiro | tags | Total de Git tags encontradas no repositório. |
| `c2_deployment_frequency` | Float | deploys/semana | Frequência de deploy sob a combinação C2: `(releases + pré-releases na janela) / (365/7) semanas`. |
| `c2_lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b) para todos os commits entregues em releases e pré-releases da janela. |
| `c3_deployment_frequency` | Float | tags/semana | Frequência de deploy sob a combinação C3: `tags na janela / (365/7) semanas`. |
| `c3_lead_time_b_hours` | Float | horas | Mediana do lead time por commit (variante b) para commits entregues entre tags consecutivas da janela. |
| `cfr_b` | Float | proporção (0.0 a 1.0) | Change Failure Rate variante (b), proxy de entrega: `cfr_b_failed_releases / cfr_b_evaluated_releases`. Nulo quando `cfr_b_evaluated_releases = 0` (todas as releases da janela censuradas ou ignoradas). Definição na subseção 2.1. |
| `cfr_b_tier` | String | faixa | Nível DORA de CFR sobre `cfr_b`, com as mesmas faixas de `cfr_tier` (`Elite`: $\le 15\%$, `High`: $15\% < x \le 30\%$, `Medium`: $30\% < x \le 45\%$, `Low`: $> 45\%$). Diferente de `cfr_tier`, é **nulo** (e não `Low`) quando `cfr_b` é nulo. |
| `cfr_b_failed_releases` | Inteiro | releases | Releases da janela classificadas como falhas (seguidas, em até 7 dias, de uma release corretiva). Numerador de `cfr_b`; nunca nulo. |
| `cfr_b_evaluated_releases` | Inteiro | releases | Releases avaliadas (falhas + sem falha). Denominador de `cfr_b`; nunca nulo. |
| `cfr_b_censored_releases` | Inteiro | releases | Releases publicadas nos últimos 7 dias da janela (`published_at > janela.fim − 7 dias`, com `janela.fim` = fim do dia: para `2026-09-30`, o corte é `2026-09-23T23:59:59.999999Z`), que ainda não podem ser avaliadas e ficam fora do denominador; nunca nulo. |
| `cfr_b_skipped_releases` | Inteiro | releases | Releases ignoradas porque a próxima release veio em até 7 dias, mas seus commits são desconhecidos (`status` `first_release` ou `not_found`), então não dá para julgar se ela é corretiva; ficam fora do denominador; nunca nulo. |
| `c2_cfr_b` | Float | proporção (0.0 a 1.0) | CFR (b) sob a combinação C2 (decisão do grupo, Q8): mesma definição de `cfr_b` (subseção 2.1), mas sobre as releases **e pré-releases** da janela (as mesmas de `releases_c2/`). Nulo quando `c2_cfr_b_evaluated_releases = 0`. Gerado pela regeneração final (seção 7.2). |
| `c2_cfr_b_tier` | String | faixa | Nível DORA de CFR sobre `c2_cfr_b`, com as faixas de `cfr_b_tier`; nulo quando `c2_cfr_b` é nulo. |
| `c2_cfr_b_failed_releases` | Inteiro | releases | Unidades de C2 classificadas como falhas; numerador de `c2_cfr_b`; nunca nulo. |
| `c2_cfr_b_evaluated_releases` | Inteiro | releases | Unidades de C2 avaliadas; denominador de `c2_cfr_b`; nunca nulo. |
| `c2_cfr_b_censored_releases` | Inteiro | releases | Unidades de C2 publicadas nos últimos 7 dias da janela (fora do denominador); nunca nulo. |
| `c2_cfr_b_skipped_releases` | Inteiro | releases | Unidades de C2 ignoradas por commits desconhecidos da próxima unidade; nunca nulo. |

### 2.1 CFR (b): release corretiva (`metricas/cfr_b.py`)

O CFR (b) mede falhas de **entrega** a partir das releases da definição principal (C1: publicadas, sem pré-releases), as mesmas de `releases/`. Para cada release `R` da janela, em ordem cronológica:

1. **Censurada** (`cfr_b_censored_releases`): `R` foi publicada depois de `janela.fim − 7 dias` (corte em `2026-09-23T23:59:59.999999Z` para `fim: "2026-09-30"`). Não há tempo de observação suficiente; fica fora do denominador.
2. **Sem falha**: não existe próxima release ou ela veio mais de 7 dias depois de `R`. Conta no denominador.
3. **Ignorada** (`cfr_b_skipped_releases`): a próxima release veio em até 7 dias, mas os commits dela são desconhecidos (`status ≠ ok` em `releases/`). Fica fora do denominador.
4. Caso contrário, a próxima release `N` (em até 7 dias) é avaliada pela **heurística de release corretiva**: se `N` é corretiva, `R` é **falha** (`cfr_b_failed_releases`); senão, `R` é sem falha.

Em cada repositório, `cfr_b_evaluated_releases + cfr_b_censored_releases + cfr_b_skipped_releases = releases_count_window`, e `cfr_b_evaluated_releases` é a soma das releases falhas e das sem falha.

Heurística `v1` (única versão disponível em `metricas/cfr_b.HEURISTICS`): `N` é corretiva se (a) só o número de patch aumenta em relação a `R` (por exemplo `2.3.0 → 2.3.1`) **e** (b) ao menos um commit de `N` tem mensagem com `revert`, `hotfix`/`hot-fix`, `fix`/`fixes`/`fixed` ou `bugfix` como palavra inteira (sem diferenciar maiúsculas; `fix(escopo):` também vale). Para tags fora do padrão SemVer (`MAJOR.MINOR[.PATCH]` com prefixo e sufixo opcionais), o critério de versão é desconhecido e vale só o critério (b).

**Versão da heurística:** é escolhida pela chave `cfr_b.heuristica` do `config.yaml` (padrão `v1`; um valor fora de `HEURISTICS` aborta a execução com `ValueError`). O dataset **não** grava qual versão foi usada: ao trocar a chave, é preciso regenerar o dataset (seção 7) e registrar a versão no commit. A versão final será definida na avaliação contra o consenso da amostra-ouro (Issue #62).

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
| `conclusion` | `string` | Conclusão da execução como devolvida pela API (`success`, `failure`, `timed_out`, `startup_failure`, `cancelled`, `skipped`, `neutral`, `action_required`, `stale`; nulo se em andamento). |
| `run_started_at` | `timestamp[us, UTC]` | Data e hora de início da execução. |
| `updated_at` | `timestamp[us, UTC]` | Data e hora de encerramento da execução. |
| `is_valid` | `bool` | Indicador se a execução é válida para cálculo de CFR e tempo de recuperação: `True` para `success` e para falhas (`failure`, `timed_out`, `startup_failure`); `False` para conclusões ignoradas (`cancelled`, `skipped`, `neutral`, `action_required`, `stale`, nula). Soma de `True` = `workflow_runs_count_window`. |

**Coleta e limite de 1.000 runs por consulta (`pipeline/workflow_runs.py`).** A API de Actions só devolve 1.000 resultados (10 páginas × 100) por consulta, qualquer que seja o `total_count`. O coletor consulta cada mês da janela e, enquanto `total_count >= 1000`, divide o intervalo ao meio (`[ini, meio]` e `[meio + 1 s, fim]`, disjuntos, em segundos inteiros) e consulta as metades em paralelo, **recursivamente, sem limite de profundidade e sem tamanho mínimo em dias** (antes: profundidade máxima 3 e intervalos mínimos de 2 dias, o que truncava em silêncio ≥ 20 repositórios). A divisão só pára quando `total_count < 1000` ou quando o intervalo chega a 1 segundo.

*Caso residual:* se um intervalo de 1 s ainda tiver `total_count >= 1000`, o filtro `created` não consegue separá-los; o coletor lê o que a API entrega (os 1.000 primeiros), registra **um único aviso por repositório** (com a quantidade de intervalos, `total_count` somado e runs lidos) e segue. Não há coluna de sinalização no dataset (decisão Q20): o artigo deve declarar esse limite residual na §3.9. O resultado em memória (`WorkflowRunsCollectionResult.api_requests` e `.unsplittable_intervals`) expõe a contagem de chamadas e os intervalos afetados.

---

## 5. Dicionário de Dados: `releases/{owner}__{repo}.parquet` e `releases_c2/{owner}__{repo}.parquet`

Uma linha por release publicada **dentro** da janela de observação, em ordem cronológica. A release âncora (última antes da janela) não vira linha: ela só aparece como `previous_release` da primeira release da janela. Os commits vêm de `git log {previous_release}..{tag_name}` no clone local *treeless/blobless* (`--bare --filter=tree:0`, ver nota abaixo; equivalente ao `compare/{base}...{head}` da API).

**Mensagem completa (`full_message`).** Além do assunto, a coleta guarda a mensagem inteira do commit (`git log --format=%B`), para a heurística CFR (b) poder ser avaliada sobre assunto + corpo (`Fixes #123`, `Revert ...` no corpo, mensagens de *merge*). Regras: quebras de linha CRLF viram `\n`, espaços nas pontas são removidos e o texto é **truncado em 10.000 caracteres** (`metricas.schemas.MAX_FULL_MESSAGE_CHARS`) para limitar o tamanho. `message` (assunto) continua igual, e a heurística `v1` lê só ele, então o resultado dela não muda. A heurística `v1_full_message` (em `metricas.cfr_b.HEURISTICS`) aplica a mesma regra da `v1` sobre `full_message`; o padrão (`DEFAULT_HEURISTIC`) segue sendo `v1`. Arquivos gerados antes desse campo não o têm: ao ler, use `Commit.from_record`, que deixa `full_message = None` e faz a `v1_full_message` cair no assunto (igual à `v1`). Custo medido em repositórios públicos: o Parquet de `releases/` cresce cerca de 35% a 70% (ver PR); recoletar é preciso para ter o campo.

**Filtro do clone.** O clone é `git clone --bare --single-branch --filter=tree:0` e as tags vêm de `git fetch --filter=tree:0 origin '+refs/tags/*:refs/tags/*'`. O filtro `tree:0` já exclui árvores **e** blobs (por isso o artigo pode chamar o clone de *treeless* e de *blobless*): só os objetos de commit e as tags são baixados, e é o que `git log` e `for-each-ref` usam. O grupo decidiu usar `combine:tree:0+blob:none`, mas o GitHub rejeita filtros `combine` (`fatal: remote error: filter 'combine' not supported`), então o pipeline usa `tree:0`, que equivale ao combinado. SHAs, datas de autor, assuntos, mensagens e tags saem idênticos com e sem o filtro (testado contra um clone completo em repositório local, onde o `combine` também foi comparado, e em repositórios públicos do GitHub; ver `tests/test_git_messages_real_git.py` e o PR).

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
| `commits` | `list<struct<sha: string, committed_at: string, message: string, full_message: string>>` | - | Commits incluídos na release: SHA, data do autor (`commit.author.date`, ISO 8601), **assunto** da mensagem em `message` (primeira linha, `%s`) e **mensagem completa** em `full_message` (assunto + corpo, `%B`). Lista vazia quando `status ≠ ok`. |

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
| `commits` | `list<struct<sha: string, committed_at: string, message: string, full_message: string>>` | Lista estruturada de commits entre as tags consecutivas com SHA, data, assunto (`message`) e mensagem completa (`full_message`, ver seção 5). |

---

## 7. Como regenerar o dataset final

`repositorios.csv`, `repositorios.parquet`, `funil.csv` e `runs/` são gerados pelo pipeline completo (`python -m pipeline`). Como a amostra-ouro (60 repositórios, seed 42) foi sorteada sobre os 330 repositórios atuais, o **conjunto de repositórios não pode mudar**; por isso as colunas novas são preenchidas por *backfill* (seção 7.1), e não por uma nova busca.

**Estado atual (execução de 2026-10-20):** `repositorios.csv` e `repositorios.parquet` têm as 38 colunas da seção 2, com os mesmos 330 repositórios e a mesma ordem. As 24 primeiras colunas (até `overall_dora_tier`) são as da coleta original, inalteradas; as 6 colunas `cfr_b*` foram preenchidas pelo backfill. As 8 colunas de pré-releases, tags, C2 e C3 (`prereleases_count_window`, `total_prereleases`, `tags_count_window`, `total_tags`, `c2_*`, `c3_*`) foram preenchidas pelo segundo backfill (seção 7.2, execução de 2026-10-21) para 329 dos 330 repositórios; `MadsLorentzen/ai-job-search` (repositório desabilitado no GitHub) e `c2_lead_time_b_hours` de `expo/expo` continuam nulos, com os motivos na seção 7.2.

Requisitos:

- Rede com acesso à API do GitHub e `git` instalado (os commits vêm de clones *treeless/blobless* temporários, `--filter=tree:0`).
- Token em `GITHUB_TOKEN` (ou vários separados por vírgula em `GITHUB_TOKENS`, que habilita rotação), em `.env` ou via `gh auth token`.
- `uv` e Python 3.12 (`uv sync` dentro de `lab03/`).
- Tempo: a regeneração de `releases/` de 330 repositórios leva cerca de 10 minutos (seção 5); o tempo do pipeline completo depende da cota da API e não foi medido para este documento.

Passos (a partir de `lab03/`):

```bash
uv sync
export GITHUB_TOKEN="seu_personal_access_token"   # ou: export GITHUB_TOKEN=$(gh auth token)
# opcional: conferir cfr_b.heuristica em config.yaml (padrão v1)
uv run python -m pipeline --config config.yaml --clean
```

Pontos de atenção:

- Uma regeneração completa com `--clean` refaz a busca de candidatos e **não preserva o conjunto de 330 repositórios** (ver a seção 7.1 para o caminho que o preserva). `--clean` é o caminho para recalcular todas as colunas. Sem ele, o pipeline reaproveita os repositórios já gravados em `repositorios.parquet` e **não** os recalcula: nesses repositórios as colunas `cfr_b*` ausentes saem nulas.
- `--clean` apaga `repositorios.parquet`, `repositorios.csv`, `funil.csv` e `.pipeline_state.json`. Os diretórios `runs/`, `releases/`, `releases_c2/` e `tags/` não são apagados; seus arquivos são sobrescritos para cada repositório aceito.
- A seleção usa a Search API, que reflete o estado atual do GitHub; a amostra regenerada pode diferir da anterior (estrelas, releases e runs mudam com o tempo).
- `python -m pipeline.persist_releases` (seção 5) regenera apenas `releases/`, e `python -m analises.persistir_amostra_ouro` persiste `releases/` só dos 60 repositórios da amostra-ouro; nenhum dos dois altera `repositorios.*`. Para preencher só as colunas `cfr_b*` nos repositórios já coletados, use o backfill da seção 7.1; para as colunas de pré-releases, tags, C2 e C3, o da seção 7.2.
- `releases/`, `releases_c2/` e `tags/` (e o `c2_c3_meta/` da seção 7.2) não são versionados (seções 5 e 6; `.gitignore`); versione apenas `repositorios.*`, `funil.csv` e `runs/`.
- Depois de regenerar, rode `uv run python -m pytest --cov=metricas --cov=pipeline --cov-report=term-missing --cov-fail-under=80` e confira se as 38 colunas de `repositorios.parquet` seguem a seção 2.

### 7.1 Backfill das colunas `cfr_b*` sem alterar os 330 repositórios

`pipeline/backfill_cfr_b.py` preenche as colunas `cfr_b*` do dataset existente. Para cada repositório, na ordem do arquivo, lê `releases/{owner}__{repo}.parquet` (coletando-o antes, pelo mesmo caminho de `persist_releases`, se não existir), calcula as colunas com a heurística de `cfr_b.heuristica` (`config.yaml`, padrão `v1`) pela mesma função do orquestrador e regrava `repositorios.parquet` e `repositorios.csv` com o esquema completo. Todas as outras colunas e a ordem das linhas são preservadas.

```bash
# a partir de lab03/, com GITHUB_TOKEN definido
uv run python -m pipeline.backfill_cfr_b --config config.yaml            # coleta o que falta e preenche
uv run python -m pipeline.backfill_cfr_b --config config.yaml --offline  # só usa dados/releases/ já existente
```

Opções: `--workers N` (padrão 4) e `--limit N` (só os N primeiros repositórios). O comando é idempotente e retomável: arquivos de `releases/` já coletados são reaproveitados, então uma execução interrompida só coleta o que falta; repositórios que falham mantêm os valores anteriores (nulos) e saem listados no relatório final (código de saída 1). Ele também avisa quando `cfr_b_evaluated_releases + cfr_b_censored_releases + cfr_b_skipped_releases` difere de `releases_count_window`. O backfill **não** reescreve `funil.csv` nem `runs/`.

Execução real (2026-10-20, heurística `v1`, janela 2025-10-01 a 2026-09-30):

| Resultado | Quantidade |
|---|---|
| Repositórios no dataset (mesmos nomes e ordem de antes) | 330 |
| Com `cfr_b` calculado | 328 |
| Sem release avaliável (`cfr_b` e `cfr_b_tier` nulos; todas as releases censuradas) | 2 (`Alishahryar1/free-claude-code`, `expo/expo`) |
| Com ao menos uma release censurada | 141 |
| Com ao menos uma release ignorada (`cfr_b_skipped_releases > 0`) | 0 |
| `cfr_b_tier`: Elite / High / Medium / Low / nulo | 149 / 68 / 48 / 63 / 2 |
| Releases: falhas / avaliadas / censuradas / ignoradas | 7923 / 24681 / 1050 / 0 |

Observações da execução:

- 12 repositórios grandes (por exemplo `llvm/llvm-project`, `rails/rails`) estouraram o timeout fixo de 120 s do `git clone` (`pipeline/git_clone.py`). Foram pré-clonados manualmente com o mesmo comando (`git clone --bare --filter=tree:0 --single-branch`, mais o *fetch* das tags), que o pipeline reaproveita, e o backfill foi reexecutado para coletá-los.
- `PostHog/posthog` tem 2576 releases na janela em `releases_count_window` (coleta original) e 2575 na coleta atual (2165 avaliadas + 410 censuradas); a diferença de uma release vem de a coleta ter sido refeita meses depois. O `releases_count_window` original foi mantido.

### 7.2 Backfill das colunas de pré-releases, tags, C2 e C3

`pipeline/backfill_c2_c3.py` preenche as 8 colunas que restavam nulas (`prereleases_count_window`, `total_prereleases`, `tags_count_window`, `total_tags`, `c2_deployment_frequency`, `c2_lead_time_b_hours`, `c3_deployment_frequency`, `c3_lead_time_b_hours`) sem alterar o conjunto de repositórios. Para cada repositório, na ordem do arquivo:

1. coleta (se ainda não existir **para a janela atual**) as releases e pré-releases via GraphQL e as tags de um clone com o filtro de `pipeline/git_clone.py`, pela **mesma função do orquestrador** (`pipeline.orchestrator.collect_c2_c3_units`: C2 = releases + pré-releases da janela, C3 = todas as tags da janela, datadas pela data de autor do commit, commits via `git log` local). A janela é interpretada como no orquestrador (`parse_window_end`: `fim` só com data vale o fim do dia; denominador de 365/7 semanas);
2. grava `releases_c2/{owner}__{repo}.parquet` e `tags/{owner}__{repo}.parquet` (seções 5 e 6) e `c2_c3_meta/{owner}__{repo}.json` com a janela da coleta, os totais que esses arquivos não guardam (`total_prereleases`, `total_tags`) e os valores de C1 da coleta nova (`releases_count_window`, `total_releases`), usados só para detectar deriva;
3. calcula as colunas a partir desses arquivos com `pipeline.orchestrator.compute_c2_c3_columns`, a mesma função que o orquestrador agora usa, e regrava `repositorios.parquet` e `repositorios.csv` com o esquema completo.

```bash
# a partir de lab03/, com GITHUB_TOKEN definido
uv run python -m pipeline.backfill_c2_c3 --config config.yaml            # coleta o que falta e preenche
uv run python -m pipeline.backfill_c2_c3 --config config.yaml --offline  # só usa os arquivos já coletados
```

Opções: `--workers N` (padrão 4) e `--limit N`. O comando é idempotente (duas execuções `--offline` seguidas geram o mesmo CSV byte a byte) e retomável: um repositório só é considerado coletado quando os três arquivos existem (o JSON é gravado por último) e a janela gravada no JSON é a do `config.yaml`; arquivos coletados com outra janela são recoletados. Falhas deixam as colunas do repositório como estavam no dataset de entrada (nulas) e saem no relatório (código de saída 1). Todas as outras 30 colunas e a ordem das linhas são preservadas (conferido contra o `repositorios.parquet` anterior). O backfill **não** reescreve `funil.csv` nem `runs/`.

Execução real (2026-10-21, janela 2025-10-01 a 2026-09-30 com fim do dia, 365 dias; o clone usou o mesmo filtro `tree:0` do pipeline):

| Coluna | Nulos antes | Nulos depois | Valores nos 329 repositórios preenchidos |
|---|---|---|---|
| `prereleases_count_window` | 330 | 1 | soma 7481, mediana 0 (142 repositórios com ao menos uma) |
| `total_prereleases` | 330 | 1 | soma 11613, mediana 2 (185 repositórios com ao menos uma) |
| `tags_count_window` | 330 | 1 | soma 57016, mediana 43, mínimo 5 |
| `total_tags` | 330 | 1 | soma 191132, mediana 230, mínimo 7 |
| `c2_deployment_frequency` | 330 | 1 | mediana 0,633 deploys/semana |
| `c2_lead_time_b_hours` | 330 | 2 | mediana 267,2 h em 328 repositórios |
| `c3_deployment_frequency` | 330 | 1 | mediana 0,825 tags/semana |
| `c3_lead_time_b_hours` | 330 | 1 | mediana 237,5 h |

Semântica dos valores nulos e casos limite:

- **`MadsLorentzen/ai-job-search`: as 8 colunas ficam nulas.** O repositório foi movido para `ai-job-search-dev/ai-job-search` e está desabilitado no GitHub (`git clone` falha com "Repository ... is disabled"), então as releases e tags não podem ser recoletadas. Uma coleta anterior à mudança da janela existia, mas foi descartada para não misturar janelas na mesma linha. As demais colunas desse repositório seguem como na coleta original.
- `c2_lead_time_b_hours` é nulo também em `expo/expo`: as 146 unidades C2 da janela não têm nenhum commit novo entre releases consecutivas (uma delas é `not_found`), então não há lead time por commit. É um nulo legítimo da definição (como o `lead_time_b_hours` de C1, nulo em 61 repositórios); não foi forçado nenhum valor. `c3_lead_time_b_hours` só é nulo em `ai-job-search`.
- `prereleases_count_window = 0` quando não há pré-release na janela (187 dos 329 repositórios); nesse caso as unidades C2 coincidem com as de C1. Pré-releases existem em 185 repositórios (`total_prereleases > 0`), 43 deles só fora da janela.
- `tags_count_window` e `total_tags` não são zero em nenhum repositório (mínimos observados: 5 e 7).
- **Janela nova × colunas antigas.** As colunas novas usam a janela vigente no `config.yaml` (fim do dia 30/09 e denominador 365/7 ≈ 52,14 semanas), mas as 30 colunas anteriores (inclusive `releases_count_window`, `deployment_frequency` e `cfr_b*`) ainda foram calculadas com a janela antiga (`fim` = 30/09 00:00Z, denominador 52,1) e só mudam quando o dataset for regenerado com a janela nova (seção "Janela de observação"). Por isso `releases_count_window` difere da contagem C1 da coleta nova em 60 repositórios, sempre para mais (releases publicadas em 30/09, por exemplo `PostHog/posthog`, +96), e `c2_deployment_frequency` não é comparável diretamente com `deployment_frequency` na mesma linha enquanto isso não ocorrer.
- **Deriva de `total_releases`.** As colunas novas refletem o GitHub em 2026-10-21; `total_releases` é maior na coleta nova em 69 repositórios, porque a coleta pagina da mais recente para a mais antiga e novas releases publicadas depois da coleta original empurram a âncora para páginas posteriores. Como `total_prereleases` vem da coleta nova, em `vercel/next.js` (610 pré-releases contra `total_releases` = 600) e `abhigyanpatwari/GitNexus` (976 contra 969) o invariante "pré-releases estão contidas em `total_releases`" não vale no dataset; `total_releases` não foi alterado.
- `tags/` guarda a comparação de uma tag sem commits como `ok`, sem diferenciá-la de `not_found`; isso não afeta nenhuma das 8 colunas, que só usam a contagem na janela e a mediana por commit.
- 12 repositórios grandes e alguns outros estouraram o timeout fixo de 120 s do `git clone`/`git log` (`pipeline/git_clone.py`) com o clone feito pelo próprio comando; foram pré-clonados manualmente (mesmo comando, mais o *fetch* das tags), que o pipeline reaproveita. `openbq-org/OpenBB` tem tags que só diferem na caixa das letras e não pode ser clonado em um sistema de arquivos que ignora caixa com o backend de referências padrão; foi clonado com `--ref-format=reftable`.

### 7.3 Regeneração final dos 330 repositórios (Issue #56)

`pipeline/regenerar.py` faz a **única regeneração final** do dataset sobre os 330 repositórios **congelados** (a seleção não é refeita e `funil.csv` não é tocado). Lê a lista de `repositorios.csv`, recalcula **todas as colunas de métricas** de exatamente esses repositórios, na mesma ordem, com as regras atuais (janela até o fim do dia, divisão recursiva de runs sem piso, filtro de clone, mensagens completas dos commits, regras de nulos, CFR (b) em C1 e em C2 e todas as colunas C2/C3) pelas mesmas funções do pipeline (`compute_metric_columns`). As colunas de metadados da seleção (`owner`, `name`, `full_name`, `stars`, `language`, `default_branch`, `created_at`, `contributors_count`) são copiadas do dataset versionado e nunca recalculadas.

```bash
# a partir de lab03/, com GITHUB_TOKEN (ou GITHUB_TOKENS) definido
uv run python -m pipeline.regenerar --config config.yaml --limit 3     # teste: coleta 3 repositórios, não publica nada
uv run python -m pipeline.regenerar --config config.yaml --fresh       # coleta tudo e publica
uv run python -m pipeline.regenerar --config config.yaml --resume      # retoma uma execução interrompida
uv run python -m pipeline.regenerar --config config.yaml --somente-relatorio
```

Opções: `--workers K` (padrão 4), `--limpar-clones` (apaga cada clone bare após o uso; por padrão eles são mantidos para retomar sem reclonar) e `--relatorio CAMINHO` (padrão `docs/regeneracao_final.md`).

- **Estado de trabalho** (ignorado pelo git) em `dados/.regenerar/`: `baseline.parquet|csv` (cópia do dataset de antes, usada como lista de repositórios e como lado "antes" do relatório), `checkpoint.jsonl` (uma linha por repositório concluído) e `runs/` (runs regenerados). Um checkpoint de outra janela, heurística ou esquema é ignorado; uma execução sem `--resume` com checkpoint existente é recusada (use `--resume` ou `--fresh`).
- **Publicação tudo ou nada:** só quando os 330 repositórios foram coletados (sem `--limit` e sem falhas) e as invariantes valem (330 linhas, mesmos nomes e ordem, metadados idênticos, esquema completo, CSV e Parquet com as mesmas colunas), o comando grava `repositorios.parquet|csv`, copia os runs regenerados para `runs/<owner>__<repo>.parquet`, remove de `runs/` os arquivos que não são de nenhum dos 330 repositórios (`git rm` quando versionados; os três órfãos `elastic__elasticsearch`, `home-assistant__core` e `ueberdosis__tiptap`) e escreve o relatório `docs/regeneracao_final.md` (antes × depois por coluna, transições de faixa, repositórios com faixa geral alterada, contagem de nulos e invariantes).
- Falhas por repositório (rede, clone) não interrompem a execução: ficam listadas no resumo (sem tokens), o código de saída é 1 e nada é publicado; basta rodar de novo com `--resume`.
- **Modo dos runs (`--runs-modo`)**: `completo` (padrão) coleta os runs da janela inteira com o coletor recursivo; `reconciliar` parte dos runs já versionados (`runs/`, janela anterior definida em `regeneracao.janela_anterior` do `config.yaml`) e, para cada intervalo mensal, pede à API só o `total_count` (1 requisição, mesmos filtros do coletor: branch padrão, `event=push`, `created`): se bate com os runs já coletados no intervalo, eles são mantidos; se difere (intervalo truncado em 1.000, runs removidos/expirados, reexecuções que deslocam o intervalo), o intervalo é recoletado com a divisão recursiva; o trecho final da janela (30/09 após 00:00:00Z até 23:59:59Z) é sempre coletado. Custo típico: ~12 requisições de contagem por repositório mais as recoletas. `--validar-reconciliacao OWNER/REPO ...` compara reconciliação × coleta completa (ids de runs e métricas derivadas) sem publicar nada. O relatório lista os intervalos recoletados e o motivo.
- **Execução desacoplada:** `--status ARQUIVO` mantém um `status.json` (progresso, requisições, cota, ETA, último erro) e `--bundle-dir DIR` gera `outputs-<data UTC>.tar.gz` (+ `.sha256`) ao concluir. `scripts/regen_supervisor.sh` roda a regeneração com `--resume`, reinicia após falhas (espera de 60 s a 10 min) e escreve o marcador `DONE`; instruções em `docs/regeneracao_final.md`, seção "Execução desacoplada".
- **Repositório indisponível:** os listados em `regeneracao.manter_valores_anteriores` (`config.yaml`) ou em `--manter-antigo OWNER/REPO` (hoje `MadsLorentzen/ai-job-search`, desabilitado no GitHub) que não puderem ser recoletados **permanecem entre os 330** com os valores de métricas anteriores inalterados (colunas novas nulas) e o `runs/` anterior; o relatório os lista com o motivo. Qualquer outro repositório que falhe continua bloqueando a publicação.
- Repositórios que, após a recoleta, ficarem abaixo dos mínimos da seleção (5 releases, 50 runs válidos) **permanecem** no dataset (a amostra é congelada) e são listados no relatório.

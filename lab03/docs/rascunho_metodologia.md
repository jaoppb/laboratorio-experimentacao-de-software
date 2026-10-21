# Rascunho da seção de Metodologia (Issue #68)

> **Estado:** rascunho em Markdown para colar e adaptar no Overleaf (template SBC). O texto final do
> artigo **não** vive neste repositório; este arquivo existe para que os números e as definições
> citados batam com o que o código e os CSVs versionados realmente fazem.
>
> **Legenda dos marcadores**
>
> * `[PENDENTE: ...]`: informação que ainda **não existe** (resultado, decisão ou etapa humana). Diz
>   qual issue ou arquivo vai fornecê-la. Não preencher com estimativas.
> * `[VERIFICAR: ...]`: inconsistência ou dúvida encontrada ao cruzar documentos, código e CSVs.
>   Precisa ser resolvida pelos autores antes da submissão.
> * `[REF: ...]`: citação bibliográfica que **não** consta nos documentos do repositório. Foi deixada
>   como marcador para não inventar referência; os autores devem localizar a fonte.
>
> **Regras seguidas:** tudo o que está afirmado abaixo foi derivado do código (`metricas/`,
> `pipeline/`, `analises/`), dos documentos em `lab03/docs/`, do `config.yaml` e dos CSVs
> versionados. O apêndice B liga cada afirmação ao arquivo de origem. Nenhum resultado de análise
> (kappa, precisão/recall/F1, correlações, testes) é reportado, porque nenhum existe ainda.
>
> **Tamanho.** O guia limita o artigo a 10 páginas. Este rascunho é deliberadamente mais longo que a
> versão final: os autores devem condensar (sugestão: mover as fórmulas e tabelas de apoio para o
> repositório e citar `lab03/dados/README.md`).
>
> **Divisão da escrita (corpo da Issue #68).** Marcela: seções 3.2, 3.3 e 3.7 (fonte de dados,
> funil, janela, validação manual e kappa). Gabriel: seções 3.5 (lead time), 3.6 (CFR (b) e
> heurística) e os motivos de nulos da 3.9. João: seções 3.4 (pipeline, cache, rate limit, justificativa
> do clone *blobless*), 3.5 (CFR (a), recuperação e censura) e o dicionário de dados.

---

## 3. Metodologia

### 3.1 Desenho do estudo

Trata-se de um estudo observacional, quantitativo e baseado em mineração de repositórios. A unidade
de análise é o **repositório** open-source do GitHub que usa GitHub Actions. Para cada repositório,
calculamos as quatro métricas DORA (*deployment frequency*, *lead time for changes*, *change
failure rate* e tempo de recuperação) (Forsgren, Humble & Kim, 2018; DORA, [guia das métricas](https://dora.dev/guides/dora-metrics-four-keys/))
dentro de uma janela de observação de 12 meses.

Como o GitHub não registra *deploys* nem falhas em produção, todas as métricas são **proxies**:
uma *release* publicada representa um *deploy*, e uma execução de CI com falha representa uma falha.
Por isso o estudo inclui, além do cálculo das métricas, (i) uma **validação manual** do proxy de
falha por entrega (CFR (b)) contra o julgamento humano e (ii) uma **análise de sensibilidade** sobre
as definições operacionais (RQ 07).

**Tabela 1.** Questões de pesquisa, métricas e análise planejada.

| RQ | Pergunta | Métrica / variantes | Análise planejada | Hipótese informal (a priori) |
|---|---|---|---|---|
| RQ 01 | Qual a frequência de deploys? | *Deployment frequency* = releases publicadas na janela ÷ 52,1 semanas | mediana, IQR e faixa DORA | `artigo_contexto_e_hipoteses.md` |
| RQ 02 | Qual o tempo entre commit e deploy? | *Lead time*: (a) por release; (b) por commit | mediana, IQR e faixa DORA; contraste (a) × (b) | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 03 | Qual a taxa de falha das mudanças entregues? | CFR: (a) proxy de CI; (b) proxy de entrega (release corretiva em até 7 dias) | mediana, IQR e faixa DORA; contraste (a) × (b) | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 04 | Qual o tempo de recuperação após falha de CI? | Duração de episódios de falha por workflow; proporção de episódios censurados | mediana, IQR e faixa DORA | `docs/hipoteses_rq04_rq07.md` |
| RQ 05 | Maior frequência de deploy implica maior ou menor taxa de falha? | Correlação de Spearman entre RQ 01 e RQ 03, para CFR (a) e CFR (b) | ρ, p-valor e n | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 06 | Que características dos repositórios se associam ao desempenho? | Métricas das RQ 01 a 04 comparadas entre subgrupos | Kruskal-Wallis / Mann-Whitney, correção de Holm, ε² / Cliff's δ | `artigo_contexto_e_hipoteses.md` |
| RQ 07 | A classificação DORA depende da definição operacional? | Combinações C1, C2 e C3 (seção 3.5.6) | % de mudança de categoria e κ ponderado linear | `docs/hipoteses_rq04_rq07.md` |
| RQ 08 (bônus) | (Rework rate ou evolução temporal) | — | — | `[PENDENTE: decisão do grupo sobre fazer ou não a RQ 08; nada disso existe no repositório]` |

As hipóteses informais foram escritas **antes** da coleta e da análise dos dados, conforme o guia, e
estão na Introdução do artigo; esta seção não as repete.

### 3.2 Fonte de dados e janela de observação

**Fonte.** Os dados vêm da API REST e da API GraphQL do GitHub, mais um clone Git local de cada
repositório (seção 3.4). Seguindo o guia, a coleta é feita por código próprio (cliente HTTP
assíncrono sobre `httpx`), sem bibliotecas prontas de acesso à API do GitHub.

**Janela.** A janela de observação tem 12 meses, de **01/10/2025 a 30/09/2026** (`janela.inicio` e
`janela.fim` em `config.yaml`). Entram nos cálculos apenas releases publicadas e *workflow runs*
criados dentro da janela. Para a frequência de deploy, divide-se a contagem de releases por **52,1
semanas** (≈ 365/7, constante `DEFAULT_WINDOW_WEEKS` em `metricas/dora.py`, valor indicado pelo guia
para 12 meses). Como o limite superior é lido como 30/09/2026 às 00:00 UTC (ver abaixo), o intervalo
efetivo tem 364 dias (52,0 semanas); a diferença no denominador é de cerca de 0,2%.
`[VERIFICAR: o config.yaml diz que as datas foram "fixadas para a Sprint 01 conforme o enunciado" e são "ajustáveis caso o professor defina janela específica", e o guialab03.md só diz que o professor fixa as datas na abertura do Lab03S01, sem trazê-las; confirmar com o professor/enunciado que 01/10/2025-30/09/2026 é a janela oficial da turma.]`
`[VERIFICAR: "2026-09-30" é lido como 2026-09-30T00:00:00Z (metricas/schemas.py::_parse_datetime). Verificado no código que isso vale para as duas pontas: releases entram se start <= published_at <= end (pipeline/releases.py::filter_window) e o último intervalo mensal de runs termina em 2026-09-30T00:00:00Z (pipeline/workflow_runs.py::split_window_into_months), então releases e runs de 30/09 depois de 00:00 UTC ficam de fora do limite superior; decidir se isso é aceitável ou se o limite deve ser o fim do dia.]`

**Data da coleta.** `[PENDENTE: data(s) exata(s) da coleta e da regeneração final do dataset, a registrar na consolidação do dataset (#56). Indício (histórico do git): as 100 primeiras linhas de repositorios.csv vêm do commit da refatoração #47, de 10/10/2026, e o commit da amostra de 330 repositórios (#53) é de 14/10/2026.]`
Como a Search API e as contagens (estrelas, releases, runs) refletem o estado do GitHub no momento
da coleta, uma nova execução pode produzir uma amostra ligeiramente diferente.

**Branch.** Considera-se apenas o *default branch* de cada repositório (`defaultBranchRef` do GraphQL).

### 3.3 Seleção de repositórios e funil

**Candidatos.** A Search API é consultada com fatiamento por faixas de estrelas, para contornar o
teto de 1.000 resultados por consulta: `>10000`, `5001..10000`, `2501..5000`, `1501..2500` e
`1000..1500`. Cada consulta usa os qualificadores `archived:false`, `mirror:false` e `size:>1000`,
ordenação por estrelas decrescente e até 10 páginas de 100 resultados. Duplicatas entre faixas são
unificadas por `owner/name`. As faixas são percorridas na ordem acima e os candidatos são avaliados
na ordem em que chegam; como o funil avaliou menos de 1.000 candidatos (653 na Tabela 2), a primeira
faixa (`>10000`) basta para explicar a amostra, e as demais não devem ter sido alcançadas (inferência
a partir da contagem do funil e do teto de 1.000 resultados por consulta; o log da execução não está
versionado).

**Critérios de inclusão (aplicados nesta ordem a cada candidato).**

1. **Uso de GitHub Actions:** `GET /repos/{owner}/{repo}/actions/workflows` com `total_count > 0`
   (erro de acesso conta como descarte).
2. **≥ 5 releases na janela:** releases publicadas (`draft = false` e `prerelease = false`) com
   `published_at` dentro da janela.
3. **≥ 50 *workflow runs* válidos no default branch na janela:** runs do evento `push` cuja
   conclusão é `success` ou falha (`failure`, `timed_out`, `startup_failure`); as demais conclusões
   não contam.
4. **Integridade do clone local:** repositórios cuja etapa de clone local falha de forma irrecuperável
   são descartados (no código, qualquer exceção nessa etapa, que inclui o `git clone`, a leitura das
   tags e dos commits e a gravação dos Parquet de releases).

Erros de coleta são contados na etapa em que ocorrem: uma falha ao obter as releases (inclusive na
rota de contingência REST) entra no descarte "menos de 5 releases", e uma falha ao obter os *runs*
entra no descarte "menos de 50 runs" (`pipeline/orchestrator.py::evaluate_candidate`). Esses
descartes por erro não são distinguidos dos descartes por critério no `funil.csv`.

**Seleção da amostra final.** Os candidatos são avaliados em ordem decrescente de estrelas, por
4 trabalhadores assíncronos concorrentes (padrão de `PipelineOrchestrator`), e a avaliação **para ao
atingir 330 repositórios aceitos** (`amostra.tamanho_final`). Na prática, a amostra é composta dos
repositórios mais populares que cumprem todos os critérios. Como há concorrência, a ordem de aceitação
pode divergir levemente da ordem estrita de estrelas.

A amostra atual resulta de **duas execuções** do pipeline com retomada: as 100 primeiras linhas de
`dados/repositorios.csv` são exatamente os 100 repositórios aceitos na execução da Issue #47 (commit
de 10/10/2026), e as 230 seguintes foram acrescentadas no commit que escalou a coleta (Issue #53,
14/10/2026).
Na retomada, os repositórios já aceitos são pulados. Por isso o arquivo não está ordenado por
estrelas, e as estrelas dos dois blocos foram medidas em momentos diferentes.

**Tabela 2.** Funil de seleção: valores de `dados/funil.csv` (rótulos das etapas abreviados).

| Etapa | Restantes | Descartados | Motivo |
|---|---:|---:|---|
| Candidatos avaliados até atingir a meta (Search API) | 653 | — | — |
| Uso de CI/CD (GitHub Actions) | 597 | 56 | `total_count` de workflows = 0 ou erro de acesso |
| ≥ 5 releases publicadas na janela | 282 | 315 | menos de 5 releases na janela |
| ≥ 50 *workflow runs* válidos na janela | 232 | 50 | menos de 50 runs válidos no default branch |
| Integridade do clone local | 230 | 2 | falha irrecuperável no `git clone` |
| **Amostra final** | **330** | — | — |

`[VERIFICAR: a coluna "restantes" do funil.csv não fecha. 653 − 56 − 315 − 50 − 2 = 230, mas a amostra final é 330. A soma dos descartes (423) mais as 330 aceitas dá 753, ou seja, exatamente 100 a mais que o 653 da primeira linha, e as quatro linhas intermediárias ficariam 697, 382, 332 e 330. Evidências já conferidas: (i) as 100 primeiras linhas de repositorios.csv são exatamente os 100 repositórios do repositorios.csv do commit da Issue #47; (ii) 230 + 100 = 330; (iii) no código, o contador total_evaluated parte de 0 quando não há .pipeline_state.json (pipeline/orchestrator.py::_load_state) e os 100 aceitos anteriores só entram em accepted_records/evaluated_names, não no contador. Isso torna provável que o funil conte apenas a segunda execução, mas NÃO está confirmado, porque o .pipeline_state.json e o log da execução não são versionados. Antes de publicar a Tabela 2, a Marcela (#31/#66) deve confirmar a causa e corrigir o funil.csv (o funil completo seria 753 → 697 → 382 → 332 → 330 se os 100 aceitos antes forem somados a todas as etapas); este rascunho não altera o arquivo.]`

A primeira linha conta os candidatos **avaliados**, e não todos os resultados que a Search API
devolveria, porque a avaliação para ao atingir a meta (`docs/criterios_selecao_e_funil.md`).

**Caracterização da amostra.** Valores calculados sobre as 330 linhas de `dados/repositorios.csv`
(24 colunas nessa versão do arquivo; estrelas medidas no momento da coleta de cada bloco de repositórios):

| Característica | Valor |
|---|---|
| Repositórios | 330 (todos distintos) |
| Estrelas | mínimo 38.855; mediana 59.203,5; máximo 391.529 |
| Linguagens principais distintas | 23 (TypeScript 93, Python 76, Go 37, Rust 34, JavaScript 28; nenhuma linha sem linguagem) |
| Releases publicadas na janela | mínimo 5; mediana 26; máximo 2.584 |
| *Workflow runs* válidos na janela | mínimo 51; mediana 1.562; máximo 89.089 |
| Data de criação do repositório | de 11/04/2008 a 01/07/2026 |

Observação importante para a validade externa: embora a busca aceite repositórios a partir de 1.000
estrelas, a amostra final tem **mínimo de 38.855 estrelas**, efeito direto de parar a avaliação nos
330 primeiros aceitos em ordem de popularidade.

`[PENDENTE: reconferir esta tabela depois da regeneração do dataset (#56); o repositorios.csv versionado ainda é anterior às colunas novas e à correção do lead time, e a amostra pode mudar numa nova coleta.]`

### 3.4 Coleta de dados e pipeline

A coleta roda com um único comando (`uv run python -m pipeline --config config.yaml`; `--limit N`
para amostras reduzidas e `--clean` para regenerar o dataset). O token é lido de `GITHUB_TOKEN`
(ou vários, em `GITHUB_TOKENS`) ou do `gh auth token`, e nunca é versionado.

**Metadados e releases.** Uma consulta GraphQL por repositório (`pipeline/graphql/queries/repo_details.graphql`)
traz estrelas, linguagem principal, default branch, data de criação e as releases (tag, data de
publicação, *draft* e *pre-release*), da mais recente para a mais antiga. A paginação para na página
que contém a **release âncora**: a última release estável anterior à janela, usada como predecessora
da primeira release da janela. Rascunhos e releases sem data de publicação são descartados na coleta.
O número de contribuidores é obtido por `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true`,
lendo o número da última página no cabeçalho `Link`. Se o GraphQL falhar, há uma rota de contingência
em REST.

***Workflow runs*.** `GET /repos/{owner}/{repo}/actions/runs` com `branch` = default branch,
`event=push` e `created=<início>..<fim>`. A janela é dividida em intervalos mensais consultados em
paralelo. Se um intervalo devolve `total_count ≥ 1.000` (teto da API), ele é dividido ao meio
recursivamente (profundidade máxima 3, intervalo mínimo de 2 dias). Os runs são deduplicados por `id`
e gravados em `dados/runs/{owner}__{repo}.parquet`. Registramos para cada run o `workflow_id`, a
`conclusion`, `run_started_at` e `updated_at`.

**Commits de cada release: clone Git local no lugar do `compare`.** O guia sugere obter os commits
de uma release com `GET /compare/{base}...{head}`. O pipeline, desde a Issue #47, obtém os mesmos
commits com `git log {release anterior}..{release}` em um **clone *bare* e *blobless***
(`git clone --bare --filter=tree:0 --single-branch`), seguido de
`git fetch --filter=tree:0 origin +refs/tags/*:refs/tags/*` para trazer todas as tags. A semântica
é a do `compare` (commits alcançáveis pela release e não pela anterior), com estas vantagens:

* **não consome cota da API**, o que importa para 330 repositórios com milhares de releases (a base
  tem 25.732 releases na janela);
* **não tem o teto de 250 commits** nem exige paginação do `compare`;
* o clone sem árvores nem arquivos (`tree:0`) baixa só o histórico de commits, o que é leve.

O clone tenta primeiro sem autenticação e, se falhar por limite de taxa ou autenticação, tenta de
novo com um token do conjunto. O clone temporário é apagado depois do uso. A primeira versão do clone
trazia só as tags alcançáveis do default branch e fazia o pipeline descartar como "tag não
encontrada" 20,6% das releases da janela; o `fetch` de todas as tags corrigiu isso (seção 3.9,
`docs/investigacao_lead_time.md`). A implementação via REST (`pipeline/commits.py`) continua no
código e testada, mas não é a usada na coleta.

**Datas e mensagens dos commits.** Cada commit é guardado com SHA, data do **autor**
(`%aI`, equivalente a `commit.author.date`, como manda o guia) e **assunto** da mensagem (primeira
linha, `%s`). Diferença em relação à REST: o corpo da mensagem não é coletado (ver ameaça à validade
na seção 3.9).

**Releases, pré-releases e tags (C1, C2 e C3).** Para a RQ 07, o pipeline coleta três conjuntos de
"unidades de deploy" na mesma rodada, cada um com a lista de commits entre unidades consecutivas:

| Conjunto | Unidade de deploy | Arquivo (por repositório) | Datação |
|---|---|---|---|
| C1 (definição principal) | releases publicadas, sem pré-releases | `dados/releases/` | `published_at` da release |
| C2 | releases publicadas **e** pré-releases | `dados/releases_c2/` | `published_at` da release |
| C3 | tags Git | `dados/tags/` | data do autor do commit apontado pela tag |

Em cada conjunto, a **predecessora** de uma unidade é a unidade imediatamente anterior na ordem
cronológica; para a primeira unidade da janela, é a âncora (a última unidade anterior à janela). Se
não há âncora, a unidade é a primeira da história do repositório (`first_release`) e não entra no
lead time. Se a tag da release ou da predecessora não existe no clone (equivalente ao 404 do
`compare`), a unidade recebe o status `not_found` e também fica fora do lead time. Cada unidade é
marcada com `ok`, `first_release` ou `not_found`, e essas contagens são reportadas (seção 3.9).

**Robustez e retomada.** O cliente HTTP lê `X-RateLimit-Remaining` e `X-RateLimit-Reset`, alterna
entre vários tokens, coloca em espera o token que atinge o limite e, sem token, espera o reinício
da cota. Erros 5xx e de rede são repetidos com *backoff* exponencial (1 s, 2 s, 4 s, ..., até 5
tentativas). Toda resposta 2xx é gravada em um cache SQLite em disco (modo WAL), e cada repositório
aceito é gravado de forma incremental em `dados/repositorios.parquet`/`.csv`; assim, uma execução
interrompida continua de onde parou, sem repetir chamadas. As funções de métricas e do pipeline têm
testes automatizados com *fixtures* sintéticas (pytest) e cobertura mínima de 80% (módulos
`metricas` e `pipeline`), executados no GitHub Actions do repositório (`.github/workflows/testes-lab03.yml`).

### 3.5 Definições operacionais e métricas

Todas as fórmulas abaixo estão implementadas em `metricas/` e documentadas coluna a coluna em
`dados/README.md`. Os tempos são calculados em horas; para classificar, o lead time (variante (a))
é convertido em dias (÷ 24) e o tempo de recuperação permanece em horas (3.5.5).

#### 3.5.1 Frequência de deploy (RQ 01)

$$\text{DF} = \frac{\text{releases publicadas na janela (draft = false, prerelease = false)}}{52{,}1\ \text{semanas}}$$

#### 3.5.2 Lead time (RQ 02)

Para cada release $R$ da janela com predecessora disponível, sejam $C_R$ os commits incluídos em $R$
(`git log anterior..R`, isto é, os alcançáveis por $R$ e não pela predecessora, o que inclui commits de
*merge* e de ramos mesclados), $\text{autor}(c)$ a data do autor do commit $c$ (`commit.author.date`)
e $t_R$ a data de publicação de $R$ (`published_at`).

* **(a) por release:** $LT_a(R) = t_R - \min_{c \in C_R} \text{autor}(c)$. O valor do repositório é a
  **mediana** de $LT_a$ entre as releases.
* **(b) por commit:** $LT_b(c) = t_R - \text{autor}(c)$ para todo $c \in C_R$. O valor do repositório é
  a **mediana de todos os commits de todas as releases**.

Regras: (i) release `first_release` ou `not_found` é ignorada e contada; (ii) release **sem commits
novos** (lista vazia) não contribui para nenhuma das duas variantes, pois não há "commit mais
antigo"; (iii) se a data do commit é posterior à da release (relógio adiantado, *rebase*), o lead
time é truncado em 0. Dentro de uma mesma release, $LT_b \le LT_a$ sempre (o commit mais antigo define
$LT_a$; o truncamento em 0 preserva a desigualdade); entre releases, a mediana de (b) pode superar a de
(a), porque (a) dá peso 1 a cada release e (b) dá a cada release o peso do seu número de commits
(`docs/investigacao_lead_time.md`, seção 4). Na base de 330 repositórios, 138 têm mediana (b) maior que
a (a) (`dados/analises/lead_time_diagnostico.csv`); nos quatro casos de maior concentração, conferidos
à mão, a causa foi uma release *major* grande e antiga cercada de *patches* pequenos e rápidos. A
verificação automática do invariante por release não encontrou nenhuma violação.

Como só SHAs, datas de autor e assuntos são lidos, o clone sem árvores nem arquivos (`tree:0`) não
altera o lead time. O que o alterou foi o `--single-branch`, que omitia tags de ramos de manutenção
(seção 3.9).

#### 3.5.3 Taxa de falha de mudanças, variante (a): proxy de CI (RQ 03 e RQ 05)

$$\text{CFR}_a = \frac{\#\text{falhas}}{\#\text{falhas} + \#\text{sucessos}}$$

calculada sobre todos os *workflow runs* do default branch com `event = push`, **todos os workflows
juntos**. A classificação da conclusão segue o guia:

| `conclusion` | Tratamento |
|---|---|
| `success` | sucesso |
| `failure`, `timed_out`, `startup_failure` | falha |
| `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio (em andamento) | ignorado: fora do numerador e do denominador |

O $\text{CFR}_a$ é nulo se o repositório não tem nenhum run de sucesso ou falha. Esta variante mede
falha de **pipeline**, e não falha em produção.

#### 3.5.4 Tempo de recuperação e censura (RQ 04)

Os runs são agrupados por workflow e ordenados por `run_started_at`. Dentro de cada workflow,
conclusões ignoradas não iniciam, interrompem nem encerram episódios. Um **episódio de falha** começa
na primeira falha (após um sucesso, ou no início do histórico) e inclui as falhas consecutivas; ele
termina no próximo sucesso do mesmo workflow. A duração é

$$\text{recuperação} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira falha}}$$

(truncada em 0). O valor do repositório é a **mediana** das durações dos episódios resolvidos, de
todos os workflows. Um episódio que não termina até o fim do histórico coletado é **censurado**, e
o pipeline registra a proporção `censored_episodes_ratio = censurados ÷ (resolvidos + censurados)`
(0 se não há episódios). Os episódios censurados **não são descartados da contagem**, mas também
**não entram na mediana**, que usa apenas os episódios resolvidos (ver ameaça na seção 3.9). O valor
é nulo se nenhum episódio foi resolvido.

#### 3.5.5 Classificação DORA (faixas fixas da disciplina)

Usamos os cortes fixos da disciplina, adaptados das faixas dos relatórios DORA (que mudam a cada
edição), para que toda a turma classifique da mesma forma.

| Métrica | Elite | High | Medium | Low |
|---|---|---|---|---|
| Frequência de deploy | ≥ 7 /semana | ≥ 1 e < 7 /semana | ≥ 1 /mês (12 ÷ 52,1 ≈ 0,23 /semana) e < 1 /semana | < 1 /mês |
| Lead time (mediana, variante (a)) | < 1 dia | 1 dia a < 7 dias | 7 a < 30 dias | ≥ 30 dias |
| CFR | ≤ 15% | > 15% e ≤ 30% | > 30% e ≤ 45% | > 45% |
| Tempo de recuperação (mediana) | < 1 h | 1 h a < 24 h | 24 h a < 168 h | ≥ 168 h |

A **classificação geral** atribui 4, 3, 2 e 1 pontos a Elite, High, Medium e Low em cada uma das
quatro métricas; a categoria é a **mediana** das quatro notas **arredondada para baixo** (por
exemplo, notas 4, 3, 3 e 1 dão mediana 3, logo High). No dataset atual, a faixa de lead time usa a
variante (a), a de CFR usa a variante (a) e o CFR (b) **não** entra na nota geral.

Tratamento de valores ausentes: se lead time, CFR ou tempo de recuperação são nulos, o código
(`metricas/dora.py::classify_*`) atribui a faixa **Low** (nota 1) àquela métrica; só `cfr_b_tier` é
deixado nulo. A frequência de deploy nunca é nula.
`[VERIFICAR: esse tratamento penaliza repositórios sem episódios de falha resolvidos. No dataset versionado, os 18 repositórios com recovery_hours nulo se dividem em 15 sem nenhum episódio de falha (todos com cfr_a = 0) e 3 só com episódios censurados; todos ficam com recovery_tier = Low. Como cálculo de verificação, tratar como Elite os 15 sem episódios mudaria a classificação geral de 14 deles. Também no dataset versionado, os 61 repositórios com lead_time_a_hours nulo ficam Low em lead time; com o lead time corrigido (docs/investigacao_lead_time.md) resta 1 nulo (expo/expo). Decidir se o artigo mantém a regra, declara a limitação ou analisa os nulos à parte.]`

Em todas as RQs, reportamos **mediana e intervalo interquartil (IQR)**, e não média e desvio-padrão,
por causa da assimetria das distribuições, como pede o guia.

#### 3.5.6 Combinações de definições para a análise de sensibilidade (RQ 07)

| Combinação | Unidade de deploy | Lead time | CFR |
|---|---|---|---|
| C1 (referência) | release (sem pré-release) | (a) | (a) |
| C2 | release + pré-release | (b) | (b) |
| C3 | tag | (b) | (a) |

O dataset traz, além da referência, `c2_deployment_frequency`, `c2_lead_time_b_hours`,
`c3_deployment_frequency` e `c3_lead_time_b_hours`. Em C3, a data de uma tag é a data do autor do commit
apontado por ela (`git for-each-ref`, não a data de criação da tag), e não o `published_at` de uma
release.
`[VERIFICAR: o cfr_b do dataset é calculado sobre as releases de C1 (dados/README.md, seção 2.1; pipeline/orchestrator.py chama compute_cfr_b_columns com release_commits_c1), e não sobre as de C2 (releases + pré-releases). A combinação C2 definida no guia usa CFR (b); decidir, ao implementar a RQ 07, se o CFR (b) de C2 será recalculado sobre C2 ou se isso será declarado como limitação.]`

### 3.6 CFR (b) e a heurística de release corretiva

**Definição.** Uma release $R$ **falha** se for seguida, **em até 7 dias**, por uma release
**corretiva**, isto é, uma release cujo objetivo principal é corrigir um defeito recente. O
$\text{CFR}_b$ do repositório é `releases que falharam ÷ releases avaliadas`. O guia não define como
identificar uma release corretiva e pede que o grupo proponha uma heurística automática e a valide
contra a amostra rotulada manualmente (seção 3.7).

**Classificação de cada release da janela** (`metricas/cfr_b.py::calculate_cfr_b`, as unidades em
ordem cronológica, C1):

1. **Censurada:** publicada depois de `janela.fim − 7 dias`. Como `"2026-09-30"` é lido como
   2026-09-30T00:00Z, isso vale para releases publicadas depois de 23/09/2026 00:00 UTC. Ainda não se sabe
   se haverá correção; fica fora do denominador.
2. **Sem falha:** não existe próxima release, ou a próxima veio **mais de 7 dias** depois (exatamente 7
   dias ainda conta como "em até 7 dias", conforme `test_corrective_release_exactly_seven_days_later_counts`).
3. **Ignorada (*skipped*):** a próxima veio em até 7 dias, mas os commits dela são desconhecidos
   (`status` `first_release` ou `not_found`), então não dá para julgar se ela é corretiva; fica fora do
   denominador.
4. Caso contrário, a próxima release $N$ (em até 7 dias) é avaliada pela heurística: se $N$ é
   corretiva, $R$ **falhou**; senão, $R$ **não falhou**. O veredito depende só da tag e dos commits de $N$;
   os commits da própria $R$ não são usados.

Assim, `avaliadas = falhas + sem falha`, e, por repositório,
`avaliadas + censuradas + ignoradas = releases na janela`. O $\text{CFR}_b$ é nulo se `avaliadas = 0`.
Note-se que apenas a **próxima** release é examinada; releases seguintes dentro dos 7 dias não são
consideradas, e a "próxima" é sempre a seguinte na ordem de publicação entre as releases de C1 da
janela.

**Heurística `v1`** (`metricas/cfr_b.py::heuristic_v1`; é a única versão registrada, e a versão em uso
é escolhida em `cfr_b.heuristica` do `config.yaml`, com `v1` como padrão; o dataset **não** grava qual
versão foi usada, conforme `dados/README.md`, seção 2.1). A release $N$, com predecessora $R$, é
**corretiva** se as duas condições ocorrem juntas:

1. **só o número de *patch* aumenta** em relação a $R$ no Versionamento Semântico ([semver.org](https://semver.org/lang/pt-BR/))
   (por exemplo, `2.3.0 → 2.3.1`; `MAJOR` e `MINOR` iguais e `PATCH` maior, não necessariamente em +1).
   O padrão aceito é `MAJOR.MINOR[.PATCH]` no **final** da tag, com prefixo livre (`v`, `release-`,
   `pkg@`; o caractere anterior à versão não pode ser dígito nem ponto) e sufixo opcional (`-rc.1`,
   `+build`); `PATCH` ausente vale 0. O sufixo é ignorado na comparação (`2.3.0-rc.1 → 2.3.0` não é
   incremento de *patch*), e o nome do pacote não é comparado (em monorepos, `a@1.0.1` após `b@1.0.0`
   conta como incremento de *patch*); e
2. **ao menos um commit de $N$** tem, no assunto, uma das palavras `revert`/`reverts`/`reverted`,
   `hotfix`/`hot-fix`, `fix`/`fixes`/`fixed` ou `bugfix`, como palavra inteira e sem diferenciar
   maiúsculas de minúsculas (`fix(escopo):`, `bug fix` e `bug-fix` também valem; `fixing`, `reverting`,
   `hotfixes` e `fix_x` não valem).

Quando alguma das tags não segue esse padrão (por exemplo, `nightly`, `1.2.3.4` ou `v1.2.3_beta`), o
critério de versão é desconhecido e vale **só** o critério 2. Tags de calendário (CalVer, como
`2026.01.29`) casam com o padrão e são lidas como `MAJOR.MINOR.PATCH` (`2026.1.29`), de modo que o
"*patch*" passa a ser o dia do mês (ver 3.9).
A escolha do operador **E** (e não OU) se deve, segundo o relatório da Sprint 02, a que quase toda release
tem algum commit com "fix" e, com OU, quase tudo viraria "corretiva" (`docs/relatorio_sprint2_gabriel_assis.md`);
essa frequência é uma afirmação qualitativa do relatório e não foi medida neste repositório.

`[PENDENTE: versão final da heurística (v1 ou refinamentos v2, v3...) e o F1 de cada versão testada, que dependem da avaliação contra o consenso (#62), por sua vez dependente da rotulação (#57, #61, #64) e do consenso (#65). Hoje só a v1 existe.]`

### 3.7 Validação manual (amostra-ouro)

**Objetivo.** Estimar o quanto o proxy automático de release corretiva (CFR (b)) concorda com o
julgamento humano, e rotular o tipo do projeto (fator da RQ 06).

**Amostragem.** Foram sorteados **60 repositórios** das 330 linhas de `dados/repositorios.parquet`,
com `df.sample(n=60, random_state=42)`, e, para cada um, **5 releases** sorteadas entre as releases
publicadas da janela (C1, sem pré-releases), com semente determinística por repositório
(`42 × 1000 + índice`, em que o índice vai de 1 a 60 na ordem do sorteio dos repositórios). O desenho
prevê **300 linhas** (60 × 5). A lista dos 60 repositórios está em `dados/amostra_ouro/sorteio_info.json`
(gerado em 15/10/2026) e o código está em `analises/amostra_ouro.py`. Reexecutar o sorteio sobre o
`repositorios.parquet` e o `repositorios.csv` versionados reproduz exatamente os mesmos 60 repositórios.
`[VERIFICAR: o sorteio de releases só foi feito para 30 dos 60 repositórios. Para os outros 30, o arquivo dados/releases/ do repositório não existia no momento do sorteio (analises/amostra_ouro.py::carregar_releases_repositorio devolve lista vazia), então releases_sorteadas está vazia no sorteio_info.json e as 5 linhas de cada um (150 das 300) saíram na planilha com tag_name = "(pendente de persistência)" e sem data. Hoje só 150 releases reais estão identificadas. Antes de a rotulação seguir, é preciso persistir as releases desses 30 repositórios (analises.persistir_amostra_ouro) e gerar de novo as planilhas (analises.amostra_ouro), e as 150 linhas já rotuladas em validacao/rotulos_marcela.csv precisam ser refeitas, porque não apontam para uma release identificável.]`
`[VERIFICAR: o sorteio usou a ordem das linhas do dataset de 15/10/2026. Se o dataset for regenerado (#56) e a composição ou a ordem das 330 mudar, a lista de 60 repositórios pode deixar de pertencer à amostra final. O sorteio_info.json é o registro oficial dos 60.]`

**Rotulação independente.** Cada um dos três autores preenche, **sem consultar os demais e sem ver a
saída da heurística**, sua própria planilha (CSV/XLSX com *links* diretos para a página de cada
release no GitHub; `dados/amostra_ouro/amostra_ouro_<nome>.csv`), com:

| Dimensão | Categorias | Unidade de análise | N |
|---|---|---|---|
| `tipo_projeto` | biblioteca/framework, aplicação/serviço, ferramenta CLI, outro | repositório | 60 |
| `entrega_real` (as releases representam entregas reais ao usuário?) | sim, não, incerto | repositório | 60 |
| `release_corretiva` | sim, não | release | 300 |

`tipo_projeto` e `entrega_real` são julgamentos por repositório e aparecem repetidos nas 5 linhas
dele; para não inflar o kappa, cada repositório é contado **uma vez** nessas duas dimensões, e os
arquivos com valores diferentes entre as linhas do mesmo repositório são rejeitados pela ferramenta.

**Concordância entre avaliadores.** Para cada dimensão, calculamos o **kappa de Fleiss** (`[REF: Fleiss, 1971]`)
entre os 3 avaliadores com `statsmodels` (`aggregate_raters` com `n_cat` fixo, seguido de
`fleiss_kappa(..., method="fleiss")`):

$$P_i = \frac{\sum_j n_{ij}^2 - n}{n(n-1)}, \qquad \bar{P} = \frac{1}{N}\sum_i P_i, \qquad P_e = \sum_j p_j^2, \qquad \kappa = \frac{\bar{P} - P_e}{1 - P_e}$$

com $n = 3$ avaliadores, $n_{ij}$ o número de avaliadores que escolheram a categoria $j$ na unidade
$i$, e $p_j$ a proporção global da categoria $j$. Reportamos também a concordância unânime (%) como
apoio. Se todos os avaliadores escolhem sempre a mesma categoria, $P_e = 1$ e o kappa é indefinido;
a ferramenta o reporta como `n/d`, e isso será discutido. A interpretação segue Landis & Koch (1977):
< 0 pobre; 0,00-0,20 leve; 0,21-0,40 razoável; 0,41-0,60 moderada; 0,61-0,80 substancial; 0,81-1,00
quase perfeita (a ferramenta usa limites superiores inclusivos, por exemplo 0,40 é razoável). Um kappa baixo indica que o próprio critério é ambíguo, o que é um achado e será
discutido. O kappa é calculado **antes** da reunião de consenso e os arquivos de rótulos individuais
**não são editados depois**.

**Consenso e desempate** (`docs/protocolo_consenso.md`). (1) Vale a maioria simples (placares 3-0 e
2-1), preenchida pela ferramenta. (2) `release_corretiva`, com apenas duas categorias, sempre tem
maioria. (3) Os empates 1-1-1 (possíveis em `tipo_projeto` e `entrega_real`) são decididos **em
reunião** com os três presentes, a partir do critério do guia. (4) Se, após a discussão, os três
mantiverem rótulos distintos, aplica-se o desempate final: `tipo_projeto = outro` e `entrega_real =
incerto`. (5) `incerto` é uma categoria como as demais (entra no kappa e na maioria) e **não é
forçado** para `sim` ou `não`. (6) A reunião pode rever casos 2-1 se o dissidente apontar erro de
leitura do critério. O arquivo `validacao/consenso.csv` registra, para cada rótulo, a origem
(`unanimidade`, `maioria` ou `reuniao`).

**Avaliação da heurística** (`docs/avaliacao_heuristica.md`, `analises/avaliar_heuristica.py`). Para
cada release do consenso, aplica-se a heurística (com a release anterior e os commits persistidos) e
compara-se com o rótulo `release_corretiva` de consenso, tomando `sim` como classe positiva:

$$\text{Precisão} = \frac{VP}{VP+FP}, \qquad \text{Recall} = \frac{VP}{VP+FN}, \qquad F_1 = \frac{2PR}{P+R}$$

calculados com `sklearn.metrics.precision_recall_fscore_support`, junto com a matriz de confusão. Se
um denominador é zero, a métrica é reportada como indefinida (`n/d`), e não como 0. Releases que não
podem ser avaliadas (repositório sem arquivo de releases, tag ausente, `status ≠ ok` ou sem release
anterior) são **excluídas, contadas e discriminadas por motivo**, e o conjunto avaliado é o mesmo para
todas as versões da heurística. A **meta é F1 ≥ 0,70**. Se nenhuma versão atingir a meta, analisa-se
a lista de falsos positivos e negativos, propõe-se uma nova versão (sem apagar as anteriores),
justificada por uma **regra geral** e não por um caso isolado (para limitar o ajuste excessivo às 300
releases), e reavalia-se. **Cada versão testada, mesmo as que falharam, e o seu F1 entram no artigo.**

**Estado atual da validação manual** (verificado nesta data no repositório):

* o sorteio e as planilhas em branco existem (`dados/amostra_ouro/`; Issue #63), mas só 30 dos 60
  repositórios têm as 5 releases identificadas (ver o `[VERIFICAR]` em "Amostragem");
* **apenas um** dos três arquivos de rótulos existe: `validacao/rotulos_marcela.csv`, que passa na
  validação de formato da ferramenta (300 linhas válidas; essa validação compara `repo_name` e
  `tag_name` com a planilha e, por isso, não detecta que 150 linhas têm `tag_name` pendente);
* **não existem** `validacao/rotulos_joao.csv`, `validacao/rotulos_gabriel.csv` nem
  `validacao/consenso.csv`. Rodar `python -m analises.concordancia kappa` termina com código 2,
  informando os arquivos ausentes.

Portanto, **a rotulação manual pelos três autores ainda não foi concluída**, e o texto final não pode
afirmar o contrário até que os arquivos existam.

`[PENDENTE: rotulação independente de João (#57) e Gabriel (#61).]`
`[PENDENTE: kappa de Fleiss em cada dimensão (tipo_projeto, entrega_real, release_corretiva), com interpretação de Landis & Koch (#65).]`
`[PENDENTE: reunião de consenso e commit de validacao/consenso.csv (#65); data, relator e número de casos por origem (unanimidade, maioria, reunião).]`
`[PENDENTE: precisão, recall e F1 da heurística por versão, matriz de confusão, número e motivos de releases excluídas, versão final e justificativa (#62); executar a persistência de releases da amostra-ouro com analises.persistir_amostra_ouro, que exige GITHUB_TOKEN e rede.]`

### 3.8 Análise estatística planejada

Esta subseção descreve o plano do guia. **Nenhum script das RQ 05, 06 e 07 existe ainda no
repositório** (a pasta `analises/` tem apenas amostra-ouro, concordância, avaliação da heurística,
diagnóstico de lead time e persistência das releases da amostra-ouro; uma busca por `spearmanr`,
`kruskal`, `mannwhitneyu`, `multipletests` e `cohen_kappa` no código Python não encontra nada), e
nenhum resultado é reportado.
`[PENDENTE: scripts e resultados das RQ 01 a 07 (Sprint 03); não há issue aberta para isso até a #69.]`

* **Estatística descritiva (RQ 01 a 04).** Mediana e IQR de cada métrica entre os repositórios,
  distribuição das faixas DORA e da classificação geral. Para o tempo de recuperação, também a
  proporção de episódios censurados.
* **RQ 05.** Correlação de Spearman ($\rho$) entre frequência de deploy e CFR, **separadamente** para
  CFR (a) e CFR (b), reportando $\rho$, p-valor e $n$ (`[REF: Spearman]`). Spearman foi escolhida por
  não exigir normalidade nem relação linear (mede associação monotônica, a partir dos postos). O $n$
  pode diferir entre as duas variantes, porque o CFR (b) é nulo quando nenhuma release do repositório
  pôde ser avaliada (3.6). Correlação não implica causalidade.
* **RQ 06.** Comparação das métricas das RQ 01 a 04 entre subgrupos definidos por **no mínimo três
  fatores** entre: linguagem principal, popularidade (quartis de estrelas), número de contribuidores
  (quartis), idade do repositório (quartis) e tipo do projeto. Teste de Kruskal-Wallis para fatores
  com 3 ou mais grupos e de Mann-Whitney para 2 grupos (`[REF: Kruskal e Wallis, 1952; Mann e Whitney, 1947]`).
  Os p-valores são corrigidos para comparações múltiplas pelo método de Holm
  (`statsmodels.stats.multitest.multipletests`, `method='holm'`; `[REF: Holm, 1979]`). Tamanho de
  efeito: $\varepsilon^2 = H/(n-1)$ para Kruskal-Wallis, e $\delta = 2U_1/(n_1 n_2) - 1$ (Cliff's
  delta) para dois grupos, interpretado por |δ| < 0,147 desprezível, < 0,33 pequeno, < 0,474 médio e
  ≥ 0,474 grande (Romano et al., 2006).
  `[PENDENTE: fatores efetivamente usados. Decisão aberta na Issue #69, ver abaixo.]`
  `[VERIFICAR: o guia descreve o tipo do projeto com três grupos (biblioteca/framework, aplicação/serviço, ferramenta CLI), mas a rotulação da amostra-ouro admite também "outro". Definir se "outro" vira um quarto grupo ou é excluído da RQ 06.]`
* **RQ 07.** Para cada combinação C1, C2 e C3 (3.5.6), classifica-se cada repositório em
  Elite/High/Medium/Low (3.5.5; ver o `[VERIFICAR]` sobre o CFR (b) de C2 em 3.5.6). Para cada par (C1×C2, C1×C3, C2×C3) calcula-se a **porcentagem de
  repositórios que mudaram de categoria** e o **kappa de Cohen ponderado linear**
  (`sklearn.metrics.cohen_kappa_score(..., weights='linear')`; `[REF: Cohen, 1968]`), que pesa menos
  uma troca entre categorias vizinhas do que uma troca entre extremos, por serem ordinais.

**Decisão aberta: fator "tipo do projeto" na RQ 06 (Issue #69, aberta).** O tipo do projeto só é rotulado nos
60 repositórios da amostra-ouro. Se ele for um dos fatores da RQ 06, essa análise terá $n = 60$,
contra até $n = 330$ nos demais fatores (o $n$ de cada teste ainda varia com os valores nulos de cada
métrica). As opções registradas na issue são: **(a)** não usar o tipo; **(b)** rotular o tipo nos
330 repositórios (uma dimensão só, o que é mais rápido que a rotulação completa, mas aumenta a carga
de rotulação da sprint); ou **(c)** usar com $n = 60$ e registrar como ameaça à validade. A decisão
e a justificativa ainda não foram tomadas.
`[PENDENTE: decisão (a), (b) ou (c) da Issue #69 e sua justificativa. Se for (a), ajustar a hipótese 4 da RQ 06 na Introdução (artigo_contexto_e_hipoteses.md), que hoje prevê um efeito do tipo de projeto.]`

### 3.9 Ameaças à validade e limitações conhecidas

Organizadas nas quatro categorias de Wohlin et al. (2012). Os itens com números vêm dos artefatos
versionados; o que depende de resultados futuros está marcado.

**Validade de construto: estamos medindo o que achamos que medimos?**

* **Release não é deploy.** Uma biblioteca que publica uma release por mês não "implanta" nada em
  produção; os usuários é que o fazem. A frequência de deploy mede cadência de publicação.
* **Falha de CI não é falha em produção.** O CFR (a) mede falhas do pipeline no default branch; o
  CFR (b) só captura falhas que motivam uma nova release corretiva em até 7 dias. As duas
  variantes medem coisas diferentes.
* **A heurística de release corretiva pode errar.** Ela usa só a mudança de *patch* e palavras no
  **assunto** do commit (o corpo da mensagem não é coletado). Releases corretivas que mudam o *minor*
  e correções sem palavra-chave escapam (falsos negativos). Palavras como "fix" em manutenção rotineira
  e tags fora de SemVer, que são julgadas só pelas palavras, podem gerar falsos positivos. Tags de
  calendário (CalVer, como `2026.01.29` em `yt-dlp/yt-dlp`) são lidas como SemVer, e o "*patch*"
  vira o dia do mês, o que distorce o critério 1. `[PENDENTE: precisão, recall e F1 reais (#62).]`
* **Só a próxima release é examinada** no CFR (b). Quem publica muitas releases em menos de 7 dias
  tem, em princípio, mais chance de aparecer como "falha", o que poderia gerar correlação espúria na
  RQ 05 (hipótese, ainda não testada).
* **Data do autor.** `commit.author.date` pode ser distorcida por *rebase* e *squash merge* (aviso do
  guia), e valores posteriores à release são truncados em 0.
* **Predecessora de outra linha de manutenção.** A release anterior é a cronologicamente anterior
  (definição comum da turma, necessária para a replicação), mas em projetos com várias linhas de
  manutenção ela pode estar em outra linha (por exemplo, `v19.0.1` comparada com `v19.2.0` no
  `react/react`), e o `git log` entre linhas diferentes conta commits que a release não "entregou".
  Como indicador (limite superior), **2.649 releases em 120 repositórios** têm predecessora com SemVer
  maior. Em monorepos, tags de pacotes diferentes também contam. Uma variante "por linha" pode entrar
  na análise de sensibilidade (`docs/investigacao_lead_time.md`, seção 5).
* **Monorepos com várias releases por commit.** No `expo/expo`, 145 das 146 releases da janela não têm
  commits novos em relação à anterior (a restante tem tag não encontrada); por isso é o único
  repositório sem lead time depois da correção do clone.
* **Tags (C3).** São todas as tags do repositório, o que pode incluir tags que não são entregas. Além
  disso, a data de uma tag é a data do autor do commit apontado, e não a de criação da tag, de modo que
  o lead time de C3 mede o intervalo entre commits e o commit etiquetado.
* **Motivos de valores nulos.** Um valor nulo nunca é imputado; o que muda é o tratamento na classificação.
  * `lead_time_a_hours`/`lead_time_b_hours`: nenhuma release da janela pôde ser avaliada (todas
    `first_release`, `not_found` ou sem commits novos). No `repositorios.csv` versionado há 61 nulos (59 por
    tag não encontrada em todas as releases, 1 por tag não encontrada somada a releases sem commits novos e
    1 por primeira release somada a tag não encontrada; `docs/investigacao_lead_time.md`, seção 3.1);
    depois da correção do clone resta 1 (`expo/expo`).
  * `recovery_hours`: nenhum episódio de falha foi resolvido. No `repositorios.csv` versionado há 18
    nulos: 15 repositórios sem nenhum episódio de falha (todos com `cfr_a = 0`) e 3 com apenas episódios
    censurados (`censored_episodes_ratio = 1`). Entre os 330, 151 têm ao menos um episódio censurado.
  * `cfr_a`: nulo só sem nenhum run válido, o que o critério de ≥ 50 runs válidos impede; nenhum nulo no
    `repositorios.csv` versionado.
  * `cfr_b`: nulo quando `cfr_b_evaluated_releases = 0` (todas as releases da janela censuradas ou
    ignoradas). `[PENDENTE: contar os nulos de cfr_b depois da regeneração do dataset (#56); o repositorios.csv versionado não tem as colunas cfr_b*.]`
  * Os nulos de lead time, CFR (a) e recuperação viram **Low** na classificação (3.5.5), e os de
    `cfr_b` ficam sem faixa. `[VERIFICAR: ver 3.5.5.]`
* **Releases e janela.** Releases publicadas em 30/09/2026 depois de 00:00 UTC ficam fora da janela
  (3.2).

**Validade interna: há fatores não controlados?**

* Repositórios mais antigos ou maiores têm, em geral, mais releases e runs, o que pode confundir
  as associações da RQ 06 (exemplo do guia). Sem controle estatístico de covariáveis, as associações
  são descritivas.
* A coleta foi feita em momento único; a Search API e as contagens mudam no tempo, e a amostra regenerada
  pode diferir (`dados/README.md`, seção 7).
* **Possível truncamento de *workflow runs*.** Mesmo com a divisão adaptativa (profundidade máxima 3),
  um intervalo ainda com `total_count ≥ 1.000` é lido só até 10 páginas (1.000 runs), e o dataset não
  traz coluna indicando que isso ocorreu. `[VERIFICAR: medir em quantos repositórios isso aconteceu; o resultado da divisão (bisection_events) não é persistido.]`
* **A correção do clone mudou os resultados.** Antes de buscar todas as tags, 5.289 das releases da
  janela (20,6%) eram descartadas como `not_found` (`--single-branch` trazia só as tags alcançáveis a
  partir do default branch, e não as de ramos de manutenção); depois da correção, resta **1**. O lead time passou de 269 para 329 repositórios com valor,
  a mediana de (a) foi de 6,91 para 10,35 dias e a de (b), de 6,07 para 11,97 dias; 23 dos 269 repositórios
  que já tinham valor mudaram de faixa de lead time. Isso mostra a sensibilidade das métricas à
  coleta. `[PENDENTE: o repositorios.csv/.parquet versionado ainda é anterior a essa correção (61 repositórios com lead time nulo no CSV; 1 depois da correção). Regerar o dataset (#56) antes de reportar qualquer valor de lead time.]`
* **Diferença REST × Git.** A coleta via clone usa só o assunto do commit; a implementação via
  `compare` guardaria a mensagem completa.

**Validade externa: os resultados valem além da amostra?**

* A amostra contém apenas projetos **muito populares** (mínimo de 38.855 estrelas), open-source, que
  usam GitHub Actions e têm ao menos 5 releases e 50 runs na janela. Isso exclui projetos pequenos,
  corporativos/fechados e os que usam outras plataformas de CI; há viés de sobrevivência para projetos
  que publicam releases no GitHub.
* A janela é única (12 meses) e a distribuição de linguagens é concentrada (TypeScript, Python, Go,
  Rust e JavaScript somam 268 dos 330 repositórios).
* A amostra-ouro tem 60 repositórios e 300 releases, o que limita a generalização do F1 da heurística.

**Validade de conclusão: a análise estatística é adequada?**

* **Comparações múltiplas** (RQ 06: ≥ 3 fatores × 4 métricas = ≥ 12 testes) tratadas com Holm; os
  tamanhos de efeito acompanham os p-valores.
* **Subgrupos pequenos.** Alguns grupos (linguagens raras, tipo do projeto com $n = 60$ se a opção (c)
  for adotada) têm poucos repositórios. `[PENDENTE: tamanhos de grupo reais e decisão da Issue #69.]`
* **Dependência entre observações.** As 5 releases sorteadas de cada repositório não são
  independentes entre si, e o kappa e o F1 as tratam como observações separadas; o efeito de
  agrupamento não é corrigido.
* **Ajuste da heurística à própria amostra-ouro.** As mesmas 300 releases guiam o refinamento e medem o F1;
  a regra de "mudança justificada por regra geral" mitiga, mas não elimina, o ajuste excessivo.
  `[PENDENTE: avaliar se parte dos repositórios será reservada para a avaliação final (opção prevista em docs/avaliacao_heuristica.md).]`
* **Kappa sem variabilidade.** Se as categorias quase não variam (por exemplo, quase todo repositório
  com `entrega_real = sim`), o kappa fica instável ou indefinido, mesmo com alta concordância
  percentual. `[PENDENTE: kappas reais (#65).]`
* **Censura.** O CFR (b) deixa de fora as releases dos últimos 7 dias da janela, e o tempo de
  recuperação usa só os episódios resolvidos na mediana; como o guia alerta, ignorar os censurados faz
  os repositórios parecerem mais rápidos para se recuperar. A proporção de censurados é reportada por
  repositório (`censored_episodes_ratio`). `[PENDENTE: proporções reais de censura e, se o grupo quiser, uma análise de sensibilidade que trate os censurados (RQ 04).]`
* **Releases fora do lead time (tag não encontrada, primeira release, sem commits novos).** Contadas e
  reportadas: depois da correção,
  das 25.732 releases da janela, 21.835 têm commits novos, 3.835 não têm commits novos, 61 são a
  primeira release da história do repositório e **1** tem tag não encontrada
  (`dados/analises/lead_time_diagnostico.csv`).
  O mesmo diagnóstico não prova a ausência de outros efeitos de coleta.

### 3.10 Reprodutibilidade e disponibilidade

O pipeline (código, `config.yaml`, testes e documentação) e os dados (`dados/repositorios.csv` e
`.parquet`, `funil.csv`, `runs/`, `analises/`, `amostra_ouro/`) estão versionados no repositório do
grupo. `dados/releases/` e `dados/releases_c2/` (cerca de 320 MB; um arquivo passa de 100 MB) **não**
são versionados e são regenerados em cerca de 10 minutos por
`uv run python -m pipeline.persist_releases --config config.yaml`. O dicionário de dados completo está
em `lab03/dados/README.md`. `dados/tags/` também é gerado pelo pipeline, mas não consta entre os
arquivos versionados hoje. A replicação cruzada é relatada em seção própria.
`[PENDENTE: link final do repositório e do GitHub Projects no artigo; link do Overleaf (#48).]`

---

## Apêndice A. Lista de pendências para fechar a seção

| # | Pendência | Onde entra | Fonte / responsável |
|---|---|---|---|
| 1 | Corrigir ou explicar o funil (653 → 230, mas 330 finais) | 3.3, Tabela 2 | `dados/funil.csv`; Marcela (#31/#66) |
| 2 | Confirmar janela oficial e o limite de 30/09 | 3.2 | professor; `config.yaml` |
| 3 | Data(s) da coleta e regeneração do dataset | 3.2, 3.9 | João (#56) |
| 4 | Regerar `repositorios.*` (colunas novas, lead time corrigido) e reconferir a caracterização da amostra | 3.3, 3.9 | João (#56) |
| 5 | Rótulos de João e Gabriel | 3.7 | #57, #61 |
| 6 | Kappa de Fleiss real (3 dimensões) | 3.7 | #65 |
| 7 | Consenso (`validacao/consenso.csv`), reunião, relator e data | 3.7 | #65 |
| 8 | Precisão, recall e F1 por versão da heurística; versão final | 3.6, 3.7 | #62 |
| 9 | Decisão do fator "tipo do projeto" na RQ 06 | 3.8, 3.9 | #69 |
| 10 | Tratamento de valores nulos na classificação DORA | 3.5.5 | grupo |
| 11 | CFR (b) em C2 sobre C2 ou C1 | 3.5.6 | grupo (Sprint 03) |
| 12 | Scripts e resultados das RQ 01 a 07 | 3.8 | Sprint 03 |
| 13 | RQ 08 (bônus): fazer ou não | 3.1 | grupo |
| 14 | Quantos repositórios sofreram truncamento de runs | 3.9 | João |
| 15 | Citações `[REF: ...]` marcadas no texto | todo o texto | autores |
| 16 | Link do Overleaf e do repositório no artigo | 3.10 | #48 |

## Apêndice B. Afirmação → arquivo de origem

Todos os caminhos são relativos a `lab03/`, salvo indicação.

| Afirmação | Arquivo |
|---|---|
| Janela 01/10/2025-30/09/2026; `tamanho_final` 330; mín. 5 releases e 50 runs; faixas de estrelas; qualificadores de busca; heurística `v1` | `config.yaml` |
| 52,1 semanas; faixas de DF, lead time, CFR e recuperação; nota geral = mediana arredondada para baixo | `metricas/dora.py` |
| Lead time (a) e (b); truncamento em 0; release sem commits e releases ignoradas | `metricas/lead_time.py` |
| CFR (a); classificação de `conclusion`; episódios, recuperação e censura | `metricas/stability.py` |
| CFR (b): horizonte de 7 dias; censurada, ignorada, sem falha, falha; heurística `v1`; regex de SemVer e palavras-chave; `HEURISTICS` | `metricas/cfr_b.py` |
| Datas convertidas para UTC; `"2026-09-30"` lido como meia-noite UTC | `metricas/schemas.py` |
| Busca fatiada por estrelas; deduplicação; máximo de 10 páginas por faixa | `pipeline/repo_selector.py` |
| Filtros na ordem Actions, releases, runs, clone; avaliação em ordem de estrelas; parada ao atingir a meta; classificação C1/C2/C3; colunas do registro | `pipeline/orchestrator.py` |
| Estrutura das linhas do funil | `pipeline/funnel.py`; `dados/funil.csv` |
| Etapas do funil, critério dos 330 e ressalva da primeira linha | `docs/criterios_selecao_e_funil.md` |
| Contagens do funil (653, 597, 282, 232, 230, 330) | `dados/funil.csv` |
| Caracterização da amostra (estrelas, linguagens, releases, runs, datas) | `dados/repositorios.csv` |
| Consulta GraphQL (campos coletados, ordenação, paginação) | `pipeline/graphql/queries/repo_details.graphql`; `pipeline/releases.py` |
| Contagem de contribuidores por cabeçalho `Link` | `pipeline/metadata.py` |
| Coleta de runs: filtros, divisão mensal, divisão adaptativa (teto 1.000, profundidade 3, 2 dias), deduplicação por `id` | `pipeline/workflow_runs.py` |
| Clone *bare* e *blobless*, `fetch` de todas as tags, fallback com token, `git log` com `%aI` e `%s`, `for-each-ref` das tags | `pipeline/git_clone.py` |
| Alternativa via REST `compare` (paginação, 404, status `ok`/`first_release`/`not_found`) | `pipeline/commits.py` |
| Âncora, janela, pré-releases, descarte de rascunhos | `pipeline/releases.py` |
| Rate limit, rotação de tokens, *backoff* exponencial, concorrência | `pipeline/http_client.py` |
| Cache SQLite em modo WAL | `pipeline/cache.py` |
| Retomada, checkpoint incremental, comando único, `--limit`, `--clean` | `README.md`; `pipeline/__main__.py`; `pipeline/orchestrator.py` |
| Dicionário de dados, colunas `cfr_b*`, regras de C1/C2/C3, regeneração do dataset, CSV versionado anterior às colunas novas | `dados/README.md` |
| Motivos de lead time nulo; 5.289 → 1 `not_found`; medianas antes e depois; LT(b) > LT(a); predecessora de outra linha (2.649 releases, 120 repositórios); `expo/expo` | `docs/investigacao_lead_time.md`; `dados/analises/lead_time_diagnostico.csv` |
| Decisão pelo operador E na heurística; contexto da Sprint 02 | `docs/relatorio_sprint2_gabriel_assis.md` |
| Sorteio de 60 repositórios (semente 42) e 5 releases por repositório; 300 linhas; lista de repositórios | `analises/amostra_ouro.py`; `dados/amostra_ouro/sorteio_info.json` |
| Dimensões, unidades de análise, kappa de Fleiss, Landis & Koch, consenso e desempate, formato dos arquivos | `docs/protocolo_consenso.md`; `analises/concordancia.py` |
| Precisão/recall/F1, exclusões, meta F1 ≥ 0,70, regra de decisão e versões | `docs/avaliacao_heuristica.md`; `analises/avaliar_heuristica.py` |
| Só `rotulos_marcela.csv` existe; faltam `rotulos_joao.csv`, `rotulos_gabriel.csv` e `consenso.csv` | `validacao/` (listagem); `docs/protocolo_consenso.md` (seção 6) |
| Plano estatístico (Spearman, Kruskal-Wallis, Mann-Whitney, Holm, ε², Cliff's δ, κ ponderado), definições operacionais, validação manual | `guialab03.md` |
| Opções (a), (b) e (c) para o fator "tipo do projeto" | Issue #69 (GitHub) |
| Divisão da escrita da metodologia | Issue #68 (GitHub) |
| Hipóteses informais por RQ | `artigo_contexto_e_hipoteses.md`; `docs/hipoteses_rq02_rq03_rq05.md`; `docs/hipoteses_rq04_rq07.md` |
| CI do grupo e cobertura mínima de 80% | `../.github/workflows/testes-lab03.yml`; `README.md` |

## Apêndice C. Referências já citadas nos documentos do repositório

Apenas estas obras aparecem em `guialab03.md`; as demais citações do texto estão como `[REF: ...]`.

* Forsgren, N.; Humble, J.; Kim, G. *Accelerate: The Science of Lean Software and DevOps*. IT Revolution, 2018.
* DORA. Relatórios *Accelerate State of DevOps* (<https://dora.dev/research/>) e guia das métricas (<https://dora.dev/guides/dora-metrics-four-keys/>).
* Wohlin, C. et al. *Experimentation in Software Engineering*. Springer, 2012.
* Romano, J. et al. *Appropriate statistics for ordinal level data*. 2006.
* Landis, J. R.; Koch, G. G. The measurement of observer agreement for categorical data. *Biometrics*, 1977.
* Versionamento Semântico: <https://semver.org/lang/pt-BR/>.

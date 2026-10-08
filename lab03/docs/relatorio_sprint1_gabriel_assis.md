# Relatório individual — Lab03S01

**Integrante:** Gabriel Assis de Souza (@GabriAssiss)
**Sprint:** Lab03S01 — pipeline de coleta base, testes e hipóteses
**Papel na divisão sugerida do guia:** integrante **B** (coleta de releases/tags e
de commits entre releases, mais as funções e testes de lead time)

## 1. Escopo

| Issue | Título | Artefato |
|---|---|---|
| #41 | Coletar releases e tags | `pipeline/releases.py`, `tests/test_releases.py` |
| #42 | Coletar commits entre releases | `pipeline/commits.py`, `tests/test_commits.py` |
| #43 | Lead time (a) e (b) (funções + testes) | `metricas/lead_time.py`, `tests/test_lead_time.py` |
| #44 | Hipóteses RQ02, RQ03 e RQ05 | `docs/hipoteses_rq02_rq03_rq05.md` |

A Issue #45 (consolidar a introdução no artigo) está atribuída aos três
integrantes e será feita em grupo, por isso não faz parte deste relatório.

Todo o código usa a infraestrutura já entregue pelo João Pedro: o cliente REST
`GitHubClient` (#35), com paginação pelo cabeçalho `Link`, tratamento de rate
limit e backoff exponencial, e o cache em SQLite (#46), que permite retomar a
coleta sem repetir requisições. Também reaproveita os dataclasses `Release` e
`Commit` de `metricas/schemas.py`, sem alterá-los.

## 2. #41 — Coleta de releases e tags (`pipeline/releases.py`)

### 2.1 Releases

- `parse_release(payload)` converte o JSON da API em `Release`, guardando
  `tag_name`, `published_at`, `draft` e `prerelease`. **Drafts são
  descartados**, pois não são deploys e não têm `published_at`.
- `fetch_releases(client, owner, repo, window_start)` pagina
  `GET /repos/{owner}/{repo}/releases?per_page=100`.
  - A API lista as releases da mais nova para a mais antiga. Quando
    `window_start` é informado, a paginação **para depois da página que contém a
    primeira release estável publicada antes da janela**. Essa release é a
    *âncora*: é contra ela que se calcula o lead time da primeira release da
    janela. Releases mais antigas que a âncora não são necessárias, o que poupa
    cota da API em repositórios com histórico longo.
  - Sem `window_start`, o histórico inteiro é baixado.
  - O retorno é ordenado da mais antiga para a mais nova.

### 2.2 Janela de observação e unidade de deploy

- `deploy_units(releases, include_prerelease=False)` aplica a definição de
  deploy: na definição principal, só releases publicadas; na variante da RQ 07
  (combinação C2), releases **e** pré-releases.
- `filter_window(releases, start, end, include_prerelease=False)` devolve um
  `WindowReleases` com:
  - `in_window`: as unidades de deploy publicadas em `[start, end]` (limites
    inclusivos);
  - `anchor`: a última unidade publicada antes da janela, ou `None` se não
    existir (nesse caso, a primeira release da janela é a primeira da história
    do repositório);
  - `count`: número de deploys válidos na janela;
  - `with_anchor()`: âncora seguida das releases da janela, pronta para a
    comparação entre releases consecutivas.
- `count_valid_releases(releases, start, end)` conta as releases válidas
  (publicadas, não pré-release, dentro da janela) e alimenta o critério mínimo
  de inclusão (≥ 5 releases) do funil de seleção.

### 2.3 Tags (variante da RQ 07)

- `fetch_tags(client, owner, repo, max_tags=None)` pagina
  `GET /repos/{owner}/{repo}/tags`. Como tags não têm data, cada uma é datada
  pelo `commit.author.date` do commit para o qual aponta, obtido em
  `GET /repos/{owner}/{repo}/commits/{sha}`.
  - Tags que apontam para o **mesmo commit** geram uma única requisição.
  - As tags são devolvidas como objetos `Release`, para que as mesmas funções de
    janela e de lead time sirvam para a combinação C3 da RQ 07.
  - O parâmetro `max_tags` limita o custo em repositórios com milhares de tags,
    já que cada commit distinto custa uma requisição (que fica no cache).

## 3. #42 — Coleta de commits entre releases (`pipeline/commits.py`)

- `fetch_compare_commits(client, owner, repo, base, head)` chama
  `GET /repos/{owner}/{repo}/compare/{base}...{head}` com `per_page=100` e
  `page=1, 2, …`. Sem paginação, esse endpoint devolve no máximo 250 commits.
  - Para quando a página vem vazia ou incompleta, ou quando o número coletado
    atinge `total_commits`. Se faltar algum commit, registra um aviso no log.
  - Os nomes das tags são codificados na URL (ex.: `v1.0+b1` → `v1.0%2Bb1`),
    preservando `/` para tags como `pkg/v1.0`.
- `parse_commit(payload)` guarda `sha`, `commit.author.date` (data do commit
  conforme a definição operacional do guia) e a **mensagem**, que será usada na
  heurística de release corretiva do CFR (b) na S02.
- `collect_release_commits(client, owner, repo, window)` compara cada release
  da janela com a anterior (a primeira, com a âncora) e devolve uma lista de
  `ReleaseCommits` com `release`, `previous`, `commits` e `status`:
  - `OK`: comparação feita (a lista pode estar vazia, caso de release sem
    commits novos);
  - `FIRST_RELEASE`: primeira release da história, sem anterior. É pulada sem
    chamar a API;
  - `NOT_FOUND`: o `compare` devolveu 404 (tag apagada ou reescrita). O caso é
    registrado no log e a release é pulada, como manda a seção 11 do guia.
    Outros erros HTTP (ex.: 401) continuam sendo lançados.
- `ReleaseCommits.commits_or_none` devolve `None` para releases puladas, que é
  o formato esperado pela função de lead time.
- `count_by_status(results)` conta quantas releases ficaram em cada status, por
  exemplo quantas foram puladas por 404, para reportar no artigo.

## 4. #43 — Lead time (a) e (b) (`metricas/lead_time.py`)

Implementa a RQ 02 conforme a seção 5 do guia. Os valores são em **horas**,
seguindo o padrão de `metricas/stability.py`.

- `release_lead_time(release, commits)` — **variante (a)**: data de R menos a
  data do commit mais antigo incluído em R. Devolve `None` se a release não tem
  commits novos.
- `commit_lead_times(release, commits)` — **variante (b)**: data de R menos a
  data de cada commit incluído em R.
- `calculate_lead_time(pares)` recebe pares `(release, commits)` e devolve um
  `LeadTimeResult` com:
  - `median_a_hours`: mediana, entre as releases, do lead time por release;
  - `median_b_hours`: mediana de **todos** os commits de **todas** as releases;
  - as listas de valores individuais, para análises posteriores (IQR, gráficos);
  - `evaluated_releases`, `releases_without_commits` e `skipped_releases`.

Decisões tomadas:

| Situação | Tratamento | Motivo |
|---|---|---|
| `commits = None` (primeira release ou 404) | Ignorada e contada em `skipped_releases` | Guia, RQ 02 e seção 11 |
| Lista de commits vazia | Fica fora das duas variantes e é contada em `releases_without_commits` | Não existe "commit mais antigo" para a variante (a) |
| Commit com data posterior à da release | Lead time 0 | Datas de autor podem ser distorcidas por rebase ou relógio errado; mesmo critério do tempo de recuperação em `stability.py` |
| Datas em fusos diferentes | Comparadas como instantes absolutos | Todas as datas são convertidas para *timezone-aware* em `schemas.py` |

## 5. #44 — Hipóteses RQ 02, RQ 03 e RQ 05 (`docs/hipoteses_rq02_rq03_rq05.md`)

Rascunho em português para a Introdução do artigo, escrito antes de qualquer
coleta de dados, como exige o guia. Resumo:

- **RQ 02:** lead time (b) na faixa Medium; (a) bem maior que (b), muitas vezes
  Low, por causa de commits "esquecidos" e *backports*.
- **RQ 03:** CFR (a) na faixa High, puxado por *flaky tests*; CFR (b) na faixa
  Elite, porque releases corretivas em até 7 dias são raras. Baixa correlação
  entre as duas variantes.
- **RQ 05:** sem *trade-off* (ρ fraco, negativo ou próximo de zero) para o CFR
  (b) e correlação fraca e positiva para o CFR (a). Discute também o viés de
  repositórios com muitas releases terem mais chance de duas releases em menos
  de 7 dias.

O texto ainda precisa ser colado no Overleaf, que será consolidado na #45.

## 6. Testes

Três arquivos novos, com 28 testes que usam *fixtures* e `httpx.MockTransport`,
sem chamar a API real:

- `tests/test_lead_time.py` (10 testes): exemplo da `v1.1` do guia
  ((a) = 13 dias; (b) = 13, 5 e 1 dias), medianas entre duas releases, commit
  antigo "esquecido" inflando (a) mas não (b), release sem commits novos,
  release única, release pulada por 404, repositório sem releases, commit datado
  após a release e fusos horários diferentes.
- `tests/test_releases.py` (11 testes): descarte de drafts, definição principal
  e variante com pré-releases, âncora da janela, ausência de âncora, limites
  inclusivos da janela, contagem de releases válidas, parada da paginação depois
  da âncora, histórico completo, datação de tags pelo commit e `max_tags`.
- `tests/test_commits.py` (7 testes): paginação com 320 commits (4 páginas),
  mensagem e data do autor, codificação de tags com caracteres especiais,
  parada em página incompleta, uso da âncora com 404 e release sem commits,
  primeira release sem requisição e propagação de erros diferentes de 404. Um
  dos testes integra a coleta com `calculate_lead_time`.

Resultado da suíte completa (`uv run pytest --cov=metricas --cov=pipeline`):

```
65 passed
metricas/lead_time.py   100%
pipeline/releases.py    100%
pipeline/commits.py      98%
TOTAL (metricas)         99%   (CI exige ≥ 80%)
```

## 7. Validação contra a API real

Além dos testes, as funções foram executadas contra a API real do GitHub, sem
cache:

- `psf/requests`, janela de 2024: coletou 19 releases, encontrou a âncora
  `v2.31.0` (maio de 2023) e 4 releases na janela; as 4 comparações retornaram
  `OK` com 128, 1, 4 e 6 commits.
- `compare/v2.25.0...v2.32.0` no mesmo repositório: 290 commits coletados, todos
  distintos, igual ao `total_commits` da API. Isso confirma que a paginação
  passa do limite de 250.

## 8. Pendências e integração

- A integração ao comando único do pipeline e a execução com 100 repositórios
  são da Issue #39 (João). Para isso, as funções recebem a janela como
  parâmetro, já que o `config.yaml` da #28 ainda não existe.
- Fluxo sugerido por repositório:
  `fetch_releases` → `filter_window` → `count_valid_releases` (funil) →
  `collect_release_commits` → `calculate_lead_time`.
- As mensagens de commit já são guardadas para a heurística de release corretiva
  do CFR (b), que é a tarefa do integrante B na S02.
- Ameaça à validade a registrar: `commit.author.date` pode ser distorcido por
  rebases e *squash merges*.

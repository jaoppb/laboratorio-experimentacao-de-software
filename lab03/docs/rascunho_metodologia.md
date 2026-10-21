# Rascunho da seção de Metodologia (Issue #68)

> **Estado:** rascunho em Markdown para colar e adaptar no Overleaf (template SBC). O texto final do
> artigo **não** vive neste repositório; este arquivo existe para que os números e as definições
> citados batam com o que o código e os CSVs versionados realmente fazem.
>
> **Edição automatizada (21/10/2026), pendente de leitura pelos autores.** Esta versão aplica ao
> rascunho as decisões do grupo de 20/10/2026 (janela de observação, regra de valores nulos, CFR (b)
> na combinação C2, divisão dos *workflow runs*, filtro do clone e mensagens completas, funil,
> rotulação do tipo de projeto por agentes, validação manual com avaliador LLM e política da
> heurística) e troca os marcadores de referência (`[REF]`) pelas citações verificadas em
> `referencias_metodologia.md`. Foi feita por um agente de IA, sem calcular nenhum resultado novo.
> Onde uma decisão já vale para o texto mas o código ou os dados versionados ainda não a refletem,
> o texto afirma a decisão e traz um `[PENDENTE]` dizendo o que falta (a regeneração do dataset é a
> Issue #56).
>
> **Legenda dos marcadores**
>
> * `[PENDENTE: ...]`: informação que ainda **não existe** (resultado, decisão ou etapa humana). Diz
>   qual issue ou arquivo vai fornecê-la. Não preencher com estimativas.
> * `[VERIFICAR: ...]`: inconsistência ou dúvida encontrada ao cruzar documentos, código e CSVs, ou
>   referência com verificação incompleta. Precisa ser resolvida pelos autores antes da submissão.
> * Os marcadores `[REF]` da versão anterior foram todos substituídos por citações no formato
>   autor-ano; a lista completa está em "Referências", no fim do arquivo.
>
> **Regras seguidas:** tudo o que está afirmado abaixo foi derivado do código (`metricas/`,
> `pipeline/`, `analises/`), dos documentos em `lab03/docs/`, do `config.yaml`, dos CSVs
> versionados ou das decisões do grupo de 20/10/2026 (citadas no texto como "decisão do grupo,
> 20/10/2026"). O apêndice B liga cada afirmação ao arquivo de origem. Nenhum resultado de análise
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
de análise é o **repositório** open-source do GitHub que usa GitHub Actions e atende aos critérios de
inclusão da seção 3.3 (amostra-alvo de 330 repositórios, `amostra.tamanho_final` em `config.yaml`).
Para cada repositório, calculamos as quatro métricas DORA (*deployment frequency*, *lead time for
changes*, *change failure rate* e tempo de recuperação) (Forsgren, Humble & Kim, 2018; Harvey, s.d.,
[guia das métricas](https://dora.dev/guides/dora-metrics-four-keys/); DORA, 2024) dentro de uma
única janela de observação de 12 meses (seção 3.2). Seguimos a definição clássica das quatro
métricas adotada no guia da disciplina; o guia online da DORA hoje descreve cinco métricas (inclui
o *deployment rework rate*) e já renomeou a métrica de recuperação, então ele serve aqui como
referência conceitual, e não como especificação das fórmulas. Não há intervenção sobre os
repositórios: os dados são coletados a posteriori, a partir de registros públicos.

Como o GitHub não registra *deploys* nem falhas em produção, todas as métricas são **proxies**:
uma *release* publicada representa um *deploy*, e uma execução de CI com falha representa uma falha.
Por isso o estudo inclui, além do cálculo das métricas, (i) uma **validação manual** do proxy de
falha por entrega (CFR (b)) contra o julgamento humano e (ii) uma **análise de sensibilidade** sobre
as definições operacionais (RQ 07).

**Tabela 1.** Questões de pesquisa, métricas e análise planejada.

| RQ | Pergunta | Métrica / variantes | Análise planejada | Hipótese informal (a priori) |
|---|---|---|---|---|
| RQ 01 | Qual a frequência de deploys? | *Deployment frequency* = releases publicadas (sem rascunhos nem pré-releases) na janela ÷ 52,1 semanas (constante do guia; a janela tem 365 dias ≈ 52,14 semanas) | mediana, IQR e faixa DORA | `artigo_contexto_e_hipoteses.md` |
| RQ 02 | Qual o tempo entre commit e deploy? | *Lead time*: (a) por release; (b) por commit | mediana, IQR e faixa DORA; contraste (a) × (b) | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 03 | Qual a taxa de falha das mudanças entregues? | CFR: (a) proxy de CI (runs `push` do default branch com falha ÷ runs com sucesso ou falha); (b) proxy de entrega (release corretiva em até 7 dias) | mediana, IQR e faixa DORA; contraste (a) × (b) | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 04 | Qual o tempo de recuperação após falha de CI? | Duração de episódios de falha por workflow (mediana por repositório); proporção de episódios censurados | mediana, IQR e faixa DORA | `docs/hipoteses_rq04_rq07.md` |
| RQ 05 | Maior frequência de deploy implica maior ou menor taxa de falha? | Correlação de Spearman entre RQ 01 e RQ 03, para CFR (a) e CFR (b) | ρ, p-valor e n | `docs/hipoteses_rq02_rq03_rq05.md` |
| RQ 06 | Que características dos repositórios se associam ao desempenho? | Métricas das RQ 01 a 04 comparadas entre subgrupos | Kruskal-Wallis / Mann-Whitney, correção de Holm, ε² / Cliff's δ | `artigo_contexto_e_hipoteses.md` |
| RQ 07 | A classificação DORA depende da definição operacional? | Combinações C1, C2 e C3 (seção 3.5.6) | % de mudança de categoria e κ de Cohen ponderado (pesos lineares) | `docs/hipoteses_rq04_rq07.md` |
| RQ 08 (bônus) | (Rework rate ou evolução temporal) | — | — | `[PENDENTE: decisão do grupo sobre fazer ou não a RQ 08; nada disso existe no repositório]` |

As hipóteses informais foram versionadas antes do primeiro dado do Lab03 (arquivos de hipóteses em
08/10/2026; primeiro `repositorios.csv` em 09/10/2026, segundo o histórico do Git) e devem estar na
Introdução do artigo; esta seção não as repete. `docs/hipoteses_rq04_rq07.md` foi alterado depois
(#51, 14/10/2026, correção da definição de falha no texto da RQ 04). Um dos autores (João Pedro)
confirmou, em 20/10/2026, que nenhuma hipótese foi escrita nem alterada depois de ver dados do
dataset e que ele não viu nenhuma coleta local anterior a 09/10/2026. Os outros dois autores
(Marcela e Gabriel) **não foram consultados** sobre isso, e a ordem “hipótese antes dos dados” também
só foi checada pelas datas dos commits; por isso a afirmação vale, por ora, como declaração de um
autor.
`[VERIFICAR: Marcela e Gabriel devem confirmar que não viram dados do dataset antes de escrever ou alterar as hipóteses (incluindo a alteração de 14/10/2026, #51); o texto da Introdução no Overleaf não está no repositório.]`

### 3.2 Fonte de dados e janela de observação

**Fonte.** Os dados vêm da API REST e da API GraphQL do GitHub, mais um clone Git local de cada
repositório (seção 3.4). Seguindo o guia, a coleta é feita por código próprio (cliente HTTP
assíncrono sobre `httpx`), sem bibliotecas prontas de acesso à API do GitHub.

**Janela.** A janela de observação tem 12 meses, de **01/10/2025 a 30/09/2026, ambos os dias
inclusive**: do início de 01/10/2025 (00:00:00 UTC) ao **fim do dia 30/09/2026 (23:59:59 UTC)**, o que
dá **365 dias** (≈ 52,14 semanas). Entram nos cálculos apenas releases publicadas e *workflow runs*
criados dentro da janela. Para a frequência de deploy, divide-se a contagem de releases por **52,1
semanas** (constante `DEFAULT_WINDOW_WEEKS` em `metricas/dora.py`, valor indicado pelo guia para 12
meses e igual a 365/7 com a precisão de uma casa; a diferença para 52,14 é de cerca de 0,08%).

*Origem da janela.* As datas foram **definidas pelo grupo em sala de aula**. Não há registro escrito
dessa definição e ela **não foi confirmada com o professor** (decisão do grupo, 20/10/2026: não
será pedida confirmação). O `guialab03.md` só diz que o professor fixa as datas na abertura do
Lab03S01, sem trazê-las.

*Limite superior (mudança em relação à primeira coleta).* Na primeira coleta, `janela.fim = "2026-09-30"`
era lido como 2026-09-30T00:00:00Z (`metricas/schemas.py::_parse_datetime`), tanto para as releases
(`pipeline/releases.py::filter_window`) quanto para o último intervalo mensal de runs
(`pipeline/workflow_runs.py::split_window_into_months`). O dia 30/09 ficava de fora e a janela efetiva
tinha 364 dias (52,0 semanas). Por **decisão do grupo (20/10/2026)**, o limite superior passa a ser o
**fim do dia** (2026-09-30T23:59:59Z, inclusive), e o dataset será regenerado com ele. Uma estimativa
offline sobre os dados persistidos (`docs/impacto_limitacoes_conhecidas.md`, seção 3) mostra que o
dia 30/09 corresponderia a cerca de 93 releases (0,36% das 25.731) e 7,2 mil runs (0,32%), ou seja,
a mudança é pequena para as estatísticas agregadas e importa sobretudo para repositórios na fronteira
de uma faixa. O corte de censura do CFR (b) (`janela.fim − 7 dias`, seção 3.6) acompanha o novo limite.
`[PENDENTE: aplicar a mudança no config.yaml e no código e regenerar o dataset (#56). Em 21/10/2026, o config.yaml ainda traz fim "2026-09-30" lido como 00:00Z, e os CSV/Parquet versionados foram gerados com a janela de 364 dias; os valores que dependem da janela (releases na janela, deployment_frequency, censura do CFR (b), caracterização da amostra) devem ser reconferidos depois da regeneração. analises/persistir_amostra_ouro.py e analises/amostra_ouro.py (DEFAULT_WINDOW_END) também fixam o limite e precisam acompanhar a mudança.]`

*Desvio documentado.* A **seleção dos 330 repositórios** (seção 3.3) e o **sorteio da amostra-ouro**
(seção 3.7; 15/10/2026, completado em 20/10/2026) foram feitos com a janela antiga, que terminava em
30/09/2026 às 00:00Z. Por decisão do grupo (20/10/2026), os 330 repositórios ficam **congelados**: a
seleção e o funil não são refeitos, e a regeneração recoleta os mesmos 330 com a janela nova. Os
critérios de inclusão (≥ 5 releases e ≥ 50 runs na janela) não são reavaliados com o dia 30/09 incluído,
e o sorteio das releases da amostra-ouro não é refeito.

**Data da coleta.** O dataset versionado foi coletado em duas execuções do pipeline, nas datas dos
respectivos commits, confirmadas por um dos autores: **10/10/2026** (100 repositórios, Issue #47) e
**14/10/2026** (230 repositórios, Issue #53), ambas com Python 3.14 (seção 3.10). A correção do
funil (#66) e o preenchimento posterior das colunas `cfr_b*` (#56, 20/10/2026) não foram execuções de
coleta. `[PENDENTE: data da regeneração final do dataset (#56), que recoleta os mesmos 330 repositórios com as regras decididas em 20/10/2026.]`
Como a Search API e as contagens (estrelas, releases, runs) refletem o estado do GitHub no momento
da coleta, uma nova execução pode produzir uma amostra ligeiramente diferente.

**Branch.** Considera-se apenas o *default branch* de cada repositório (`defaultBranchRef` do GraphQL).

### 3.3 Seleção de repositórios e funil

**Candidatos.** A Search API é consultada com fatiamento por faixas de estrelas, para contornar o
teto de 1.000 resultados por consulta: `>10000`, `5001..10000`, `2501..5000`, `1501..2500` e
`1000..1500`. Cada consulta usa os qualificadores `archived:false`, `mirror:false` e `size:>1000`,
ordenação por estrelas decrescente e até 10 páginas de 100 resultados. Duplicatas entre faixas são
unificadas por `owner/name`. As faixas são percorridas na ordem acima e os candidatos são avaliados
na ordem em que chegam; como o funil avaliou menos de 1.000 candidatos (753 na Tabela 2), a primeira
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
| Candidatos avaliados até atingir a meta (Search API); **derivada: aceitos + descartes** | 753 | — | — |
| Uso de CI/CD (GitHub Actions) | 697 | 56 | `total_count` de workflows = 0 ou erro de acesso |
| ≥ 5 releases publicadas na janela | 382 | 315 | menos de 5 releases na janela |
| ≥ 50 *workflow runs* válidos na janela | 332 | 50 | menos de 50 runs válidos no default branch |
| Integridade do clone local | 330 | 2 | falha irrecuperável no `git clone` |
| **Amostra final** | **330** | — | — |

A primeira linha é **derivada**: é a soma dos repositórios aceitos (330) com os descartados nas etapas
seguintes (56 + 315 + 50 + 2 = 423), e a coluna "restantes" fecha em cada etapa (753 − 56 = 697;
697 − 315 = 382; 382 − 50 = 332; 332 − 2 = 330). Ela conta os candidatos **avaliados**, e não todos os
resultados que a Search API devolveria, porque a avaliação para ao atingir a meta
(`docs/criterios_selecao_e_funil.md`). Esta tabela corrige a versão anterior do `funil.csv`, cuja
primeira linha era 653 e cuja coluna "restantes" terminava em 230, e não nos 330 aceitos; o código do
pipeline passou a derivar a primeira linha em vez de persistir o contador (Issue #66). O texto do
artigo deve descrever a primeira linha apenas como derivada (aceitos + descartes). A evidência
disponível não permite afirmar por que o contador antigo ficou 100 abaixo do valor derivado, e este
rascunho não propõe uma explicação.

Fora do funil, `dados/runs/` tem 333 arquivos para os 330 repositórios da amostra. Os três a mais
(`elastic__elasticsearch`, `home-assistant__core` e `ueberdosis__tiptap`) são órfãos, sem linha em
`repositorios.csv`; por decisão do grupo (20/10/2026), eles saem do versionamento (ver 3.10).

**Caracterização da amostra.** Valores calculados sobre as 330 linhas de `dados/repositorios.csv`
(38 colunas nessa versão do arquivo, das quais 8 ainda nulas; estrelas medidas no momento da coleta de cada bloco de repositórios, 10/10 e 14/10/2026):

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

`[PENDENTE: reconferir esta tabela depois da regeneração do dataset (#56), que recoleta os mesmos 330 repositórios com a janela de 365 dias; o repositorios.csv versionado ainda tem lead time anterior à correção do clone e as colunas de pré-releases, tags, C2 e C3 nulas, e as contagens de releases e runs mudam com o dia 30/09 incluído.]`

### 3.4 Coleta de dados e pipeline

A coleta roda com um único comando (`uv run python -m pipeline --config config.yaml`). A opção
`--limit N` limita o número de repositórios aceitos, e `--clean` apaga o dataset, o funil e o estado
da execução anterior (`dados/runs/` e o cache HTTP não são apagados). Os tokens são lidos de
`GITHUB_TOKENS` (lista separada por vírgulas, que habilita a rotação) ou `GITHUB_TOKEN`, nas
variáveis de ambiente ou, na falta delas, em um arquivo `.env`, e por último de `gh auth token`.
`.env`, o cache e o estado da execução estão no `.gitignore` e nunca são versionados.

**Metadados e releases.** A consulta GraphQL `repo_details.graphql` (uma por repositório, repetida
com cursor apenas se as releases não cabem em uma página de 100) traz estrelas, linguagem principal,
default branch, data de criação e as releases (tag, data de publicação, *draft* e *pre-release*),
ordenadas por data de **criação** decrescente. A paginação para na página que contém a **release
âncora**: a última release estável anterior à janela, usada como predecessora da primeira release
da janela. Isso supõe que a ordem de criação coincida com a de publicação; uma release criada muito
antes de ser publicada poderia ficar em página não lida, e não medimos essa ocorrência. Rascunhos e
releases sem data de publicação são descartados na coleta.
O número de contribuidores é obtido por `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true`,
lendo o número da última página no cabeçalho `Link` (0 se a requisição falha). Se o GraphQL falha,
há uma rota de contingência em REST (`GET /repos/{owner}/{repo}/releases` e os metadados do candidato
devolvido pela Search API).

***Workflow runs*.** `GET /repos/{owner}/{repo}/actions/runs` com `branch` = default branch,
`event=push`, `created=<início>..<fim>` e 100 resultados por página. A janela é dividida em
intervalos por mês-calendário (UTC), consultados em paralelo. Se um intervalo devolve
`total_count ≥ 1.000` (teto de resultados por consulta), ele é dividido ao meio (metades disjuntas,
em segundos inteiros) e as metades são consultadas em paralelo, **recursivamente, sem limite de
profundidade e sem tamanho mínimo em dias** (decisão do grupo, 20/10/2026; antes: profundidade máxima 3
e intervalos mínimos de 2 dias). A divisão só pára quando `total_count < 1.000` ou quando o intervalo
chega a 1 segundo. **Não há marcador de truncamento** no dataset (decisão do grupo): se um intervalo
de 1 segundo ainda tem `total_count ≥ 1.000`, o filtro `created` não consegue separá-los, o coletor lê
os 1.000 primeiros e registra um único aviso por repositório. Esse **limite residual** é declarado
na seção 3.9. Os runs são deduplicados por `id` e gravados em
`dados/runs/{owner}__{repo}.parquet`, com `id`, `workflow_id`, `name`, `event`, `branch`,
`conclusion`, `run_started_at`, `updated_at` e `is_valid`. O arquivo guarda todos os runs
recuperados, inclusive os de conclusão ignorada; só `is_valid` os distingue.
`[PENDENTE: os runs/ versionados foram coletados com a regra antiga (profundidade 3, mínimo de 2 dias); a regra nova só vale para o dataset depois da regeneração (#56), que faz mais chamadas à API por repositório.]`

**Commits de cada release: clone Git local no lugar do `compare`.** O guia sugere obter os commits
de uma release com `GET /compare/{base}...{head}`. O pipeline, desde a Issue #47, obtém os mesmos
commits com `git log {release anterior}..{release}` em um **clone parcial *bare*, *treeless* e
*blobless*** (`git clone --bare --single-branch` com filtro de objetos), seguido de um `fetch` com o
mesmo filtro para trazer todas as tags. *Treeless* é o filtro `tree:0` e *blobless* é o filtro
`blob:none`; **nota técnica:** `tree:0` já exclui as árvores **e** os blobs, então os dois nomes
descrevem, na prática, o mesmo clone, que só traz objetos de commit e tags. Por **decisão do grupo
(20/10/2026)**, o pipeline usa **um único filtro combinado**, `combine:tree:0+blob:none`, e o texto
cita os dois termos. Na implementação (Issue #56), o servidor do GitHub **rejeita** filtros `combine`
no clone (`filter 'combine' not supported`), de modo que o código passa `--filter=tree:0`
(`pipeline/git_clone.py::CLONE_FILTER`), que é equivalente ao combinado: SHAs, datas de autor,
assuntos, mensagens e tags saem idênticos nos testes do repositório (`dados/README.md`, seção 5).
`[VERIFICAR: o texto do artigo não deve dizer que o clone usa literalmente combine:tree:0+blob:none; a decisão do grupo foi o filtro combinado, mas o que roda contra o GitHub é tree:0.]`
A semântica é a do `compare` (commits alcançáveis pela release e não pela anterior), com estas
vantagens:

* **não consome a cota das APIs REST e GraphQL**, o que importa para 330 repositórios com milhares
  de releases (a base tem 25.732 releases na janela). O clone usa o protocolo Git em `github.com`,
  que tem limites próprios (ver o uso de token abaixo);
* **não tem o teto de 250 commits** nem exige paginar o `compare`;
* o clone sem árvores nem blobs traz apenas objetos de commit, que bastam para o `git log` entre
  tags, em vez do repositório completo. Não medimos o ganho de tempo nem de espaço.

O clone tenta primeiro sem autenticação e, se falhar por limite de taxa ou autenticação (mensagem de
erro com `403`, `429`, `authentication`, `rate limit` ou `username`), tenta de novo com um token do
conjunto. O clone fica em `cache/git_repos/` e é apagado depois do uso (`limpeza_git_cache: true`
no `config.yaml`). A primeira versão do clone
trazia só as tags alcançáveis do default branch e fazia o pipeline descartar como "tag não
encontrada" 20,6% das releases da janela; o `fetch` de todas as tags corrigiu isso (seção 3.9,
`docs/investigacao_lead_time.md`). Se esse `fetch` falhar, o clone continua utilizável, com aviso no
log, e as releases cujas tags faltam recebem `not_found`. A implementação via REST
(`pipeline/commits.py`) continua no código e testada, mas não é a usada na coleta.

**Datas e mensagens dos commits.** Cada commit é guardado com SHA, data do **autor**
(`%aI`, equivalente a `commit.author.date`, como manda o guia), **assunto** da mensagem (primeira
linha, `%s`, campo `message`) e **mensagem completa** (`%B`, assunto mais corpo, campo
`full_message`). A mensagem completa passou a ser coletada por decisão do grupo (20/10/2026): a
primeira coleta guardava só o assunto (ver nota histórica na seção 3.9). Quebras CRLF viram `\n`,
espaços nas pontas são removidos e o texto é truncado em 10.000 caracteres
(`metricas.schemas.MAX_FULL_MESSAGE_CHARS`). A heurística de release corretiva `v1` continua lendo
só o assunto (padrão inalterado); a variante `v1_full_message` aplica a mesma regra à mensagem
completa e é avaliada junto com a `v1` (seção 3.6).
`[PENDENTE: os releases/ e o repositorios.* versionados não têm full_message; só a regeneração (#56) o coleta.]`

**Releases, pré-releases e tags (C1, C2 e C3).** Para a RQ 07, o pipeline coleta três conjuntos de
"unidades de deploy" na mesma rodada, cada um com a lista de commits entre unidades consecutivas:

| Conjunto | Unidade de deploy | Arquivo (por repositório) | Datação |
|---|---|---|---|
| C1 (definição principal) | releases publicadas, sem pré-releases | `dados/releases/` | `published_at` da release |
| C2 | releases publicadas **e** pré-releases | `dados/releases_c2/` | `published_at` da release |
| C3 | tags Git | `dados/tags/` | data do autor do commit apontado pela tag |

Em cada conjunto, a **predecessora** de uma unidade é a unidade imediatamente anterior na ordem
cronológica; para a primeira unidade da janela, é a âncora (a última unidade anterior à janela). Se
não há âncora, a unidade é a primeira release (ou tag) do repositório (`first_release`) e não entra
no lead time. Se o `git log {predecessora}..{unidade}` não resolve (por exemplo, a tag da release ou
da predecessora não existe no clone, equivalente ao 404 do `compare`), a unidade recebe o status
`not_found` e também fica fora do lead time. Cada unidade é marcada com `ok`, `first_release` ou
`not_found`, e essas contagens são reportadas (seção 3.9). A coluna `status` só é gravada em
`releases/` e `releases_c2/`; em `tags/` ela não é gravada e `commits_count` vale 0 tanto para
`first_release` quanto para `not_found`.

**Robustez e retomada.** O cliente HTTP (HTTP/2, até 15 requisições simultâneas) lê
`X-RateLimit-Remaining` e `X-RateLimit-Reset` de cada resposta. Quando um token esgota a cota, ele
fica em espera até o reinício (ou por 60 s, se o cabeçalho não existe) e o cliente passa ao próximo
token do conjunto, em rodízio; se todos estão em espera, aguarda o primeiro reinício, e sem nenhum
token aguarda o reinício da cota. Um token que devolve 401 é desativado. Erros 5xx e de rede são
repetidos com *backoff* exponencial: até 5 novas tentativas, com esperas de 1, 2, 4, 8 e 16 s. Toda
resposta 2xx é gravada em um cache SQLite em disco (modo WAL), indexado por URL e parâmetros e sem
prazo de validade. Cada repositório aceito é gravado de forma incremental em
`dados/repositorios.parquet`/`.csv`, e os contadores de descartes e os nomes já avaliados ficam em
`dados/.pipeline_state.json`. Assim, uma execução interrompida (limite de taxa, queda de rede,
*Ctrl+C*) continua de onde parou: os candidatos já avaliados são pulados e as chamadas já feitas são
servidas do cache. Como o cache não expira, uma nova execução com o mesmo `cache/` reaproveita
respostas antigas; para recoletar do zero é preciso apagar o `cache/` e usar `--clean`. Os clones
Git são temporários e não entram no cache.

As funções de métricas e do pipeline têm testes automatizados com *fixtures* sintéticas (pytest). A
verificação local exige cobertura mínima de 80% sobre `metricas` e `pipeline`
(`pytest --cov=metricas --cov=pipeline --cov-fail-under=80`). O GitHub Actions do repositório
(`.github/workflows/testes-lab03.yml`) executa `pytest --cov=metricas --cov-fail-under=80`, ou seja,
exige cobertura apenas do módulo `metricas`, como pede o guia.

### 3.5 Definições operacionais e métricas

Todas as fórmulas abaixo estão implementadas em `metricas/` e documentadas coluna a coluna em
`dados/README.md`. Os tempos são calculados em horas; para classificar, o lead time (variante (a))
é convertido em dias (÷ 24) e o tempo de recuperação permanece em horas (3.5.5).

#### 3.5.1 Frequência de deploy (RQ 01)

$$\text{DF} = \frac{\text{releases publicadas na janela (draft = false, prerelease = false)}}{52{,}1\ \text{semanas}}$$

O numerador conta as releases com `janela.inicio ≤ published_at ≤ janela.fim` (limites inclusivos).
O divisor 52,1 é o valor fixo do guia (≈ 365 ÷ 7 = 52,14) e não é recalculado a partir das datas
configuradas. Com o fim do dia 30/09/2026 (decisão do grupo, seção 3.2), a janela tem 365 dias,
52,14 semanas, e o divisor 52,1 a subestima em cerca de 0,08%. Na primeira coleta, em que o dia 30/09
ficava de fora, a janela efetiva tinha 364 dias (52,0 semanas) e a diferença era de cerca de 0,2%;
esse valor é só histórico.
`[PENDENTE: os limites inclusivos acima valem para o dataset regenerado (#56); o repositorios.* versionado foi gerado com a janela de 364 dias.]`

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
juntos**. Cada run conta uma vez, sem ponderar por workflow nem por commit: um mesmo `push` pode
gerar vários runs, um por workflow. A classificação da conclusão segue o guia:

| `conclusion` | Tratamento |
|---|---|
| `success` | sucesso |
| `failure`, `timed_out`, `startup_failure` | falha |
| `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio (em andamento) | ignorado: fora do numerador e do denominador |

Nos `runs/` versionados (2.289.119 runs dos 330 repositórios) aparecem apenas `success`,
`failure`, `startup_failure`, `cancelled`, `skipped` e conclusão vazia; as demais linhas da tabela
estão previstas no código, mas não ocorreram. O $\text{CFR}_a$ é nulo se o repositório não tem nenhum
run de sucesso ou falha, o que não ocorre na amostra (todos têm pelo menos 51 runs válidos). Esta
variante mede falha de **pipeline**, e não falha em produção.

#### 3.5.4 Tempo de recuperação e censura (RQ 04)

Os runs são agrupados por workflow (`workflow_id`) e ordenados por `run_started_at`. Dentro de cada
workflow, conclusões ignoradas não iniciam, interrompem nem encerram episódios. Um **episódio de
falha** começa na primeira falha (a primeira depois de um sucesso ou, se o workflow não tem sucesso
anterior, a primeira falha do histórico coletado) e inclui as falhas consecutivas; ele termina no
próximo sucesso do mesmo workflow. Quando o histórico coletado começa por uma falha, a falha pode ter
começado antes da janela, e a duração é medida a partir do primeiro run visto (censura à esquerda,
não tratada). A duração é

$$\text{recuperação} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira falha}}$$

(em horas, truncada em 0). O valor do repositório é a **mediana** das durações dos episódios
resolvidos, de todos os workflows. Um episódio que não termina até o fim do histórico coletado é
**censurado**, e o pipeline registra a proporção
`censored_episodes_ratio = censurados ÷ (resolvidos + censurados)` (0 se não há episódios). Os
episódios censurados **não são descartados da contagem**, mas também **não entram na mediana**, que
usa apenas os episódios resolvidos (ver ameaça na seção 3.9). O valor é nulo se nenhum episódio foi
resolvido, seja porque não houve nenhum episódio de falha, seja porque todos os episódios ficaram
censurados; a classificação trata os dois casos de forma diferente (3.5.5).

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

**Valores ausentes (decisão do grupo, 20/10/2026).** Um valor nulo nunca é imputado; o que muda é a
faixa atribuída (`metricas/dora.py`, `pipeline/orchestrator.py`; `dados/README.md`, seção 2):

* **Tempo de recuperação nulo sem nenhum episódio de falha** (`censored_episodes_ratio = 0`): não há
  nada a recuperar, e o repositório é classificado **Elite**. No dataset anterior à decisão, são 15
  repositórios (todos com `cfr_a = 0`).
* **Tempo de recuperação nulo porque todos os episódios ficaram censurados**
  (`censored_episodes_ratio > 0`): o repositório falhou e não voltou a passar no histórico coletado, e
  é classificado **Low**. São 3 repositórios.
* **Lead time nulo** (falta de dado: nenhuma release avaliável): a métrica **fica sem faixa** (não é
  `Low` nem `Elite`) e **sai da nota geral**, que passa a ser a mediana das 3 notas disponíveis, em
  vez de 4, arredondada para baixo. No dataset anterior à correção do clone são 61 repositórios, e
  depois dela resta 1 (`expo/expo`).
* **CFR (a) nunca é nulo** na amostra (0 nulos nos 330); o critério de ≥ 50 runs válidos impede o
  caso, e o código mantém `Low` caso ele ocorresse.
* **CFR (b) fica fora da nota geral**; quando é nulo, `cfr_b_tier` é nulo.

A frequência de deploy nunca é nula. Uma estimativa offline sobre os dados persistidos
(`docs/impacto_limitacoes_conhecidas.md`, seção 4) indica a ordem de grandeza do efeito, medido
**isoladamente** para cada regra: classificar "sem falhas" como Elite em recuperação muda a faixa
geral de cerca de 14 repositórios, e tirar o lead time nulo da mediana muda cerca de 7. Antes da
decisão, os nulos eram tratados como `Low` (90% dos 20 repositórios `Low` em recuperação eram nulos,
15 deles sem falha alguma), o que penalizava justamente quem nunca falhou. A regra decidida não foi
medida em conjunto.
`[PENDENTE: recalcular as faixas e a nota geral e reportar a distribuição final depois da regeneração (#56): o repositorios.csv versionado foi gerado com a regra antiga (nulo → Low), e suas colunas de faixa ainda não refletem esta regra.]`

Em todas as RQs, reportamos **mediana e intervalo interquartil (IQR)**, e não média e desvio-padrão,
por causa da assimetria das distribuições, como pede o guia.

#### 3.5.6 Combinações de definições para a análise de sensibilidade (RQ 07)

O pipeline grava só as frequências de deploy e os lead times (b) de C2 e C3, e não as faixas nem a
nota geral dessas combinações: a análise da RQ 07 precisa classificá-las com as mesmas funções de
`metricas/dora.py`. O CFR (a) é o mesmo nas três combinações (`cfr_a`). O `repositorios.csv`
versionado já tem as 38 colunas, mas as 8 de pré-releases, tags, C2 e C3 estão nulas (ver 3.10).

| Combinação | Unidade de deploy | Lead time | CFR |
|---|---|---|---|
| C1 (referência) | release (sem pré-release) | (a) | (a) |
| C2 | release + pré-release | (b) | (b) |
| C3 | tag | (b) | (a) |

O dataset traz, além da referência, `c2_deployment_frequency`, `c2_lead_time_b_hours`,
`c3_deployment_frequency` e `c3_lead_time_b_hours`. Em C3, a data de uma tag é a data do autor do commit
apontado por ela (`git for-each-ref`, não a data de criação da tag), e não o `published_at` de uma
release.
**CFR (b) na combinação C2 (decisão do grupo, 20/10/2026).** O `cfr_b` de referência do dataset é
calculado sobre as releases de C1 (`dados/README.md`, seção 2.1). Para a combinação C2, que usa CFR
(b), ele é **recalculado sobre as unidades de C2** (releases publicadas **e** pré-releases, a partir de
`dados/releases_c2/`), e não sobre C1, de acordo com a definição da combinação C2 (todas as métricas sobre a mesma unidade
de deploy); a RQ 07 usa esse valor. Os valores de C1 e C2 serão
reportados lado a lado: `[PENDENTE: resultados após regeneração]`.
`[PENDENTE: implementar o cálculo no pipeline (colunas próprias de C2, previstas como c2_cfr_b*) e gerar releases_c2/ na regeneração (#56). Em 21/10/2026, pipeline/orchestrator.py ainda chama compute_cfr_b_columns só com release_commits_c1, e releases_c2/ não é versionado.]`

### 3.6 CFR (b) e a heurística de release corretiva

**Definição.** Uma release $R$ **falha** se for seguida, **em até 7 dias**, por uma release
**corretiva**, isto é, uma release cujo objetivo principal é corrigir um defeito recente. O
$\text{CFR}_b$ do repositório é `releases que falharam ÷ releases avaliadas`. O guia não define como
identificar uma release corretiva e pede que o grupo proponha uma heurística automática e a valide
contra a amostra rotulada manualmente (seção 3.7).

**Classificação de cada release da janela** (`metricas/cfr_b.py::calculate_cfr_b`, as unidades em
ordem cronológica, C1):

1. **Censurada:** publicada depois de `janela.fim − 7 dias`. Com o fim do dia 30/09/2026
   (23:59:59Z, decisão do grupo, seção 3.2), isso vale para releases publicadas depois de 23/09/2026
   23:59:59 UTC. Ainda não se sabe se haverá correção; fica fora do denominador. Com o limite antigo
   (30/09 às 00:00Z), o corte era 23/09 às 00:00Z; uma estimativa offline contou 1.050 releases
   censuradas em 141 repositórios nessa regra antiga (`docs/impacto_limitacoes_conhecidas.md`).
   `[PENDENTE: o código ainda calcula o corte com o fim lido como 00:00Z até a mudança da janela (#56); recontar as censuradas depois da regeneração.]`
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

**Heurística `v1`** (`metricas/cfr_b.py::heuristic_v1`; é a versão padrão, e a versão em uso é
escolhida em `cfr_b.heuristica` do `config.yaml`, com `v1` como padrão; o dataset **não** grava qual
versão foi usada, conforme `dados/README.md`, seção 2.1). Está registrada também a
`v1_full_message` (descrita abaixo), que não altera o padrão. A release $N$, com predecessora $R$, é
**corretiva** se as duas condições ocorrem juntas:

1. **só o número de *patch* aumenta** em relação a $R$ no Versionamento Semântico (Preston-Werner, [s.d.]; [semver.org](https://semver.org/lang/pt-BR/))
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
essa frequência é uma impressão do autor da heurística (confirmada por ele em 20/10/2026), e não foi
medida neste repositório.

**Variante `v1_full_message`.** Como a coleta passou a guardar a mensagem completa do commit (3.4), a
mesma regra da `v1` também é avaliada sobre assunto e corpo (`Fixes #123`, `Revert ...` no corpo,
mensagens de *merge*). Ela é registrada em `HEURISTICS` como `v1_full_message`; o padrão do pipeline
**continua sendo a `v1`**, e as duas serão avaliadas contra o consenso (3.7). Em dados persistidos
antes do campo `full_message`, a variante cai no assunto e coincide com a `v1`.

**Política de versão final (decisão do grupo, 20/10/2026).** Aceita-se a `v1` se o F1 contra o
consenso for ≥ 0,70. Se for menor, **Gabriel escreve a `heuristic_v2`**, sem prazo definido (o
prazo não foi acordado), e a versão final é a **de maior F1** entre as testadas, que entram todas no
artigo.

`[PENDENTE: versão final da heurística (v1, v1_full_message ou refinamentos v2, v3...) e o F1 de cada versão testada, que dependem da avaliação contra o consenso (#62), por sua vez dependente da rotulação (#57, #61, #64) e do consenso (#65).]`

### 3.7 Validação manual (amostra-ouro)

**Objetivo.** Estimar o quanto o proxy automático de release corretiva (CFR (b)) concorda com um
conjunto de rótulos de referência (a amostra-ouro) e rotular o tipo do projeto nos 60 repositórios
(a rotulação do tipo nos 330 é descrita em 3.8). **Desvio do guia:** o guia prevê julgamento humano;
nesta pesquisa, a maior parte dos rótulos da amostra-ouro foi produzida por um avaliador LLM (ver
"Rotulação e desvio do protocolo", abaixo), e o texto do artigo não pode chamá-los de rótulos humanos.

**Amostragem.** Foram sorteados **60 repositórios** das 330 linhas de `dados/repositorios.parquet`,
com `df.sample(n=60, random_state=42)`, e, para cada um, **5 releases** sorteadas entre as releases
publicadas da janela (C1, sem pré-releases), com semente determinística por repositório
(`42 × 1000 + índice`, em que o índice vai de 1 a 60 na ordem do sorteio dos repositórios). O desenho
prevê **300 linhas** (60 × 5). A lista dos 60 repositórios está em `dados/amostra_ouro/sorteio_info.json`
(gerado em 15/10/2026) e o código está em `analises/amostra_ouro.py`. Reexecutar o sorteio sobre o
`repositorios.parquet` e o `repositorios.csv` versionados reproduz exatamente os mesmos 60 repositórios.
O sorteio foi feito em duas etapas: em 15/10/2026, só 30 dos 60 repositórios tinham releases
persistidas; em 20/10/2026, as releases dos outros 30 foram sorteadas com a mesma semente, o mesmo
método e a mesma janela (`analises/amostra_ouro.py --completar-pendentes`, Issue #63), sem alterar o
sorteio dos 30 primeiros. As planilhas atuais têm as 300 linhas com releases reais
(`docs/amostra_ouro.md`).

Como o conjunto dos 330 repositórios fica congelado e a regeneração do dataset recoleta os mesmos 330
(decisão do grupo, 20/10/2026), a lista dos 60 continua válida. O sorteio das releases, porém, usou a
janela antiga (até 30/09/2026 às 00:00Z; ver o desvio documentado em 3.2): releases publicadas em
30/09 depois de 00:00Z não podiam ser sorteadas, e o sorteio não é refeito com a janela nova. O
`sorteio_info.json` é o registro oficial dos 60.

**Rotulação e desvio do protocolo (decisão do grupo, 20/10/2026).** O protocolo do guia pede que três
avaliadores humanos preencham, de forma independente, sua própria planilha (CSV/XLSX com *links*
diretos para a página de cada release no GitHub; `dados/amostra_ouro/amostra_ouro_<nome>.csv`), **sem
consultar os demais e sem ver a saída da heurística**. Por causa do prazo, o grupo decidiu, **com o
consentimento dos autores**, preencher as três vagas de avaliador (`joao`, `gabriel` e `marcela`) com
execuções independentes de um avaliador LLM (claude-opus-5.5, esforço alto), mantendo sem alteração as
**150 linhas válidas de rótulos humanos da Marcela**. Na prática (proveniência registrada em
`validacao/PROVENIENCIA.md`):

| Vaga | Origem dos rótulos | Independência |
|---|---|---|
| `gabriel` | **IA**: execução do próprio Gabriel com o Claude Code (Opus 5.5), 300 linhas, `validacao/rotulos_gabriel.csv` | **Parcial:** o mesmo assistente implementou a heurística `v1` (#59) e conhecia a regra, mas não a executou na amostra nem viu os rótulos dos demais |
| `marcela`, 150 linhas válidas | **Humana** (Marcela; origem `humano`), mantidas sem alteração | Rotulação humana independente, sem ver a saída da heurística |
| `marcela`, 150 linhas inválidas | **IA**: execução do avaliador LLM conduzida pelo agente coordenador do grupo, ainda não versionada | Cega à heurística e às demais execuções (pelo desenho) |
| `joao` | **IA**: execução do avaliador LLM conduzida pelo agente coordenador do grupo, ainda não versionada | Cega à heurística e às demais execuções (pelo desenho) |

`[PENDENTE: as execuções das vagas joao e marcela (150 linhas) serão versionadas em PR próprio, com linhas na tabela de proveniência; até lá, só rotulos_marcela.csv e rotulos_gabriel.csv existem.]`
`[VERIFICAR: confirmar com os autores se o rotulos_gabriel.csv existente, de independência apenas parcial, permanece como a vaga gabriel ou se a vaga será refeita com uma execução cega à heurística; e como as 150 linhas humanas e as 150 de IA da vaga marcela entram no kappa (sugestão a decidir: reportar também a concordância só nas 150 linhas com rótulo humano).]`

**Este desvio tem consequências que o artigo deve declarar:** (i) os rótulos **não são de avaliadores
humanos independentes**, exceto as 150 linhas da Marcela; (ii) o kappa mede a concordância entre
execuções de **um único modelo** (e, na vaga `marcela`, entre humana e IA), de modo que erros
correlacionados (mesmo modelo, mesma informação de entrada) tendem a **inflá-lo**, e ele **não mede a
ambiguidade do critério para humanos**; (iii) o consenso é **mecânico** (seção abaixo), sem reunião;
(iv) o F1 da heurística é medido contra esse consenso, e não contra o julgamento humano, e a
independência em relação à heurística é parcial na vaga `gabriel`. As sessões de rotulação guiada por
humanos continuam disponíveis para substituir ou ampliar qualquer vaga, e, se ocorrerem, o texto deve
ser atualizado e os rótulos humanos registrados com origem `humano`. **Nenhum rótulo produzido por IA
pode ser descrito como humano.**

Como dado indicativo de estabilidade, uma execução independente do avaliador LLM para a vaga
`gabriel`, feita pelo agente coordenador, coincidiu com a execução do Gabriel em **92,7%** das
releases em `release_corretiva`, **88,3%** dos repositórios em `tipo_projeto` e **100%** em
`entrega_real`. É concordância percentual entre duas execuções do mesmo modelo, e não kappa nem
confiabilidade humana. `[PENDENTE: confirmar esses percentuais no PR de rótulos.]`

As dimensões rotuladas são:

| Dimensão | Categorias | Unidade de análise | N |
|---|---|---|---|
| `tipo_projeto` | biblioteca/framework, aplicação/serviço, ferramenta CLI, outro | repositório | 60 |
| `entrega_real` (as releases representam entregas reais ao usuário?) | sim, não, incerto | repositório | 60 |
| `release_corretiva` | sim, não | release | 300 |

`tipo_projeto` e `entrega_real` são julgamentos por repositório e aparecem repetidos nas 5 linhas
dele; para não inflar o kappa, cada repositório é contado **uma vez** nessas duas dimensões, e os
arquivos com valores diferentes entre as linhas do mesmo repositório são rejeitados pela ferramenta.

**Concordância entre as três vagas.** Para cada dimensão, calculamos o **kappa de Fleiss** (Fleiss, 1971)
entre as 3 vagas com `statsmodels` (`aggregate_raters` com `n_cat` fixo, seguido de
`fleiss_kappa(..., method="fleiss")`):

$$P_i = \frac{\sum_j n_{ij}^2 - n}{n(n-1)}, \qquad \bar{P} = \frac{1}{N}\sum_i P_i, \qquad P_e = \sum_j p_j^2, \qquad \kappa = \frac{\bar{P} - P_e}{1 - P_e}$$

com $n = 3$ avaliadores (vagas), $n_{ij}$ o número de avaliadores que escolheram a categoria $j$ na
unidade $i$, e $p_j$ a proporção global da categoria $j$. Reportamos também a concordância unânime (%)
como apoio. Se todos os avaliadores escolhem sempre a mesma categoria, $P_e = 1$ e o kappa é indefinido;
a ferramenta o reporta como `n/d`, e isso será discutido. A interpretação segue Landis & Koch (1977):
< 0 pobre; 0,00-0,20 leve; 0,21-0,40 razoável; 0,41-0,60 moderada; 0,61-0,80 substancial; 0,81-1,00
quase perfeita (a ferramenta usa limites superiores inclusivos, por exemplo 0,40 é razoável). Pelo
desvio acima, essa escala deve ser lida com cautela: um kappa alto entre execuções de um mesmo modelo
não indica que o critério seja inequívoco para humanos, e um kappa baixo indica instabilidade do
julgamento ou ambiguidade do critério. O kappa é calculado **antes** do consenso e os arquivos de
rótulos individuais **não são editados depois**.

**Consenso e desempate** (`docs/protocolo_consenso.md`). (1) Vale a maioria simples (placares 3-0 e
2-1), preenchida pela ferramenta. (2) `release_corretiva`, com apenas duas categorias, sempre tem
maioria. (3) Nos empates 1-1-1 (possíveis em `tipo_projeto` e `entrega_real`) aplica-se diretamente o
desempate final: `tipo_projeto = outro` e `entrega_real = incerto`, regra confirmada pelos três autores
em 20/10/2026. (4) `incerto` é uma categoria como as demais (entra no kappa e na maioria) e **não é
forçado** para `sim` ou `não`. O protocolo original prevê uma **reunião** com os três presentes para
decidir os empates 1-1-1 e rever casos 2-1; **no desenho adotado, o consenso é mecânico e não há
reunião**, o que é outro desvio do protocolo. O arquivo `validacao/consenso.csv` registra, para cada
rótulo, a origem (`unanimidade`, `maioria` ou `reuniao`).
`[PENDENTE: como a origem de cada rótulo será registrada no consenso.csv quando não houver reunião (#65).]`

**Avaliação da heurística** (`docs/avaliacao_heuristica.md`, `analises/avaliar_heuristica.py`). Para
cada release do consenso, aplica-se a heurística (com a release anterior e os commits persistidos) e
compara-se com o rótulo `release_corretiva` de consenso, tomando `sim` como classe positiva:

$$\text{Precisão} = \frac{VP}{VP+FP}, \qquad \text{Recall} = \frac{VP}{VP+FN}, \qquad F_1 = \frac{2PR}{P+R}$$

calculados com `sklearn.metrics.precision_recall_fscore_support`, junto com a matriz de confusão. Se
um denominador é zero, a métrica é reportada como indefinida (`n/d`), e não como 0. Releases que não
podem ser avaliadas (repositório sem arquivo de releases, tag ausente, `status ≠ ok` ou sem release
anterior) são **excluídas, contadas e discriminadas por motivo**, e o conjunto avaliado é o mesmo para
todas as versões da heurística (`v1`, `v1_full_message` e as futuras). A **meta é F1 ≥ 0,70**. Se nenhuma versão atingir a meta, analisa-se
a lista de falsos positivos e negativos, **Gabriel propõe a `heuristic_v2`** (sem apagar as anteriores),
justificada por uma **regra geral** e não por um caso isolado (para limitar o ajuste excessivo às 300
releases), e reavalia-se; a versão final é a de maior F1 (3.6). **Cada versão testada, mesmo as que
falharam, e o seu F1 entram no artigo.**

**Estado atual da validação manual** (concluído em 21/10/2026 no repositório):

* o sorteio e as planilhas estão completos: 60 repositórios × 5 releases reais (Issue #63);
* `validacao/rotulos_marcela.csv`: 300 linhas. **150 são rotulação humana (Marcela)**, mantidas sem
  alteração (as dos 30 repositórios que tinham release real na primeira etapa do sorteio) e **150 são de
  uma execução de IA** (claude-opus-5.5, esforço `high`) para os outros 30 repositórios, listados em
  `validacao/historico/marcela_linhas_invalidas.csv`; a origem de cada linha está em
  `validacao/rotulos_marcela_origem.csv`;
* `validacao/rotulos_gabriel.csv` (Issue #61): 300 linhas, **produzidas por um agente de IA (Claude
  Code, Opus 5.5) a pedido de Gabriel**, e não por rotulação humana, com independência **parcial** em
  relação à heurística. Na concordância e na avaliação, esse arquivo é um **avaliador IA**;
* `validacao/rotulos_joao.csv` (Issue #57): 300 linhas, **produzidas por uma execução de IA**
  (claude-opus-5.5, esforço `high`), independente e cega à heurística, e não por rotulação humana;
* `validacao/extra/rotulos_gabriel_execucao2_ia.csv`: segunda execução de IA para o slot `gabriel`, fora
  dos slots, usada só para medir a confiabilidade entre execuções (`docs/confiabilidade_execucoes_ia.md`);
* todos os três arquivos possuem seus respectivos sidecars de rastreabilidade (`rotulos_*_origem.csv`);

Portanto, **os três arquivos existem, mas não são três avaliadores humanos**: `joao` e `gabriel` são
100% IA (mesmo modelo, erros correlacionados) e `marcela` mistura 150 linhas humanas e 150 de IA. O texto
final explicita essa metodologia. Um **aviso de validade** (`docs/confiabilidade_execucoes_ia.md`, seção 3): a
concordância bruta das execuções de IA com as 150 linhas humanas de Marcela é de ≈58% em
`release_corretiva` (kappa de Cohen ≈ 0,11 a 0,13) e ≈70% em `tipo_projeto`.

* **Concordância e Confiabilidade (Kappa de Fleiss entre os 3 slots):**
  - `tipo_projeto` ($N = 60$): $\kappa = 0,792$ (concordância unânime: 80,0%, substancial);
  - `entrega_real` ($N = 60$): $\kappa = 0,494$ (concordância bruta unânime: 96,7%, dimensão dominada por prevalência de `sim`);
  - `release_corretiva` ($N = 300$): $\kappa = 0,634$ (concordância unânime: 72,3%, substancial).
* **Consenso (`validacao/consenso.csv`):** consolidado em modo automático (`automatico_maioria`, validado por `verificar-consenso`), com 0 casos necessitando de desempate forçado em `release_corretiva` e `entrega_real`, e apenas 1 em `tipo_projeto` (resolvido como `outro`). Todas as decisões foram registradas com transparência de votos de IA vs. votos humanos.

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
  CFR (a) e CFR (b), reportando $\rho$, p-valor e $n$ (Spearman, 1904). Spearman foi escolhida por
  não exigir normalidade nem relação linear (mede associação monotônica, a partir dos postos). O $n$
  pode diferir entre as duas variantes, porque o CFR (b) é nulo quando nenhuma release do repositório
  pôde ser avaliada (3.6). Correlação não implica causalidade.
* **RQ 06.** Comparação das métricas das RQ 01 a 04 entre subgrupos definidos por **no mínimo três
  fatores** entre: linguagem principal, popularidade (quartis de estrelas), número de contribuidores
  (quartis), idade do repositório (quartis) e tipo do projeto. Teste de Kruskal-Wallis para fatores
  com 3 ou mais grupos (Kruskal e Wallis, 1952) e de Mann-Whitney para 2 grupos (Mann e Whitney,
  1947). Os p-valores são corrigidos para comparações múltiplas pelo método de Holm (Holm, 1979;
  `statsmodels.stats.multitest.multipletests`, `method='holm'`). Tamanho de efeito:
  $\varepsilon^2 = H/(n-1)$ para Kruskal-Wallis (Tomczak e Tomczak, 2014), e
  $\delta = 2U_1/(n_1 n_2) - 1$ (Cliff's delta; Cliff, 1993) para dois grupos, interpretado por
  |δ| < 0,147 desprezível, < 0,33 pequeno, < 0,474 médio e ≥ 0,474 grande (Romano et al., 2006).
  `[VERIFICAR: Romano et al. (2006) foi conferido só em fontes secundárias (o PDF original não foi aberto); os limiares de Cliff são atribuídos a essa obra pela documentação do pacote effsize. Abrir o PDF e conferir autores, título e limiares antes de submeter.]`
  `[PENDENTE: fatores efetivamente usados e agrupamento da linguagem principal (23 categorias).]`
  `[VERIFICAR: o guia descreve o tipo do projeto com três grupos (biblioteca/framework, aplicação/serviço, ferramenta CLI), mas a rotulação admite também "outro". Definir se "outro" vira um quarto grupo ou é excluído da RQ 06.]`
* **RQ 07.** Para cada combinação C1, C2 e C3 (3.5.6), classifica-se cada repositório em
  Elite/High/Medium/Low (3.5.5), com o CFR (b) de C2 calculado sobre as unidades de C2 (3.5.6). Para cada par (C1×C2, C1×C3, C2×C3) calcula-se a **porcentagem de
  repositórios que mudaram de categoria** e o **kappa de Cohen ponderado linear**
  (`sklearn.metrics.cohen_kappa_score(..., weights='linear')`; Cohen, 1968), que pesa menos
  uma troca entre categorias vizinhas do que uma troca entre extremos, por serem ordinais.

**Fator "tipo do projeto" na RQ 06 (Issue #69; decisão do grupo, 20/10/2026).** O guia prevê o
tipo como um dos fatores da RQ 06 e diz que ele é "rotulado manualmente". Os três autores escolheram a
opção de **rotular o tipo nos 330 repositórios, usando agentes de IA** em vez de rotulação manual.
Isso permite usar o fator com $n$ próximo de 330 (o $n$ de cada teste ainda varia com os valores nulos
de cada métrica), em vez de $n = 60$. Consequências a declarar no artigo:

* **Desvio do guia:** o tipo não é rotulado manualmente. Cada rótulo tem a origem marcada no dataset
  (`tipo_projeto_origem = agente`), e a origem deve constar também no artigo e nas ameaças à validade.
* **Referência para medir os agentes:** os rótulos de `tipo_projeto` da amostra-ouro servem de
  referência para medir a acurácia dos agentes nos 60 repositórios. Como a maior parte desses rótulos
  de referência também vem de IA (3.7), só os 30 repositórios com rótulo humano da Marcela dão
  referência humana; a acurácia contra os demais mede concordância entre IA e IA.
  `[PENDENTE: acurácia dos agentes, PR de tipo_projeto.]`
* **Ponto em aberto:** um dos autores pediu que os rótulos humanos dos 60 repositórios sejam
  **substituídos** pelos de agente (e não usados como referência); os outros entenderam a referência
  como validação. `[VERIFICAR: o grupo precisa fechar se os rótulos humanos servem de referência ou são substituídos.]`
* O escopo dos agentes para outras dimensões (`entrega_real`, `release_corretiva` fora da
  amostra-ouro) **não foi fechado**: a regra enunciada é que o que não sai de script confiável vai para
  agente, e o que sai de script vira script. Para `release_corretiva`, a heurística é justamente o
  objeto da avaliação (3.6), então rotulá-la com agente fora da amostra-ouro misturaria avaliador e
  avaliado. `[PENDENTE: escopo das dimensões rotuladas por agentes.]`
* Se a acurácia dos agentes for baixa, o fator tipo fica pouco confiável, e a hipótese 4 da RQ 06
  (`artigo_contexto_e_hipoteses.md`) deve ser tratada como exploratória.

### 3.9 Ameaças à validade e limitações conhecidas

Organizadas nas quatro categorias de Wohlin et al. (2012). Os itens com números vêm dos artefatos
versionados; o que depende de resultados futuros está marcado.

**Validade de construto: estamos medindo o que achamos que medimos?**

* **Release não é deploy.** Uma biblioteca que publica uma release por mês não "implanta" nada em
  produção; os usuários é que o fazem. A frequência de deploy mede cadência de publicação.
* **Falha de CI não é falha em produção.** O CFR (a) mede falhas do pipeline no default branch; o
  CFR (b) só captura falhas que motivam uma nova release corretiva em até 7 dias. As duas
  variantes medem coisas diferentes.
* **A heurística de release corretiva pode errar.** A `v1` usa só a mudança de *patch* e palavras no
  **assunto** do commit; a variante `v1_full_message` lê também o corpo da mensagem (3.6), o que pode
  acrescentar correspondências e também falsos positivos (`Fixes #123` ou `Revert` no corpo de commits
  de funcionalidade). Releases corretivas que mudam o *minor*
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
* **Motivos de valores nulos.** Um valor nulo nunca é imputado; o que muda é o tratamento na classificação
  (regra decidida em 20/10/2026, seção 3.5.5). Contagens do `repositorios.csv` versionado, anterior à regeneração:
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
    ignoradas). No preenchimento das colunas `cfr_b*` de 20/10/2026 (`dados/README.md`, seção 7.1),
    2 dos 330 repositórios têm `cfr_b` nulo (`Alishahryar1/free-claude-code` e `expo/expo`).
    `[PENDENTE: recontar os nulos de cfr_b depois da regeneração do dataset (#56).]`
  * **Tratamento na classificação:** recuperação nula sem nenhum episódio de falha vira **Elite**
    (15 repositórios); recuperação nula só com episódios censurados vira **Low** (3); lead time nulo
    não tem faixa e sai da nota geral (3 métricas); `cfr_a` nunca é nulo; `cfr_b` fica fora da nota
    (3.5.5). O `repositorios.csv` versionado ainda reflete a regra antiga (nulo → `Low`).
* **Janela e dia 30/09.** A primeira coleta lia o fim da janela como 30/09/2026 às 00:00Z e deixava o
  último dia de fora (janela de 364 dias). A decisão do grupo (20/10/2026) é incluir o dia inteiro
  (365 dias), mas a **seleção dos 330 repositórios e o sorteio da amostra-ouro foram feitos com a
  janela antiga** e não são refeitos: é um desvio documentado (3.2). Uma estimativa offline indica
  que o dia omitido corresponderia a cerca de 0,36% das releases e 0,32% dos runs.

**Validade interna: há fatores não controlados?**

* Repositórios mais antigos ou maiores têm, em geral, mais releases e runs, o que pode confundir
  as associações da RQ 06 (exemplo do guia). Sem controle estatístico de covariáveis, as associações
  são descritivas.
* A coleta foi feita em dois momentos (10/10 e 14/10/2026), e a Search API e as contagens mudam no
  tempo; a regeneração (#56) recoleta os mesmos 330 repositórios em outra data, e as contagens podem
  diferir das da primeira coleta (`dados/README.md`, seção 7).
* **Truncamento de *workflow runs* (limite residual).** Na primeira coleta, a divisão adaptativa tinha
  profundidade máxima 3 e intervalos mínimos de 2 dias, e um intervalo ainda com `total_count ≥ 1.000`
  era lido só até 1.000 runs, sem marca no dataset; uma estimativa offline detectou esse efeito em 21
  dos 330 repositórios (6,4%) (`docs/impacto_limitacoes_conhecidas.md`, seção 5). Por decisão do grupo
  (20/10/2026), a coleta passou a dividir recursivamente, sem piso de profundidade nem de dias, até
  `total_count < 1.000` ou intervalo de 1 segundo, e o dataset será regenerado assim. **Resta um
  limite residual:** se um intervalo de 1 segundo ainda tiver `total_count ≥ 1.000`, o filtro
  `created` não consegue separá-lo e só os 1.000 primeiros runs são lidos. Como não há coluna de
  sinalização no dataset (decisão do grupo), esse caso, que se espera raríssimo, não é identificável
  depois da coleta, apenas pelo aviso no log. `[PENDENTE: número de repositórios com intervalo irredutível na regeneração (#56), a partir dos avisos do log.]`
* **A correção do clone mudou os resultados.** Antes de buscar todas as tags, 5.289 das releases da
  janela (20,6%) eram descartadas como `not_found` (`--single-branch` trazia só as tags alcançáveis a
  partir do default branch, e não as de ramos de manutenção); depois da correção, resta **1**. O lead time passou de 269 para 329 repositórios com valor,
  a mediana de (a) foi de 6,91 para 10,35 dias e a de (b), de 6,07 para 11,97 dias; 23 dos 269 repositórios
  que já tinham valor mudaram de faixa de lead time. Isso mostra a sensibilidade das métricas à
  coleta. `[PENDENTE: o repositorios.csv/.parquet versionado ainda é anterior a essa correção (61 repositórios com lead time nulo no CSV; 1 depois da correção). Regerar o dataset (#56) antes de reportar qualquer valor de lead time.]`
* **Nota histórica: só o assunto do commit.** A primeira coleta guardava apenas o assunto da mensagem
  (`git log --format=%s`), por padrão e sem decisão consciente (confirmado pelo autor da heurística,
  20/10/2026). Uma estimativa offline mostrou que 3.152 das 21.065 decisões do CFR (b) (15%), em 152
  repositórios, poderiam mudar com a mensagem completa, sempre de "não corretiva" para "corretiva"
  (`docs/impacto_limitacoes_conhecidas.md`, seção 6). Por decisão do grupo, a regeneração coleta a
  mensagem completa (`%B`) e a variante `v1_full_message` é avaliada ao lado da `v1`, cujo padrão
  não muda. `[PENDENTE: efeito real na precisão e no recall (#62).]`
* **Rótulos produzidos por IA (validação manual e tipo do projeto).** Os rótulos da amostra-ouro vêm,
  na maior parte, de um avaliador LLM (3.7), e os de `tipo_projeto` dos 330 repositórios vêm de agentes
  (3.8). Erros sistemáticos do modelo podem se repetir nas três vagas e no consenso, e não aparecem no
  kappa. O mesmo assistente que implementou a `v1` produziu a vaga `gabriel`, o que aproxima os rótulos
  da regra da heurística e pode inflar o F1 da `v1`. Os 150 rótulos humanos da Marcela são a única
  referência humana.

**Validade externa: os resultados valem além da amostra?**

* A amostra contém apenas projetos **muito populares** (mínimo de 38.855 estrelas), open-source, que
  usam GitHub Actions e têm ao menos 5 releases e 50 runs na janela. Isso exclui projetos pequenos,
  corporativos/fechados e os que usam outras plataformas de CI; há viés de sobrevivência para projetos
  que publicam releases no GitHub.
* A janela é única (12 meses) e a distribuição de linguagens é concentrada (TypeScript, Python, Go,
  Rust e JavaScript somam 268 dos 330 repositórios).
* A amostra-ouro tem 60 repositórios e 300 releases, o que limita a generalização do F1 da heurística,
  e seus rótulos vêm, na maior parte, de um avaliador LLM (3.7), o que limita ainda mais o que o F1
  diz sobre o julgamento humano.

**Validade de conclusão: a análise estatística é adequada?**

* **Comparações múltiplas** (RQ 06: ≥ 3 fatores × 4 métricas = ≥ 12 testes) tratadas com Holm; os
  tamanhos de efeito acompanham os p-valores.
* **Subgrupos pequenos.** Alguns grupos (linguagens raras e, no tipo do projeto, a categoria
  biblioteca/framework, estimada em ~38 dos 330 a partir dos 7 de 60 rotulados antes) têm poucos
  repositórios. `[PENDENTE: tamanhos de grupo reais depois da rotulação do tipo nos 330 (3.8).]`
* **Dependência entre observações.** As 5 releases sorteadas de cada repositório não são
  independentes entre si, e o kappa e o F1 as tratam como observações separadas; o efeito de
  agrupamento não é corrigido.
* **Ajuste da heurística à própria amostra-ouro.** As mesmas 300 releases guiam o refinamento e medem o F1;
  a regra de "mudança justificada por regra geral" mitiga, mas não elimina, o ajuste excessivo.
  `[PENDENTE: avaliar se parte dos repositórios será reservada para a avaliação final (opção prevista em docs/avaliacao_heuristica.md).]`
* **Kappa sem variabilidade.** Se as categorias quase não variam (por exemplo, quase todo repositório
  com `entrega_real = sim`), o kappa fica instável ou indefinido, mesmo com alta concordância
  percentual. `[PENDENTE: kappas reais (#65).]`
* **Kappa entre execuções de um mesmo modelo.** O kappa de Fleiss da amostra-ouro mede concordância
  entre execuções de um avaliador LLM (mais as 150 linhas humanas da Marcela), com erros
  correlacionados que o inflam; ele não mede a ambiguidade do critério para humanos (3.7). O consenso é
  mecânico, sem reunião.
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
grupo. As dependências ficam travadas em `uv.lock` (`uv sync --frozen` no CI). O projeto declara
Python ≥ 3.12 (`requires-python`), mas o dataset foi gerado com **Python 3.14**, a versão fixada em
`.python-version` (confirmado pelo autor responsável pela coleta, 20/10/2026). O dicionário de dados
completo está em `lab03/dados/README.md`.
`[PENDENTE: alinhar o README e a seção 7 do dicionário de dados, que ainda citam Python 3.12, à versão 3.14 (fora do escopo desta edição, que só altera este rascunho).]`

`dados/releases/` e `dados/releases_c2/` (cerca de 320 MB, segundo o dicionário de dados e o
relatório da Sprint 02; um arquivo passa de 100 MB) **não** são versionados (`.gitignore`).
`releases/` pode ser regenerado por `uv run python -m pipeline.persist_releases --config config.yaml`,
que precisa de rede e levou cerca de 10 a 12 minutos para os 330 repositórios (o dicionário de dados
diz cerca de 10; o relatório da Sprint 02, cerca de 12). Esse comando **não** gera `releases_c2/`
nem `tags/`: eles só são escritos pelo pipeline completo (`python -m pipeline --clean`), que refaz a
busca de candidatos a partir do estado atual do GitHub e, sozinho, não preserva os 330 repositórios
congelados (`dados/README.md`, seção 7).
`[PENDENTE: procedimento de regeneração que recoleta os mesmos 330 com as regras decididas em 20/10/2026 (#56).]` `dados/tags/` também não consta entre
os arquivos versionados hoje.

Os `runs/` versionados bastam para recalcular, sem rede, `cfr_a`, `recovery_hours` e
`censored_episodes_ratio`. O lead time e o CFR (b) dependem de `releases/`, que precisa ser
regenerado. O `repositorios.csv`/`.parquet` versionado tem as 38 colunas do dicionário de dados, mas
as 24 primeiras são da coleta original, as 6 colunas `cfr_b*` foram preenchidas por *backfill* em
20/10/2026 (`dados/README.md`, seção 7.1) e as 8 de pré-releases, tags, C2 e C3 estão nulas; o lead
time é anterior à correção do clone (seção 3.4), e as faixas seguem a regra antiga de nulos. Ele só
fica consistente com as regras decididas depois da regeneração (#56).

*Arquivos órfãos em `runs/`.* `dados/runs/` tem 333 arquivos para 330 repositórios:
`elastic__elasticsearch`, `home-assistant__core` e `ueberdosis__tiptap` não constam em
`repositorios.csv`. Por decisão do grupo (20/10/2026), esses **3 arquivos órfãos são removidos do
versionamento**, o que deixa `runs/` com um arquivo por repositório aceito. O motivo de terem sido
descartados não é conhecido (a hipótese de descarte depois da coleta de runs, já que o orquestrador
grava `runs/` antes da etapa de clone, não foi verificada).
`[PENDENTE: remoção efetiva dos 3 arquivos (git rm), ainda presentes em 21/10/2026; como --clean não apaga runs/, ela precisa ser explícita no ciclo de regeneração (#56).]`

Como a coleta lê o estado do GitHub no momento da execução (Search API, contagens, releases, tags e
runs mudam com o tempo) e o cache HTTP não é versionado, uma replicação reproduz o método, e não
necessariamente os mesmos valores (seção 3.2). A replicação cruzada é relatada em seção própria.
`[PENDENTE: link final do repositório e do GitHub Projects no artigo; o link do projeto no Overleaf (#48) já consta em lab03/README.md.]`

---

## Apêndice A. Lista de pendências para fechar a seção

Situação em 21/10/2026, depois da aplicação das decisões do grupo de 20/10/2026.

**A.1 Decidido (já refletido no texto; falta, quando indicado, aplicar no código ou nos dados).**

| # | Tema | Decisão | Onde entra | Falta |
|---|---|---|---|---|
| D1 | Janela | Definida pelo grupo em sala, sem registro escrito e sem confirmação do professor; fim em 30/09/2026 23:59:59Z (365 dias) | 3.2, 3.5.1, 3.6, 3.9 | mudar `config.yaml` e código, regenerar (#56) |
| D2 | Valores nulos | Recuperação sem falhas → Elite (15); só censurados → Low (3); lead time nulo fora da nota (3 métricas); `cfr_a` nunca nulo; `cfr_b` fora da nota | 3.5.5, 3.9 | recalcular faixas na regeneração (#56) |
| D3 | CFR (b) em C2 | Calculado sobre C2 (releases + pré-releases) na RQ 07 | 3.5.6, 3.8 | implementar `c2_cfr_b*` e gerar `releases_c2/` (#56) |
| D4 | Runs | Divisão recursiva sem piso de profundidade nem de dias; sem marcador; limite residual declarado | 3.4, 3.9 | regenerar `runs/` (#56) |
| D5 | Clone | Um filtro combinado (decisão); `tree:0` na prática, equivalente; mensagens completas (`%B`); `v1_full_message`; "só assunto" virou nota histórica | 3.4, 3.6, 3.9 | regenerar `releases/` com `full_message` (#56) |
| D6 | Python e datas | Python 3.14; coleta em 10/10/2026 (100) e 14/10/2026 (230) | 3.2, 3.10 | data da regeneração final; alinhar README e dicionário (3.12 → 3.14) |
| D7 | Funil | 753 / 697 / 382 / 332 / 330; primeira linha derivada | 3.3, Tabela 2 | nada (causa da diferença de 100 não afirmada) |
| D8 | Hipóteses | Confirmadas por João; Marcela e Gabriel não consultados | 3.1 | confirmação de Marcela e Gabriel |
| D9 | RQ 06 | Tipo rotulado nos 330 por agentes (`tipo_projeto_origem = agente`); desvio do guia | 3.8, 3.9 | acurácia dos agentes; PR de `tipo_projeto`; ponto em aberto sobre substituir rótulos humanos |
| D10 | Amostra-ouro | Vagas preenchidas por avaliador LLM; 150 linhas humanas da Marcela mantidas; consenso mecânico; desvio declarado | 3.7, 3.9 | PR com os rótulos das vagas `joao` e `marcela` (150 linhas) |
| D11 | Heurística | Aceitar `v1` se F1 ≥ 0,70; senão Gabriel escreve `heuristic_v2` (sem prazo); final = maior F1 | 3.6, 3.7 | avaliação (#62) |
| D12 | Arquivos órfãos | Remover os 3 `runs/` órfãos do versionamento | 3.3, 3.10 | `git rm` efetivo |
| D13 | Referências | marcadores `[REF]` trocados por citações; lista em "Referências" | todo o texto | verificar Romano (2006) e o ano do SemVer |

**A.2 Ainda em aberto.**

| # | Pendência | Onde entra | Fonte / responsável |
|---|---|---|---|
| 1 | Regenerar `repositorios.*`, `runs/` e `releases/` com todas as regras decididas e reconferir a caracterização da amostra | 3.2, 3.3, 3.9 | João (#56) |
| 2 | Data da regeneração final | 3.2 | João (#56) |
| 3 | Versionar as execuções de IA das vagas `joao` e `marcela` (150 linhas) e confirmar os percentuais de concordância citados | 3.7 | agente coordenador; PR de rótulos |
| 4 | Decidir se a vaga `gabriel` (independência parcial) é mantida ou refeita às cegas; como as linhas humanas e de IA da vaga `marcela` entram no kappa | 3.7 | grupo |
| 5 | Kappa de Fleiss real (3 dimensões), com a ressalva de execuções de um mesmo modelo | 3.7 | #65 |
| 6 | Consenso mecânico (`validacao/consenso.csv`) e registro de origem sem reunião | 3.7 | #65 |
| 7 | Precisão, recall e F1 por versão da heurística (`v1`, `v1_full_message`, v2); versão final | 3.6, 3.7 | #62; Gabriel |
| 8 | Acurácia dos agentes em `tipo_projeto`; substituir ou usar como referência os rótulos humanos; escopo das outras dimensões; tratamento de "outro" | 3.8 | grupo; PR de `tipo_projeto` |
| 9 | Resultados do CFR (b) em C2 | 3.5.6 | RQ 07 |
| 10 | Scripts e resultados das RQ 01 a 07 | 3.8 | Sprint 03 |
| 11 | RQ 08 (bônus): fazer ou não | 3.1 | grupo |
| 12 | Confirmação de Marcela e Gabriel sobre a ordem "hipótese antes dos dados" | 3.1 | Marcela; Gabriel |
| 13 | Romano et al. (2006): abrir o PDF e conferir; ano do SemVer | Referências | autores |
| 14 | Remoção dos 3 arquivos órfãos de `runs/` | 3.10 | João (#56) |
| 15 | Link final do repositório e do GitHub Projects no artigo | 3.10 | #48 |

## Apêndice B. Afirmação → arquivo de origem

Todos os caminhos são relativos a `lab03/`, salvo indicação.

| Afirmação | Arquivo |
|---|---|
| Janela 01/10/2025-30/09/2026 (em 21/10/2026 o `fim` ainda é lido como 00:00Z; a decisão de 20/10/2026 é fim do dia 23:59:59Z); `tamanho_final` 330; mín. 5 releases e 50 runs; faixas de estrelas; qualificadores de busca; heurística `v1` | `config.yaml` |
| 52,1 semanas; faixas de DF, lead time, CFR e recuperação; nota geral = mediana arredondada para baixo; regra de nulos (recuperação sem falhas → Elite, só censurados → Low, lead time nulo fora da nota) | `metricas/dora.py`; `dados/README.md` (seção 2) |
| Lead time (a) e (b); truncamento em 0; release sem commits e releases ignoradas | `metricas/lead_time.py` |
| CFR (a); classificação de `conclusion`; episódios, recuperação e censura | `metricas/stability.py` |
| CFR (b): horizonte de 7 dias; censurada, ignorada, sem falha, falha; heurística `v1`; regex de SemVer e palavras-chave; `HEURISTICS` | `metricas/cfr_b.py` |
| Datas convertidas para UTC; `"2026-09-30"` lido como meia-noite UTC (comportamento que a decisão de 20/10/2026 muda) | `metricas/schemas.py` |
| Busca fatiada por estrelas; deduplicação; máximo de 10 páginas por faixa | `pipeline/repo_selector.py` |
| Filtros na ordem Actions, releases, runs, clone; avaliação em ordem de estrelas; parada ao atingir a meta; classificação C1/C2/C3; colunas do registro | `pipeline/orchestrator.py` |
| Estrutura das linhas do funil | `pipeline/funnel.py`; `dados/funil.csv` |
| Etapas do funil, critério dos 330, primeira linha derivada (aceitos + descartes) e correção da Issue #66 | `docs/criterios_selecao_e_funil.md` |
| Contagens do funil (753, 697, 382, 332, 330; descartes 56, 315, 50, 2) | `dados/funil.csv` |
| Caracterização da amostra (estrelas, linguagens, releases, runs, datas); 38 colunas, 8 nulas; 61 lead times nulos e 18 recuperações nulas | `dados/repositorios.csv` |
| Consulta GraphQL (campos coletados, ordenação, paginação) | `pipeline/graphql/queries/repo_details.graphql`; `pipeline/releases.py` |
| Contagem de contribuidores por cabeçalho `Link` | `pipeline/metadata.py` |
| Coleta de runs: filtros, divisão mensal, divisão recursiva sem piso de profundidade nem de dias (teto 1.000; intervalo mínimo de 1 s; caso residual com aviso), deduplicação por `id` | `pipeline/workflow_runs.py`; `dados/README.md` (seção 4) |
| Clone *bare*, filtro `tree:0` (equivalente ao combinado; o GitHub rejeita `combine`), `fetch` de todas as tags, fallback com token, `git log` com `%aI`, `%s` e `%B`, `for-each-ref` das tags | `pipeline/git_clone.py`; `dados/README.md` (seção 5) |
| Alternativa via REST `compare` (paginação, 404, status `ok`/`first_release`/`not_found`) | `pipeline/commits.py` |
| Âncora, janela, pré-releases, descarte de rascunhos | `pipeline/releases.py` |
| Rate limit, rotação de tokens, *backoff* exponencial, concorrência | `pipeline/http_client.py` |
| Cache SQLite em modo WAL | `pipeline/cache.py` |
| Retomada, checkpoint incremental, comando único, `--limit`, `--clean` | `README.md`; `pipeline/__main__.py`; `pipeline/orchestrator.py` |
| Dicionário de dados, colunas `cfr_b*`, regras de C1/C2/C3, regeneração do dataset, CSV versionado anterior às colunas novas | `dados/README.md` |
| Motivos de lead time nulo; 5.289 → 1 `not_found`; medianas antes e depois; LT(b) > LT(a); predecessora de outra linha (2.649 releases, 120 repositórios); `expo/expo` | `docs/investigacao_lead_time.md`; `dados/analises/lead_time_diagnostico.csv` |
| Decisão pelo operador E na heurística; contexto da Sprint 02 | `docs/relatorio_sprint2_gabriel_assis.md` |
| Heurísticas `v1` e `v1_full_message`; `DEFAULT_HEURISTIC` | `metricas/cfr_b.py`; `dados/README.md` (seção 5) |
| Sorteio de 60 repositórios (semente 42) e 5 releases por repositório; 300 linhas; lista de repositórios | `analises/amostra_ouro.py`; `dados/amostra_ouro/sorteio_info.json` |
| Dimensões, unidades de análise, kappa de Fleiss, Landis & Koch, consenso e desempate, formato dos arquivos | `docs/protocolo_consenso.md`; `analises/concordancia.py` |
| Precisão/recall/F1, exclusões, meta F1 ≥ 0,70, regra de decisão e versões | `docs/avaliacao_heuristica.md`; `analises/avaliar_heuristica.py` |
| Existem `rotulos_joao.csv` (IA), `rotulos_gabriel.csv` (IA) e `rotulos_marcela.csv` (150 linhas humanas + 150 de IA); falta `consenso.csv`; proveniência de cada arquivo; confiabilidade entre execuções de IA e aviso de validade | `validacao/` (listagem); `validacao/PROVENIENCIA.md`; `docs/confiabilidade_execucoes_ia.md`; `docs/protocolo_consenso.md` (seção 6) |
| Plano estatístico (Spearman, Kruskal-Wallis, Mann-Whitney, Holm, ε², Cliff's δ, κ ponderado), definições operacionais, validação manual | `guialab03.md` |
| Opções (a), (b) e (c) para o fator "tipo do projeto" e evidência de poder estatístico | Issue #69 (GitHub); `docs/decisao_rq06_tipo_projeto.md` |
| Impacto estimado da janela, dos nulos, do truncamento de runs e do assunto do commit | `docs/impacto_limitacoes_conhecidas.md` |
| Sorteio da amostra-ouro completado em 20/10/2026 e linhas inválidas da Marcela | `docs/amostra_ouro.md`; `validacao/historico/marcela_linhas_invalidas.csv` |
| Python 3.14 | `.python-version` |
| Decisões do grupo de 20/10/2026 (janela, nulos, CFR (b) em C2, runs, clone, funil, RQ 06, validação manual, heurística) | registro das entrevistas com os autores, fora do repositório |
| Divisão da escrita da metodologia | Issue #68 (GitHub) |
| Hipóteses informais por RQ | `artigo_contexto_e_hipoteses.md`; `docs/hipoteses_rq02_rq03_rq05.md`; `docs/hipoteses_rq04_rq07.md` |
| CI do grupo e cobertura mínima de 80% | `../.github/workflows/testes-lab03.yml`; `README.md` |

## Referências

Formato adaptado da ABNT, a partir de `referencias_metodologia.bib` e `referencias_metodologia.md`
(verificação feita em 20/10/2026 em Crossref, JSTOR ou fonte indicada). Dependem de checagem dos
autores apenas os itens marcados com `[VERIFICAR]`.

* CLIFF, N. Dominance statistics: ordinal analyses to answer ordinal questions. *Psychological Bulletin*, v. 114, n. 3, p. 494-509, 1993. DOI: 10.1037/0033-2909.114.3.494.
* COHEN, J. Weighted kappa: nominal scale agreement provision for scaled disagreement or partial credit. *Psychological Bulletin*, v. 70, n. 4, p. 213-220, 1968. DOI: 10.1037/h0026256.
* DORA. *Accelerate State of DevOps Report 2024*. Google Cloud, 2024. Disponível em: <https://dora.dev/research/2024/>. Acesso em: 20 out. 2026.
* FLEISS, J. L. Measuring nominal scale agreement among many raters. *Psychological Bulletin*, v. 76, n. 5, p. 378-382, 1971. DOI: 10.1037/h0031619.
* FORSGREN, N.; HUMBLE, J.; KIM, G. *Accelerate: the science of lean software and DevOps: building and scaling high performing technology organizations*. IT Revolution Press, 2018. ISBN 978-1-942788-33-1.
* HARVEY, N. DORA's software delivery performance metrics. DORA, Google Cloud, [s.d.]. Disponível em: <https://dora.dev/guides/dora-metrics-four-keys/>. Acesso em: 20 out. 2026. (A página não traz data e hoje descreve cinco métricas; ver 3.1.)
* HOLM, S. A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, v. 6, n. 2, p. 65-70, 1979. Disponível em: <https://www.jstor.org/stable/4615733>. (Sem DOI registrado.)
* KRUSKAL, W. H.; WALLIS, W. A. Use of ranks in one-criterion variance analysis. *Journal of the American Statistical Association*, v. 47, n. 260, p. 583-621, 1952. DOI: 10.1080/01621459.1952.10483441.
* LANDIS, J. R.; KOCH, G. G. The measurement of observer agreement for categorical data. *Biometrics*, v. 33, n. 1, p. 159-174, 1977. DOI: 10.2307/2529310.
* MANN, H. B.; WHITNEY, D. R. On a test of whether one of two random variables is stochastically larger than the other. *The Annals of Mathematical Statistics*, v. 18, n. 1, p. 50-60, 1947. DOI: 10.1214/aoms/1177730491.
* PRESTON-WERNER, T. *Semantic Versioning 2.0.0*. [s.d.]. Disponível em: <https://semver.org/lang/pt-BR/>. Acesso em: 20 out. 2026. `[VERIFICAR: ano da versão 2.0.0 não verificado; confirmar no repositório semver/semver ou manter [s.d.].]`
* ROMANO, J.; KROMREY, J. D.; CORAGGIO, J.; SKOWRONEK, J. Appropriate statistics for ordinal level data: should we really be using t-test and Cohen's d for evaluating group differences on the NSSE and other surveys? In: ANNUAL MEETING OF THE FLORIDA ASSOCIATION OF INSTITUTIONAL RESEARCH, 2006. `[VERIFICAR: conferido só em fontes secundárias (documentação do pacote CRAN effsize e ResearchGate); o PDF original não foi aberto. Faltam prenomes completos, local do evento e páginas, e há indício de uma segunda versão do trabalho com título diferente e quinto autor (Devine). Conferir antes de submeter.]`
* SPEARMAN, C. The proof and measurement of association between two things. *The American Journal of Psychology*, v. 15, n. 1, p. 72-101, 1904. DOI: 10.2307/1412159.
* TOMCZAK, M.; TOMCZAK, E. The need to report effect size estimates revisited: an overview of some recommended measures of effect size. *Trends in Sport Sciences*, v. 21, n. 1, p. 19-25, 2014.
* WOHLIN, C.; RUNESON, P.; HÖST, M.; OHLSSON, M. C.; REGNELL, B.; WESSLÉN, A. *Experimentation in software engineering*. Berlin, Heidelberg: Springer, 2012. DOI: 10.1007/978-3-642-29044-2.

`statsmodels`, `scikit-learn` e `scipy` são citados por nome no texto; suas referências não foram
buscadas (`referencias_metodologia.md`, seção 4).

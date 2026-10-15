# Investigação: repositórios sem lead time e casos LT(b) > LT(a) (Issue #60)

**Responsável:** Gabriel Assis de Souza (@GabriAssiss)
**Base:** amostra final de 330 repositórios (`dados/repositorios.parquet`, #53)
**Script:** `analises/investigar_lead_time.py`
**Saída por repositório:** `dados/analises/lead_time_diagnostico.csv`

## 1. Pergunta

No dataset da S01, 23 de 100 repositórios tinham lead time nulo e 28 tinham
LT(b) > LT(a). Na base de 330 repositórios os números foram **61 nulos** e
**86 casos LT(b) > LT(a)**. A Issue pede duas coisas:

1. classificar e contar os motivos dos nulos;
2. confirmar que LT(b) > LT(a) não é bug, verificando à mão pelo menos 3 casos.

## 2. Como reproduzir

```bash
# 1. Persistir releases e commits por release dos repositórios aceitos (#58)
uv run python -m pipeline.persist_releases --config config.yaml
# 2. Rodar o diagnóstico
uv run python -m analises.investigar_lead_time
```

O script recalcula o lead time com as mesmas funções do pipeline
(`metricas.lead_time.calculate_lead_time`), a partir do `status` gravado para
cada release em `dados/releases/` (`ok`, `first_release` ou `not_found`).

Para reproduzir o cenário **antes** da correção da seção 3, basta rodar o passo
1 no commit `360e3fd` (antes de `287ac2b`). Essa execução reproduziu
exatamente os números do dataset original (61 nulos e 86 inversões), o que
confirma que o script e o pipeline calculam a mesma coisa.

## 3. Motivos dos nulos: era bug

### 3.1 Diagnóstico

| Status das releases da janela (330 repositórios) | Antes da correção | Depois da correção |
|---|---:|---:|
| `ok` com commits novos | 16.660 | 21.835 |
| `ok` sem commits novos | 3.722 | 3.835 |
| `first_release` (primeira release da história) | 61 | 61 |
| `not_found` (tag não encontrada, equivalente ao 404) | **5.289** | **1** |

| Motivo do lead time nulo | Antes | Depois |
|---|---:|---:|
| Todas as releases com tag não encontrada | 59 | 0 |
| Tag não encontrada + releases sem commits novos | 1 | 1 |
| Primeira release da história + tag não encontrada | 1 | 0 |
| Falha de clone/coleta | 0 | 0 |
| **Total** | **61** | **1** |

Antes da correção, **20,6%** das releases da janela (5.289) eram descartadas
como `not_found`. A causa não era tag apagada ou reescrita, que é o caso
previsto no guia: era o clone. Desde a #47, o pipeline usa
`git clone --bare --filter=tree:0 --single-branch`, e o `--single-branch` só
traz as tags alcançáveis a partir do default branch. Projetos que publicam
releases a partir de branches de manutenção (por exemplo, `react/react`, com as
linhas `v19.0.x`, `v19.1.x` e `v19.2.x`) tinham quase todas as tags ausentes no
clone, e o `git log anterior..atual` falhava.

O exemplo mais claro é o `react/react`: das 28 releases da janela, só 1
(`eslint-plugin-react-hooks@7.1.1`) tinha commits. O lead time de 11,4 h do
dataset vinha dessa **única release**, que nem é do React.

### 3.2 Correção (commit `287ac2b`)

Depois do clone, `pipeline/git_clone.py` roda
`git fetch --filter=tree:0 origin +refs/tags/*:refs/tags/*`. Isso traz todas as
tags e os commits dos branches de manutenção, ainda sem árvores nem blobs, sem
consumir cota da API. Se o fetch falhar, o clone continua utilizável e o
comportamento volta a ser o anterior (com aviso no log).

Com a correção, 60 dos 61 repositórios passam a ter lead time. O único nulo
restante é o `expo/expo`: 145 das 146 releases da janela não têm commits novos
em relação à anterior e 1 tem tag não encontrada. É um monorepo que publica
várias releases de pacotes no mesmo commit, então o nulo é legítimo.

### 3.3 Impacto nos valores

| | n antes | n depois | Mediana antes (dias) | Mediana depois (dias) | IQR depois (dias) |
|---|---:|---:|---:|---:|---|
| LT (a) | 269 | 329 | 6,91 | 10,35 | 3,15 – 39,21 |
| LT (b) | 269 | 329 | 6,07 | 11,97 | 3,38 – 54,92 |

Dos 269 repositórios que já tinham lead time, 110 mudaram de valor e **23
mudaram de faixa DORA** de lead time. Por isso, as colunas `lead_time_*` de
`dados/repositorios.csv` precisam ser recalculadas com o pipeline corrigido na
consolidação do dataset final (#56).

## 4. LT(b) > LT(a): legítimo, não é bug

### 4.1 Por que pode acontecer

Dentro de **uma** release, LT(b) ≤ LT(a) sempre, porque o commit mais antigo
define LT(a) e todo outro commit é mais novo. Entre releases isso deixa de
valer: (a) é a mediana **por release**, em que cada release pesa 1, e (b) é a
mediana de **todos os commits**, em que cada release pesa pelo seu número de
commits. Quando uma release grande e demorada (uma versão *major*, por exemplo)
convive com várias releases pequenas e rápidas, ela domina a mediana de (b) e
quase não afeta a de (a).

### 4.2 Verificação automática

O script confere o invariante por release em **todos** os commits de todas as
releases: nenhum commit pode ter lead time maior que o LT(a) da própria
release. Resultado: **0 violações**, tanto antes quanto depois da correção.

Depois da correção, 138 repositórios têm LT(b) > LT(a). Nesses casos, a maior
release concentra em mediana 25% dos commits do repositório.

### 4.3 Verificação manual (4 casos)

Os quatro casos com maior concentração de commits numa única release foram
conferidos release a release (tabela impressa pelo script com `--exemplos 4`:
commits, LT(a) e mediana de LT(b) de cada release). Em todos, a inversão vem
de uma versão *major* que acumulou meses de trabalho, seguida de *patches*
rápidos.

| Repositório | LT(a) | LT(b) | Release dominante | Commits da dominante / total |
|---|---:|---:|---|---:|
| `pandas-dev/pandas` | 40,2 d | 448,8 d | `v3.0.0` | 3.037 / 3.191 |
| `charmbracelet/bubbletea` | 6,1 d | 335,9 d | `v2.0.0` | 759 / 817 |
| `huginn/huginn` | 9,6 d | 311,7 d | `v2026.08.27` | 667 / 740 |
| `gogs/gogs` | 20,1 d | 405,2 d | `v0.14.0` | 308 / 361 |

Exemplo (`charmbracelet/bubbletea`): `v2.0.0` tem 759 commits com mediana de
377 dias até a publicação. As outras 10 releases (`v2.0.1` a `v2.0.10`) têm de
1 a 23 commits cada, com LT(a) entre 0 e 42 dias. A mediana de (a) é a de 11
releases, então cai numa release pequena (6,1 dias). A de (b) é a de 817
commits, dos quais 759 são da `v2.0.0`, e cai dentro dela (335,9 dias).
É o efeito descrito pelo guia ao contrário: aqui é a **variante (b)** que
explode por causa de uma release grande, e não a (a) por causa de um commit
esquecido.

## 5. Achado colateral: predecessora de outra linha de manutenção

Com todas as tags disponíveis, aparece um problema de construto. Seguindo o
guia, a release anterior de R é a release publicada imediatamente antes de R.
Em projetos com várias linhas de manutenção, essa predecessora pode estar em
outra linha. No `react/react`, `v19.0.1` é comparada com `v19.2.0`, e
`v19.2.1` com `v19.1.2`. O `git log` entre linhas diferentes conta commits que
a release nunca "entregou" de novo. No caso extremo, `ClickHouse/ClickHouse`
tem releases com mais de 60 mil commits comparadas a uma predecessora LTS.

| Indicador | Valor |
|---|---:|
| Releases cuja predecessora tem SemVer maior | 2.649 |
| Repositórios afetados | 120 |
| ... deles com LT(b) > LT(a) | 69 |

O indicador é um limite superior: em monorepos, tags de pacotes diferentes
(`pkg-a@2.0.0` seguida de `pkg-b@1.3.0`) também contam.

**Decisão:** manter a definição do guia (predecessora cronológica), que é
comum à turma e necessária para a replicação cruzada, e registrar o efeito
como **ameaça à validade de construto** do lead time. Uma variante "por
linha" (predecessora = maior release anterior com SemVer menor) pode entrar
na análise de sensibilidade se o grupo quiser.

## 6. Observação sobre os arquivos de releases

`dados/releases/` ocupa cerca de 320 MB para os 330 repositórios, e só o
arquivo do `ClickHouse/ClickHouse` tem 125 MB, acima do limite de 100 MB por
arquivo do GitHub. Por isso o diretório não é versionado (`.gitignore`). Ele
é regenerado em cerca de 10 minutos pelo comando da seção 2, sem gastar cota
da API além de uma consulta GraphQL por repositório, que fica no cache. O
diagnóstico por repositório (`dados/analises/lead_time_diagnostico.csv`) é
versionado.

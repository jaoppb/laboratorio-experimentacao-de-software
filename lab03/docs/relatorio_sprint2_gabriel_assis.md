# Relatório individual — Lab03S02

**Integrante:** Gabriel Assis de Souza (@GabriAssiss)
**Sprint:** Lab03S02 — amostra completa, métricas em todas as variantes e validação manual
**Papel na divisão sugerida do guia:** integrante **B** (implementação e
refinamento da heurística de release corretiva, CFR b, a partir da validação),
além da rotulação independente da amostra-ouro

## 1. Escopo

| Issue | Título | Situação | Artefato |
|---|---|---|---|
| #58 | Persistir releases e commits por release | Concluída | `pipeline/releases.py`, `pipeline/orchestrator.py`, `pipeline/persist_releases.py`, `dados/README.md`, testes |
| #59 | CFR (b) e heurística de release corretiva (funções + testes) | Concluída | `metricas/cfr_b.py`, `tests/test_cfr_b.py` |
| #60 | Investigar repositórios sem lead time e casos LT(b) > LT(a) | Concluída | `pipeline/git_clone.py` (correção), `analises/investigar_lead_time.py`, `docs/investigacao_lead_time.md`, `dados/analises/lead_time_diagnostico.csv` |
| #61 | Rotular amostra-ouro (Gabriel) | Aguardando a #63 | `validacao/rotulos_gabriel.csv` (a fazer) |
| #62 | Avaliar heurística contra o consenso (P, R, F1) | Aguardando #61 e #65 | — |
| #68 | Seção de Metodologia no artigo (parte do Gabriel) | Em andamento | — |
| #69 | Decidir os fatores da RQ 06 | Decisão de grupo | — |

Commits desta sprint, todos referenciando a Issue:

| Commit | Mensagem |
|---|---|
| `0ebe021` | #59 implement corrective release heuristic v1 and CFR (b) with tests |
| `360e3fd` | #58 persist main-definition releases with comparison status and add backfill command |
| `287ac2b` | #60 fetch tags from all branches so maintenance releases are not skipped as not found |
| `533302f` | #58 keep persisted releases out of git and document how to regenerate them |
| `30a551c` | #60 diagnose null lead times and LT(b) > LT(a) cases on the 330-repository sample |

## 2. #58 — Releases e commits por release persistidos

Na S01, as mensagens de commit só existiam no cache HTTP. Na #54, o João
passou a gravar `dados/releases/` com as releases e pré-releases (C2). Faltavam
três coisas para destravar a planilha de rotulação (#63) e a heurística:

1. **Definição principal (C1).** O CFR (b), o lead time de referência e a
   amostra-ouro usam releases sem pré-releases. Os commits de uma release mudam
   quando há pré-releases entre ela e a anterior, então C1 não pode ser
   derivada do arquivo C2. Agora o orquestrador grava:
   - `dados/releases/`: C1 (definição principal);
   - `dados/releases_c2/`: C2 (variante da RQ 07), no mesmo esquema.
2. **Status da comparação.** Nova coluna `status` (`ok`, `first_release` ou
   `not_found`). Sem ela, uma release ignorada por 404 era indistinguível de
   uma release sem commits novos. Agora `commits_count` é nulo quando a
   comparação não foi feita e `0` só quando realmente não há commits novos.
3. **Repositórios já aceitos.** O orquestrador só grava releases dos
   repositórios que aceita na execução corrente, e os 330 da amostra (#53)
   foram coletados antes disso. O comando novo
   `uv run python -m pipeline.persist_releases --config config.yaml` lê
   `dados/repositorios.parquet` e preenche `dados/releases/` com as mesmas
   funções do pipeline: releases via GraphQL e commits via clone *blobless*.
   Ele roda com 4 *workers*, pula repositórios que já têm arquivo (retomada) e
   lista as falhas no final.

**Execução na amostra completa:** 330 de 330 repositórios, 0 falhas, 25.732
releases da janela, em cerca de 12 minutos.

Os arquivos ocupam cerca de 320 MB, e o do `ClickHouse/ClickHouse` sozinho tem
125 MB, acima do limite de 100 MB por arquivo do GitHub. Por isso
`dados/releases/` e `dados/releases_c2/` ficam no `.gitignore` e o dicionário
de dados explica como regenerá-los. O esquema completo está na seção 5 de
`dados/README.md`.

## 3. #59 — Heurística de release corretiva e CFR (b) (`metricas/cfr_b.py`)

### 3.1 Heurística v1

Uma release é **corretiva** quando **só o *patch* muda** no SemVer **e** pelo
menos um dos seus commits menciona `revert`, `hotfix` ou `fix` (palavra
inteira, sem diferenciar maiúsculas: inclui `fix(scope):`, `Fixes #123` e
`bugfix`).

- `parse_semver(tag)` extrai `(major, minor, patch)` aceitando prefixos (`v`,
  `release-`, `@scope/pkg@`) e sufixos de pré-release ou *build* (`-rc.1`,
  `+build.5`). `v1.2` vira `(1, 2, 0)`. Tags como `nightly` ou `1.2.3.4` não são
  SemVer.
- `is_patch_bump(anterior, atual)` devolve `None` quando uma das tags está fora
  do SemVer. Nesse caso, a v1 decide **só pelas mensagens**.
- Escolhi o **E** em vez do **OU** que o guia também sugere porque quase toda
  release tem algum commit com "fix". O OU marcaria como corretivas as
  releases *minor* comuns e derrubaria a precisão. A escolha será confrontada
  com o consenso na #62.
- As versões ficam num registro (`HEURISTICS = {"v1": ...}`), para que a #62
  avalie cada versão e a tabela de P/R/F1 do artigo aponte a versão final que
  vai para o pipeline (#55).

### 3.2 CFR (b)

`calculate_cfr_b(pares, window_end, version="v1")` recebe as releases da janela
com seus commits e classifica cada uma:

| Situação | Resultado | Entra no denominador? |
|---|---|---|
| Publicada nos últimos 7 dias da janela | `censored` | Não (censura do guia) |
| Próxima release em até 7 dias **e** corretiva pela heurística | `failed` | Sim |
| Próxima release em até 7 dias, mas com commits desconhecidos (404) | `skipped` | Não |
| Sem próxima release, ou próxima depois de 7 dias, ou não corretiva | `ok` | Sim |

CFR (b) = `failed / (failed + ok)`, ou `None` quando nenhuma release pode ser
avaliada. O resultado traz as contagens de avaliadas, censuradas e puladas, que
a #55 exporta, e a faixa DORA (reaproveitando
`classify_change_failure_rate` de `metricas/dora.py`).

Decisões:

- **Só a release imediatamente seguinte** é considerada. Uma correção visa a
  release mais recente. Se `2.3.1` e `2.3.2` vierem em sequência, `2.3.0` e
  `2.3.1` falham.
- **Exatamente 7 dias** ainda conta como falha ("em até 7 dias").
- **Release única** fora dos últimos 7 dias: avaliada e não falhou (CFR = 0).

### 3.3 Testes (`tests/test_cfr_b.py`, 39 testes)

- Exemplos do guia como *fixture*: `v2.3.0 → v2.3.1` falhou e
  `v2.4.0 → v2.5.0` não falhou (CFR = 1/4, faixa High).
- Casos de borda pedidos na Issue: tag fora de SemVer (decide pelas mensagens),
  repositório com uma única release e release censurada.
- Também: correção com 7 dias + 1 segundo (não conta) e com exatamente 7 dias
  (conta), próxima release com 404 (`skipped`), entrada fora de ordem, entrada
  vazia, só releases censuradas (`None`) e versão inexistente da heurística.

## 4. #60 — Repositórios sem lead time e LT(b) > LT(a)

Detalhes em `docs/investigacao_lead_time.md`. Resumo:

### 4.1 Os nulos eram bug, e foi corrigido

Na base de 330 repositórios, 61 tinham lead time nulo. O diagnóstico mostrou
que **20,6% das releases da janela (5.289) eram ignoradas como `not_found`**.
A causa não era tag apagada: o clone `--single-branch` da #47 só traz as tags
alcançáveis a partir do default branch. Projetos que publicam releases a partir
de branches de manutenção ficavam sem tag. No `react/react`, o lead time vinha
de 1 release em 28.

A correção (`287ac2b`) faz um `git fetch --filter=tree:0` de todas as tags logo
depois do clone, ainda sem consumir cota da API. Resultado:

| | Antes | Depois |
|---|---:|---:|
| Releases `not_found` | 5.289 | 1 |
| Repositórios com lead time nulo | 61 | 1 (`expo/expo`, monorepo sem commits novos entre releases: nulo legítimo) |
| Mediana LT (a), em dias | 6,91 (n = 269) | 10,35 (n = 329) |
| Mediana LT (b), em dias | 6,07 (n = 269) | 11,97 (n = 329) |
| Repositórios que mudaram de faixa DORA de lead time | — | 23 de 269 |

A execução "antes" reproduziu exatamente os 61 nulos e as 86 inversões do
dataset original, o que valida o script de diagnóstico.

### 4.2 LT(b) > LT(a) é legítimo

- **0 violações** do invariante por release (nenhum commit com lead time maior
  que o LT(a) da própria release), conferido em todos os commits da amostra.
- A inversão vem da ponderação: (a) pesa cada release igualmente e (b) pesa
  cada commit. Uma versão *major* com centenas de commits domina (b).
- Quatro casos conferidos release a release: `pandas-dev/pandas` (`v3.0.0`,
  3.037 de 3.191 commits), `charmbracelet/bubbletea` (`v2.0.0`, 759/817),
  `huginn/huginn` (667/740) e `gogs/gogs` (`v0.14.0`, 308/361).

### 4.3 Achado para a seção de ameaças à validade

Com todas as tags disponíveis, 2.649 releases em 120 repositórios são
comparadas com uma predecessora cronológica de **outra linha de manutenção**
(ex.: `v19.0.1` contra `v19.2.0`). Isso infla o número de commits e o lead
time. Mantive a definição do guia, que é comum à turma, e registrei o efeito
como ameaça de construto.

## 5. Testes e cobertura

Arquivos novos ou alterados nesta sprint:

| Arquivo | Testes | O que cobre |
|---|---:|---|
| `tests/test_cfr_b.py` | 39 | Heurística v1 e CFR (b) (seção 3.3) |
| `tests/test_persist_releases.py` | 3 | Comando de preenchimento: gravação, retomada e falhas |
| `tests/test_releases.py` | +1 | Coluna `status` e `commits_count` nulo para `not_found` |
| `tests/test_git_clone.py` | +2 | Fetch de todas as tags após o clone (com e sem token) e falha não fatal |
| `tests/test_pipeline_integration.py` | ajuste | Orquestrador grava `releases/` (C1) e `releases_c2/` |
| `tests/test_investigar_lead_time.py` | 5 | Motivos dos nulos, inversão legítima sem violar o invariante e detecção de linha de manutenção |

```
186 passed
metricas/cfr_b.py              100%
metricas (módulo inteiro)      100%   (CI exige ≥ 80%)
pipeline/releases.py            95%
pipeline/git_clone.py           84%
pipeline/persist_releases.py    80%
```

## 6. Pendências e dependências

- **#61 (rotulação):** depende da planilha da #63 (Marcela). O protocolo exige
  que eu rotule **sem ver a saída da heurística** e que o commit dos rótulos
  seja anterior ao primeiro commit da avaliação (#62). Por isso, nenhum código
  de avaliação foi commitado ainda. A #63 já pode usar `dados/releases/`
  (regenerável com o comando da seção 2) para sortear as 5 releases por
  repositório e montar os links.
- **#62 (P/R/F1):** começa depois do consenso (#65). O registro `HEURISTICS`
  já está pronto para receber as versões refinadas (v2, v3…) se o F1 ficar
  abaixo de 0,70.
- **Integração (#55 e #56, João):**
  - chamar `calculate_cfr_b` no orquestrador com a versão final da heurística;
  - recalcular as colunas `lead_time_*` de `dados/repositorios.csv` com o clone
    corrigido, porque os valores atuais ainda são os anteriores à correção (60
    nulos recuperáveis, 23 mudanças de faixa);
  - o orquestrador agora grava C1 em `releases/` e C2 em `releases_c2/`.
- **#68 (Metodologia):** minha parte (lead time a/b, CFR b, versões da
  heurística com F1 e motivos dos nulos) usa os números deste relatório e de
  `docs/investigacao_lead_time.md`. A tabela de F1 entra depois da #62.
- **#69 (fatores da RQ 06):** decisão a tomar com a Marcela.

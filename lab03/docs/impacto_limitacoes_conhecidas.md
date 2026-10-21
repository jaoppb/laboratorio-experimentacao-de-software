# Impacto das limitações conhecidas (achados 2, 3, 5 e 7 da PR #74)

**Natureza:** quantificação a partir dos dados persistidos, com opções. **Nenhuma alteração de código ou de dados.**
Os achados são os da seção "Achados fora do escopo" da PR #74 (rascunho de Metodologia). A numeração é a dela:

| # | Achado | Seção |
|---|---|---|
| 2 | Limite superior `fim: "2026-09-30"` lido como `2026-09-30T00:00:00Z` | 3 |
| 3 | Valores nulos viram `Low` em `lead_time_tier`, `cfr_tier` e `recovery_tier` | 4 |
| 5 | Runs lidos só até 1.000 quando `total_count ≥ 1.000` | 5 |
| 7 | `git log` guarda só o assunto do commit, o que limita a heurística do CFR (b) | 6 |

**Dados:** os 330 repositórios da #56 (`releases/*.parquet` com 25.731 releases na janela e `runs/*.parquet` com
2.289.119 runs), em modo somente leitura e copiados para `lab03/cache/issue69/` (ignorado pelo Git). Sem rede, sem
reexecução do pipeline. Reprodução na seção 8; os scripts completos estão nos anexos.

## 1. Resumo

| Achado | Quem é afetado | Magnitude medida | O que **não** dá para medir offline | Opções (sem mexer em código aqui) |
|---|---|---|---|---|
| 2. Janela termina às 00:00Z de 30/09 | todos os 330 (o último dia inteiro está ausente); ~93 releases (0,36%) e ~7,2 mil runs (0,32%) esperados nesse dia; 15 repositórios a ≤ 1 release de mudar de faixa de deployment frequency, ~0,85 mudança de faixa esperada | pequena nas médias, relevante só para fronteiras | os dados do dia 30/09 (a coleta já cortou) | perguntar ao professor; manter e documentar; ou ampliar o fim e recoletar só 30/09 |
| 3. Nulos viram `Low` | no CSV versionado: 61 nulos de lead time (54% dos `Low` de lead time) e 18 de recuperação (**90%** dos `Low` de recuperação). Com o lead time corrigido: 1 e 18 | recuperação: 18 repositórios; 15 deles **nunca tiveram falha**; nota geral muda em 7 a 14 repositórios | — | manter; tratar como n/d; ou regra específica para "sem falhas" |
| 5. Truncamento em 1.000 runs | 21 repositórios (6,4%), 561 intervalos saturados + 60 duvidosos; tempo não observado: mediana 4%, máximo 67% (PostHog) | CFR (a) e recuperação; efeito esperado em faixa: ~0,5 repositório | `total_count` real (não foi persistido) | aceitar e declarar; sinalizar no dataset; recoletar com divisão mais fina; excluir em sensibilidade |
| 7. Só o assunto do commit | 3.152 decisões (15% de 21.065) em 152 repositórios podem mudar, sempre para "corretiva" | cenário calibrado: ~1,6 mil releases, 32 repositórios com faixa de CFR (b) diferente (P5–P95: 19–40); teto: 51 | texto completo das mensagens | aceitar; recoletar `%B` offline (~10 min); validar em amostra |

Contexto que vale registrar junto: o dataset **versionado** em `main` ainda tem lead time anterior à correção do clone
(seção 4.1) e a heurística v1 está **abaixo da meta de F1** contra os 149 rótulos avaliáveis da Marcela (seção 6.4).

## 2. Verificação dos dados (recálculo)

O script `recalcular.py` refaz as métricas a partir de `releases/` e `runs/` com as mesmas funções de `metricas/`
e compara com `repositorios.csv` da #56 (idêntico ao `dados/repositorios.csv` de `main` em 2026-10-20).

| Coluna | Repositórios divergentes (de 330) |
|---|---:|
| `cfr_a`, `recovery_hours`, `cfr_b`, `deployment_tier`, `cfr_tier`, `recovery_tier` | 0 |
| `releases_count_window` | 1 (PostHog: 2.576 no CSV × 2.575 persistidas) |
| `lead_time_a_hours` | **170** (o CSV está defasado) |
| `lead_time_tier` | 44 |
| `overall_dora_tier` | 12 |

O recálculo reproduz todas as colunas exceto o lead time, cujo CSV é anterior à correção do clone (`docs/investigacao_lead_time.md`).
As seções 4 a 6 usam, por isso, os valores **recalculados**, que equivalem ao que a regeneração (#56) deve produzir.

## 3. Achado 2: limite superior da janela

**O que o código faz.** `config.yaml` tem `inicio: "2025-10-01"` e `fim: "2026-09-30"`. `_parse_datetime` lê as duas datas
como `00:00:00Z`; o filtro de releases é `inicio ≤ published_at ≤ fim`, e a coleta de runs usa `created=inicio..fim`.
Portanto a janela real é `[01/10/2025 00:00Z, 30/09/2026 00:00Z]`.

**Medições.**

| Medida | Resultado |
|---|---|
| Duração real da janela | 364 dias = 52,00 semanas (o guia usa ≈ 52,1 = 365/7) |
| Última release persistida / último run | 29/09/2026 23:57:16Z / 30/09/2026 04:29:28Z (provavelmente uma re-execução de run criado antes do corte) |
| Runs com `run_started_at` > fim | 7, em 3 repositórios (re-execuções; o corte vale para `created`) |
| Releases esperadas no dia 30/09 (quarta-feira) | ~93 (0,36% das 25.731), pelo padrão semanal de publicação |
| Runs esperados no dia 30/09 | ~7.226 (0,32% de 2.289.119) |
| Releases publicadas nos 7 dias anteriores ao corte (censura do CFR (b)) | 1.050 em 141 repositórios |
| Divisor 52,1 × duração real | frequência armazenada 0,19% menor que a real; 2 repositórios (52 releases) trocariam de faixa se o divisor fosse 52,0 |

**Faixa de deployment frequency.** Quantas releases faltam para mudar de faixa (≥ 12, ≥ 53, ≥ 365 releases): 15
repositórios estão a ≤ 1 release de subir de faixa, 24 a ≤ 2 e 35 a ≤ 3. Com uma Poisson de taxa diária calibrada
pela média das quartas-feiras, o dia 30/09 mudaria **~0,85 repositório** de faixa (P(≥ 1) = 0,59).

**CFR (b).** A censura usa `fim − 7 dias`. Se o fim fosse 01/10/2026 00:00Z, 166 das 1.050 releases censuradas passariam
a ser avaliadas; 50 repositórios teriam CFR (b) diferente e 2 mudariam de faixa. É um **piso** da mudança, porque as
releases de 30/09 não estão nos dados e, quando existem, são a "próxima release" de outras.

**Magnitude:** pequena para estatísticas agregadas (~0,3% dos eventos); afeta sobretudo repositórios na fronteira de
faixa. O ponto principal é de **semântica**: o texto do guia diz "12 meses", e a janela efetiva tem 364 dias.

**Opções.**
1. **Confirmar com o professor** (rascunho em `docs/mensagem_professor_janela.md`) antes de qualquer mudança.
2. **Manter e documentar** a regra na Metodologia ("fim exclusivo, 00:00 UTC"); custo ~0,5 h; mantém os dados atuais.
3. **Ampliar o fim** para incluir 30/09 inteiro (por exemplo `fim: "2026-09-30T23:59:59Z"` ou `2026-10-01`) e coletar
   de novo esse último dia: exige mudar a configuração, rodar `persist_releases` e refazer a coleta de runs do mês de setembro.
   Esforço estimado: algumas horas de execução e conferência (premissa: o cache HTTP reaproveita as demais requisições;
   não foi medido). Requer token e rede.
4. Em qualquer caso, alinhar o divisor (52,1) e a regra de censura à janela escolhida.

## 4. Achado 3: nulos mapeados para `Low`

`classify_lead_time`, `classify_change_failure_rate` e `classify_recovery_time` devolvem `Low` quando o valor é `None`.
Isso vale para as três colunas de faixa e entra na nota geral (mediana das 4 notas, arredondada para baixo).

### 4.1 Quantos nulos há

| Fonte | Lead time nulo | `Low` de lead time | Recuperação nula | `Low` de recuperação | CFR (a) nulo |
|---|---:|---:|---:|---:|---:|
| CSV versionado em `main` (38 colunas; idêntico à cópia da #56) | 61 | 112 (54% nulos) | 18 | 20 (**90% nulos**) | 0 |
| Recalculado (equivale à regeneração da #56) | 1 | 101 (1% nulo) | 18 | 20 (**90% nulos**) | 0 |

`cfr_b` nulo em 2 repositórios **não** vira `Low`: `cfr_b_tier` fica vazio, que é o tratamento correto.

**Lead time.** Os 61 nulos do CSV de `main` são o efeito do bug do clone (`--single-branch`) já corrigido; sobra 1 nulo
legítimo (tag não encontrada + release sem commits novos). **Recuperação.** Os 18 nulos persistem após a correção.

### 4.2 Por que a recuperação é nula

| Motivo | Repositórios |
|---|---:|
| Nenhum episódio de falha na janela (nada a recuperar) | **15** |
| Só episódios censurados (falhou e nunca voltou a passar) | 3 (`langflow-ai/langflow`, `axios/axios`, `YunaiV/ruoyi-vue-pro`) |

Dos 20 repositórios `Low` em recuperação, **apenas 2 têm mediana ≥ 168 h de fato**; 15 são "sem falhas" (CFR (a) = 0) e 3
são censurados. O docstring de `classify_recovery_time` diz que `Low` vale também para "ausente/censurado sem resolução", mas nem o
guia nem o código distinguem o caso "sem falhas", que é o oposto de um repositório com recuperação lenta.

### 4.3 Efeito nas distribuições (valores recalculados)

| Distribuição | Elite | High | Medium | Low | n/d |
|---|---:|---:|---:|---:|---:|
| Lead time, como está | 49 | 82 | 98 | 101 | 0 |
| Lead time, nulo = n/d | 49 | 82 | 98 | 100 | 1 |
| Recuperação, como está | 76 | 200 | 34 | **20** | 0 |
| Recuperação, nulo = n/d | 76 | 200 | 34 | **2** | 18 |

Na nota geral (`overall_dora_tier`), 19 repositórios têm pelo menos um nulo:

| Regra | Mudam de faixa geral | Elite | High | Medium | Low |
|---|---:|---:|---:|---:|---:|
| Como está (nulo → `Low`) | n/a | 21 | 141 | 148 | 20 |
| Nulo sai da mediana (usa só as notas válidas) | 7 | 22 | 144 | 146 | 18 |
| "Sem falhas" conta como Elite em recuperação; censurado segue `Low` | 14 | 22 | 148 | 146 | 14 |

**Onde isso importa.** As RQ 01 a 04 reportam valores numéricos (`NaN` fica de fora), então n cai para 329
(lead time), 312 (recuperação) e 328 (CFR (b)). O efeito aparece (i) na distribuição de **faixas** de recuperação e
lead time (RQ 02/04), (ii) na **classificação geral** e (iii) na RQ 07 (concordância de faixas entre combinações).

**Magnitude:** alta para a faixa `Low` de recuperação (90% de artefato) e moderada na nota geral (7 a 14 repositórios,
2 a 4% da amostra).

**Opções.**
1. **Manter o comportamento** e declará-lo na Metodologia e em Ameaças, citando "18 repositórios (5,5%)" e a separação
   15 + 3 acima. Custo ~0,5 h; mantém reprodutibilidade com o que foi coletado.
2. **Tratar nulo como n/d** nas faixas (e usar a mediana das notas válidas): muda a regra de `metricas/dora.py` e dos testes
   e exige regenerar o CSV; esforço estimado de ~2–3 h de código + testes e a reexecução de agregação (sem rede, pois os
   Parquet já têm tudo).
3. **Regra específica**: "sem falhas" → Elite em recuperação; "só censurado" → `Low`. Requer decisão conceitual do grupo.
4. **Sensibilidade**: manter a regra do guia na análise principal e reportar as duas variantes acima como análise de robustez.

## 5. Achado 5: truncamento em 1.000 runs

**Mecanismo** (`pipeline/workflow_runs.py`). O coletor divide a janela em meses e, em cada intervalo com
`total_count ≥ 1.000`, faz bisseção (até `max_depth = 3`, parando em intervalos de 2 dias). Uma folha que ainda tenha ≥ 1.000
runs lê só 10 páginas × 100 = 1.000 runs, as mais recentes. O `total_count` e os `bisection_events` **não são
persistidos**, e o dataset não sinaliza o truncamento.

**Como detectamos pelos dados.** `truncamento.py` replica a divisão (meses + bisseção, `ceiling = 1000`, `max_depth = 3`) sobre
`run_started_at` dos runs persistidos. Uma folha de profundidade 3 com ≥ 1.000 runs observados é uma folha saturada
(duplicatas de fronteira podem deixar 995–999, que contamos como "duvidosas").

| Medida | Resultado |
|---|---|
| Folhas saturadas (≥ 1.000 observados) | 561 |
| Folhas duvidosas (995–999) | 60 |
| Repositórios afetados | **21 de 330 (6,4%)** (20 com folha certa + 1 só duvidosa) |
| Runs persistidos nesses 21 | 1.086.369 (47% de todos os runs) |
| Tempo não observado por repositório | mediana 4,0%; mín. 0,3%; máx. 67,4% |

Repositórios mais afetados (fração da janela sem runs observados): PostHog 67,4%, openclaw 46,6%, grafana 43,8%, sentry
36,8%, pytorch 20,6%, unsloth 17,8%, superset 17,1%; depois twenty 8,2% e metabase 6,3%. Os outros 12 ficam em ≤ 4,5%.
A lista completa sai do script.

**Quais métricas são afetadas.** CFR (a) e recuperação (RQ 03a, 04, 05a e RQ 07), que usam os runs. Frequência de deploy,
lead time e CFR (b) usam releases, não runs. O filtro de ≥ 50 runs não é afetado.

**Magnitude do viés.** Como o `total_count` real é desconhecido, simulamos o mecanismo em 157 repositórios **não afetados**
com ≥ 1.500 runs: removemos os runs mais antigos de cada bloco de 3,875 dias e recalculamos.

| Fração mantida do bloco (mais recentes) | |Δ CFR (a)| mediana (P95) | Faixa de CFR (a) muda | Recuperação, razão sub/total (mediana; P5–P95) | Faixa de recuperação muda |
|---|---|---:|---|---:|
| 80% | 0,0016 (0,0076) | 0,0% | 1,02; 0,80–1,65 | 2,5% |
| 56% | 0,0027 (0,0156) | 0,0% | 1,04; 0,70–2,81 | 7,0% |
| 30% | 0,0045 (0,0295) | 1,3% | 1,15; 0,51–11,64 | 17,2% |

Aplicando a taxa à cobertura de cada repositório afetado (PostHog ~33%, openclaw ~53%, grafana ~56%, sentry ~63%, pytorch,
unsloth e superset ~80%), espera-se **~0,5 repositório** com faixa de recuperação diferente e ~0 com faixa de CFR (a)
diferente. O valor numérico da recuperação de quem perde mais de metade da janela pode variar bastante (P5–P95 de 0,5 a 11,6
vezes com 30% mantidos). Limitação: a simulação supõe perda aleatória por bloco e não reproduz o padrão real (os mais
recentes de cada folha).

**Opções.**
1. **Aceitar e declarar** como ameaça à validade, listando os 21 repositórios e a fração não observada; ~1 h.
2. **Sinalizar no dataset** (coluna `runs_truncados` / `fracao_janela_observada`) persistindo `total_count` e
   `bisection_events` na próxima coleta; exige mudança de código no pipeline e nova coleta de runs.
3. **Recoletar com divisão mais fina** (`max_depth` 4 ou 5 e `min_interval_seconds` menores): cada nível adicional
   dobra o número de chamadas nas folhas saturadas; ordem de grandeza ~10⁴ requisições por nível (premissa: 621 folhas × 2
   subintervalos × até 10 páginas; não medido). Requer token e é a única opção que remove o viés. Sem garantia para
   repositórios muito ativos como PostHog (94 folhas saturadas), que podem continuar saturados.
4. **Análise de sensibilidade**: repetir CFR (a), recuperação e RQ 05/06/07 sem os 7 repositórios com > 15% sem
   observação (n = 323) e comparar.

## 6. Achado 7: só o assunto do commit

**Mecanismo.** `pipeline/git_clone.py` extrai commits com `--format=%H<sep>%aI<sep>%s`, ou seja, só o **assunto**.
A heurística v1 (`metricas/cfr_b.py`) marca uma release como corretiva se o bump é só de patch **e** algum commit contém
`revert|hotfix|fix...` na mensagem (para tags fora de SemVer, só o critério da mensagem).

**Argumento de direção.** A mensagem completa contém o assunto, então a busca por palavra-chave só pode **acrescentar**
correspondências. Nenhuma release hoje corretiva deixaria de ser; as mudanças são sempre `não → sim`. Além disso, só
decidem pelas mensagens as releases cuja versão é bump de patch (ou fora de SemVer) e que têm commits; chamamos de
**sensíveis** as que têm essas duas condições e **nenhuma** palavra-chave no assunto.

### 6.1 Quantas decisões podem mudar

`cfr_b_mensagens.py` percorre as 21.065 decisões de CFR (b) (release seguida por outra em até 7 dias, não censurada,
com commits conhecidos), em 300 repositórios:

| Categoria | Decisões | % |
|---|---:|---:|
| Corretiva pela v1 (patch + palavra-chave) | 7.923 | 37,6% |
| Imune: o bump não é de patch (a mensagem não decide) | 9.592 | 45,5% |
| Imune: sem commits novos | 398 | 1,9% |
| **Sensível** (patch/fora de SemVer, sem palavra-chave no assunto) | **3.152** | **15,0%** |

As sensíveis estão em **152 repositórios**. Do total de 6.127.531 commits persistidos, 20,0% têm assunto de merge
("Merge pull request #N from ..."), que não traz o título do PR; esse título estaria no corpo da mensagem completa.

### 6.2 Magnitude

| Cenário | Releases que viram falha | Repositórios com CFR (b) diferente | Com faixa diferente | Mediana de CFR (b) |
|---|---:|---:|---:|---|
| Piso (nenhuma sensível muda) | 0 | 0 | 0 | 0,186 |
| **Teto** (todas as sensíveis viram corretivas) | 3.152 | 152 | **51** | 0,186 → 0,215 |
| **Calibrado** (cada sensível vira com p ≈ 0,52; 200 sorteios) | ~1.630 (P5–P95: 874–2.307) | ~119 (91–136) | **~32 (19–40)** | n/d |

O p do cenário calibrado vem dos rótulos da Marcela: no estrato sensível (n = 12 releases rotuladas e avaliáveis), 6 foram
marcadas como corretivas (50%; IC 95% de Jeffreys 24–76%); a posteriori Beta é usada para propagar a incerteza.
Duas ressalvas importantes: **n = 12 é muito pouco**, e a Marcela pode julgar "corretiva" por outras razões que não a
palavra-chave na mensagem completa (por exemplo, notas da release), o que **superestima** p. O cenário calibrado
é, portanto, um valor de referência, não uma previsão; o único número firme é o **teto** (e o piso).

### 6.3 O que a mensagem completa também pode piorar

O texto completo pode trazer `Fixes #123` e `Revert` em corpos de commits de funcionalidade, aumentando os falsos
positivos. A precisão da v1 já é baixa (seção 6.4), então ampliar a base de busca sem rever a regra pode piorar o
resultado em vez de melhorar.

### 6.4 Contexto: desempenho atual da v1 contra os rótulos da Marcela (não é o consenso)

Das 300 linhas de `validacao/rotulos_marcela.csv`, **150 têm `tag_name = "(pendente de persistência)"`** e não podem ser
ligadas a uma release; restam 149 avaliáveis (1 é a primeira release da história).

| | v1 = não | v1 = sim |
|---|---:|---:|
| Marcela = não | 56 | 33 |
| Marcela = sim | 34 | 26 |

Precisão 0,44, recall 0,43, F1 0,44 (meta do guia: F1 ≥ 0,70). Dos 34 falsos negativos, **28 são bumps que não são de patch**
(a mensagem completa não ajudaria) e só **6** pertencem ao estrato "sensível" do achado 7. Dos 33 falsos positivos, 31 são
bumps de patch cuja mensagem tem palavra-chave. Ou seja, o limite do assunto responde por uma fração pequena do erro; o
critério de versão responde pela maior parte. Isso orienta a #62: refinar a regra de versão tende a render mais que
recoletar mensagens completas.

**Opções.**
1. **Aceitar e declarar** (o teto é conhecido: +3.152 falhas; 51 repositórios mudariam de faixa); ~1 h.
2. **Recoletar com `%B`** (mensagem completa) a partir dos clones *blobless* via `pipeline.persist_releases`: o
   `docs/investigacao_lead_time.md` registra ~10 min para regenerar os Parquet; exige adaptar `git_clone.py` e o
   esquema (mudança de código, fora deste memorando) e rede para clonar de novo.
3. **Validar em amostra**: rotular, com a mensagem completa, ~100 das 3.152 sensíveis para estimar p com IC útil
   (n = 100 dá IC de ~±10 pontos); depois decidir entre 1 e 2.
4. **Rever a v1 antes de recoletar** (#62), dado o erro dominante do critério de versão.

## 7. Observações fora de escopo

- `validacao/rotulos_marcela.csv` tem 150 linhas com `tag_name = "(pendente de persistência)"` (30 repositórios); o
  arquivo tem só 6 textos distintos em `notas_justificativa`. Convém conferir isso no consenso (#65).
- O CSV versionado em `main` já traz as colunas de CFR (b) (backfill da #56), mas o lead time ainda é anterior à correção do
  clone (seção 2): 61 nulos e 170 repositórios com valor diferente do recálculo. Falta regenerar essas colunas.
- A fronteira de `fim` também aparece em `analises/persistir_amostra_ouro.py:40` e `analises/amostra_ouro.py`
  (`DEFAULT_WINDOW_END`), então qualquer mudança da janela precisa ser feita em mais de um lugar.

## 8. Como reproduzir

Pré-requisitos: ambiente `uv` do `lab03/` e os Parquet de `releases/` e `runs/` da #56 (não versionados). Os scripts
usam só arquivos locais; nada é enviado pela rede.

```bash
cd lab03 && uv sync
DADOS_56=<caminho>/lab03/dados          # onde estão releases/ e runs/ da #56 (somente leitura)
mkdir -p cache/issue69 && cp -R "$DADOS_56"/{releases,runs,repositorios.csv,repositorios.parquet,funil.csv} cache/issue69/

# extrai os scripts dos anexos para cache/issue69/scripts/ (ignorado pelo Git)
python3 - <<'PY'
import pathlib, re
saida = pathlib.Path("cache/issue69/scripts"); saida.mkdir(parents=True, exist_ok=True)
for doc in ("docs/decisao_rq06_tipo_projeto.md", "docs/impacto_limitacoes_conhecidas.md"):
    for nome, corpo in re.findall(r"```python\n# arquivo: (\S+)\n(.*?)```", pathlib.Path(doc).read_text(encoding="utf-8"), re.S):
        (saida / nome).write_text(corpo, encoding="utf-8")
PY

export PYTHONPATH=.
uv run python cache/issue69/scripts/recalcular.py                 # seção 2 (grava recomputado.pkl)
uv run python cache/issue69/scripts/janela.py                     # seção 3
uv run python cache/issue69/scripts/nulos.py                      # seção 4 (usa recomputado.pkl)
uv run python cache/issue69/scripts/truncamento.py                # seção 5 (grava truncados.pkl)
uv run python cache/issue69/scripts/truncamento_sensibilidade.py  # seção 5, tabela de viés (~30 s)
uv run python cache/issue69/scripts/cfr_b_mensagens.py            # seção 6 (~1,5 min)
```

Observações: os scripts não alteram arquivos versionados (gravam só em `cache/issue69/`). `cfr_b_mensagens.py` usa semente 42
para os sorteios do cenário calibrado.

---

## Anexo: scripts

### A.1 `recalcular.py`

```python
# arquivo: recalcular.py
"""Recalcula as métricas DORA do dataset persistido (releases/ + runs/) e compara com o CSV.

Uso (de dentro de lab03/):  uv run python cache/issue69/scripts/recalcular.py
"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from metricas.cfr_b import calculate_cfr_b
from metricas.dora import evaluate_repository_dora
from metricas.lead_time import calculate_lead_time
from metricas.schemas import Commit, Release, WorkflowRun
from metricas.stability import calculate_cfr_a, calculate_recovery_time

D = Path("cache/issue69")
WINDOW_END = "2026-09-30"
WINDOW_START = "2025-10-01"


def stem(full_name: str) -> str:
    return full_name.replace("/", "__")


def load_release_rows(full_name: str):
    """[(Release, status, previous_tag, [Commit])] ordenado por data."""
    data = pq.read_table(D / "releases" / f"{stem(full_name)}.parquet").to_pydict()
    rows = []
    for i, tag in enumerate(data["tag_name"]):
        rel = Release(tag_name=tag, published_at=data["published_at"][i], prerelease=data["prerelease"][i])
        commits = [Commit(sha=c["sha"], committed_at=c["committed_at"], message=c["message"])
                   for c in (data["commits"][i] or [])]
        rows.append((rel, data["status"][i], data["previous_release"][i], commits))
    return sorted(rows, key=lambda r: r[0].published_at)


def load_runs(full_name: str):
    d = pq.read_table(D / "runs" / f"{stem(full_name)}.parquet").to_pydict()
    return [WorkflowRun(workflow_id=d["workflow_id"][i], conclusion=d["conclusion"][i],
                        run_started_at=d["run_started_at"][i], updated_at=d["updated_at"][i], id=d["id"][i])
            for i in range(len(d["id"]))]


def recompute(full_name: str, window_end=WINDOW_END, window_start=WINDOW_START) -> dict:
    from metricas.schemas import _parse_datetime
    ws, we = _parse_datetime(window_start), _parse_datetime(window_end)
    rows = load_release_rows(full_name)
    in_win = [r for r in rows if ws <= r[0].published_at <= we and not r[0].prerelease]
    pairs = [(rel, commits if status == "ok" else None) for rel, status, _, commits in in_win]
    lt = calculate_lead_time(pairs)
    runs = load_runs(full_name)  # o pipeline não refiltra os runs: a janela já foi aplicada em `created`
    cfr_a = calculate_cfr_a(runs)
    rec = calculate_recovery_time(runs)
    ev = evaluate_repository_dora(
        len(in_win) / 52.1,
        None if lt.median_a_hours is None else lt.median_a_hours / 24.0,
        cfr_a, rec.median_hours)
    cb = calculate_cfr_b(pairs, window_end=we)
    return dict(full_name=full_name, n_rel=len(in_win), lt_a=lt.median_a_hours, lt_b=lt.median_b_hours,
                cfr_a=cfr_a, rec_h=rec.median_hours, rec_total=rec.total_episodes,
                rec_resolved=rec.resolved_episodes, rec_censored=rec.censored_episodes,
                dep_tier=ev.deployment_tier.value, lt_tier=ev.lead_time_tier.value,
                cfr_tier=ev.cfr_tier.value, rec_tier=ev.recovery_tier.value,
                overall_score=ev.overall_score, overall_tier=ev.overall_tier.value,
                scores=ev.scores, cfr_b=cb.cfr_b, cfr_b_eval=cb.evaluated_releases)


if __name__ == "__main__":
    csv = pd.read_csv(D / "repositorios.csv")
    out = pd.DataFrame([recompute(n) for n in csv.full_name])
    out.to_pickle(D / "recomputado.pkl")
    m = csv.merge(out.add_prefix("rc_").rename(columns={"rc_full_name": "full_name"}), on="full_name")
    def difere(a, b, tol=1e-9):
        return int(((m[a].fillna(-1) - m[b].fillna(-1)).abs() > tol).sum())
    chk = {
        "releases_count_window": int((m.releases_count_window != m.rc_n_rel).sum()),
        "cfr_a": difere("cfr_a", "rc_cfr_a"),
        "recovery_hours": difere("recovery_hours", "rc_rec_h", 1e-6),
        "lead_time_a_hours (CSV defasado)": difere("lead_time_a_hours", "rc_lt_a", 1e-6),
        "cfr_b": difere("cfr_b", "rc_cfr_b"),
        "deployment_tier": int((m.deployment_tier != m.rc_dep_tier).sum()),
        "cfr_tier": int((m.cfr_tier != m.rc_cfr_tier).sum()),
        "recovery_tier": int((m.recovery_tier != m.rc_rec_tier).sum()),
        "lead_time_tier (CSV defasado)": int((m.lead_time_tier != m.rc_lt_tier).sum()),
        "overall_dora_tier (CSV defasado)": int((m.overall_dora_tier != m.rc_overall_tier).sum()),
    }
    for k, v in chk.items():
        print(f"{k}: {v} divergentes de {len(m)}")
```

### A.2 `janela.py`

```python
# arquivo: janela.py
"""Achado 2: o limite superior `fim: "2026-09-30"` é lido como 2026-09-30T00:00:00Z.

Os dados persistidos não contêm nada de 30/09 (a coleta já corta em 00:00Z), então o impacto é ESTIMADO:
(1) tamanho real da janela x constante 52,1 semanas; (2) releases e runs esperados no dia 30/09 pelo padrão por
dia da semana (30/09/2026 é quarta-feira); (3) repositórios próximos de uma fronteira de faixa de deployment
frequency; (4) censura do CFR (b), que usa `window_end - 7 dias` como corte.

Uso (de dentro de lab03/):  PYTHONPATH=. uv run python cache/issue69/scripts/janela.py
"""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

from metricas.cfr_b import calculate_cfr_b
from metricas.dora import classify_change_failure_rate
from metricas.schemas import Commit, Release, _parse_datetime

D = Path("cache/issue69")
INICIO = datetime(2025, 10, 1, tzinfo=timezone.utc)
FIM = datetime(2026, 9, 30, tzinfo=timezone.utc)
csv = pd.read_csv(D / "repositorios.csv")

print("== 1. Tamanho da janela ==")
dias = (FIM - INICIO).days
print(f"Lido como [{INICIO:%Y-%m-%d}T00:00Z, {FIM:%Y-%m-%d}T00:00Z]: {dias} dias = {dias/7:.2f} semanas "
      f"(a fórmula divide por 52,1 semanas = {52.1*7:.1f} dias; 365 dias = {365/7:.2f} semanas, "
      f"ou seja, só 'fim inclusivo' dá 12 meses cheios)")
print(f"Efeito de 52,1 vs {dias/7:.2f} no deployment frequency: {100*(52.1/(dias/7)-1):+.2f}% (subestima)")

print("\n== 2. Último dado persistido ==")
rel, runs = [], []
for n in csv.full_name:
    r = pq.read_table(D / "releases" / f"{n.replace('/', '__')}.parquet", columns=["published_at", "prerelease"]).to_pandas()
    r = r[~r.prerelease]
    r["repo"] = n
    rel.append(r)
    u = pq.read_table(D / "runs" / f"{n.replace('/', '__')}.parquet", columns=["run_started_at"]).to_pandas()
    u["repo"] = n
    runs.append(u)
rel, runs = pd.concat(rel), pd.concat(runs)
print("Última release persistida:", rel.published_at.max(), "| último run:", runs.run_started_at.max())
apos = runs[runs.run_started_at > FIM]
print(f"Runs com run_started_at > fim (re-execuções de runs criados antes do corte): {len(apos)} em {apos.repo.nunique()} repositórios")
rel = rel[(rel.published_at >= INICIO) & (rel.published_at <= FIM)]
print("Releases na janela:", len(rel), "| runs persistidos:", len(runs))

print("\n== 3. Releases e runs esperados em 30/09 (quarta) ==")
wd = rel.published_at.dt.dayofweek.value_counts().sort_index()
wd_runs = runs.run_started_at.dt.dayofweek.value_counts().sort_index()
n_quartas = sum(1 for k in range(dias) if (INICIO.toordinal() + k) % 7 == datetime(2026, 9, 30).toordinal() % 7)
print("releases por dia da semana (0=seg):", wd.to_dict(), "| quartas na janela:", n_quartas)
esp_rel = wd[2] / n_quartas
esp_run = wd_runs[2] / n_quartas
print(f"Esperado em 30/09: {esp_rel:.0f} releases ({100*esp_rel/len(rel):.2f}% das {len(rel)}) "
      f"e {esp_run:.0f} runs ({100*esp_run/len(runs):.2f}% dos {len(runs)})")
ultimos = rel[rel.published_at >= FIM - pd.Timedelta(days=7)]
print(f"Releases publicadas nos últimos 7 dias antes do corte: {len(ultimos)} em {ultimos.repo.nunique()} repositórios")

print("\n== 4. Repositórios perto de uma fronteira de faixa de deployment frequency ==")
n_i = csv.releases_count_window.to_numpy()
lim = [12, 53, 365]  # n mínimo para Medium (>=12/52,1), High (>=1/sem), Elite (>=7/sem)
falta = np.array([min([t - n for t in lim if t > n], default=999) for n in n_i])
lam = n_i * (wd[2] / len(rel)) / n_quartas * 1.0  # releases esperadas em uma quarta, por repositório
for k in (1, 2, 3):
    print(f"faltam <= {k} release(s) para subir de faixa: {(falta <= k).sum()} repositórios")
p = stats.poisson.sf(falta - 1, lam)              # P(K >= falta)
print(f"Repositórios esperados mudando de faixa de deployment frequency se 30/09 entrasse: {p.sum():.2f} "
      f"(P(>=1 mudança) = {1 - np.prod(1 - p):.2f})")

print("\n== 5. CFR (b): corte de censura = fim - 7 dias ==")


def carregar(n):
    d = pq.read_table(D / "releases" / f"{n.replace('/', '__')}.parquet").to_pydict()
    out = []
    for i, tag in enumerate(d["tag_name"]):
        if d["prerelease"][i]:
            continue
        cs = [Commit(c["sha"], c["committed_at"], c["message"]) for c in (d["commits"][i] or [])]
        out.append((Release(tag, d["published_at"][i]), cs if d["status"][i] == "ok" else None))
    return sorted(out, key=lambda x: x[0].published_at)


alvo = {"corte atual (fim=2026-09-30T00:00Z)": "2026-09-30", "fim inclusivo (2026-10-01T00:00Z)": "2026-10-01"}
res = {k: {} for k in alvo}
for n in csv.full_name:
    pares = carregar(n)
    for k, v in alvo.items():
        res[k][n] = calculate_cfr_b(pares, window_end=_parse_datetime(v))
a, b = list(res.values())
cens_a = sum(r.censored_releases for r in a.values())
cens_b = sum(r.censored_releases for r in b.values())
tier = lambda r: None if r.cfr_b is None else classify_change_failure_rate(r.cfr_b).value
print(f"Releases censuradas: {cens_a} (atual) -> {cens_b} (fim inclusivo): {cens_a - cens_b} passam a ser avaliadas")
print("repositórios com CFR (b) diferente:", sum(a[k].cfr_b != b[k].cfr_b for k in a),
      "| faixa diferente:", sum(tier(a[k]) != tier(b[k]) for k in a),
      "| repositórios sem nenhuma release avaliável:", sum(r.cfr_b is None for r in a.values()), "->",
      sum(r.cfr_b is None for r in b.values()))
print("(limite inferior da mudança: as releases de 30/09, que seriam a 'próxima release' de algumas, não estão nos dados)")
```

### A.3 `nulos.py`

```python
# arquivo: nulos.py
"""Achado 3: valores nulos mapeados para `Low` (lead time, CFR, recuperação).

Uso (de dentro de lab03/; requer `recalcular.py` já executado):
    PYTHONPATH=. uv run python cache/issue69/scripts/nulos.py
"""
import statistics
from math import floor
from pathlib import Path

import pandas as pd

D = Path("cache/issue69")
TIER = {"Elite": 4, "High": 3, "Medium": 2, "Low": 1}
INV = {v: k for k, v in TIER.items()}
ORDEM = ["Elite", "High", "Medium", "Low"]


def dist(s: pd.Series) -> dict:
    return {t: int((s == t).sum()) for t in ORDEM} | {"n/d": int(s.isna().sum())}


def overall(scores: list[int]) -> int:
    return floor(statistics.median(scores))


csv_main = pd.read_csv("dados/repositorios.csv")      # versionado em main (defasado)
csv_56 = pd.read_csv(D / "repositorios.csv")          # cópia do dataset da #56
rc = pd.read_pickle(D / "recomputado.pkl")            # recálculo a partir de releases/ + runs/

print("== 1. Nulos por coluna e nulos que viraram Low ==")
for nome, df, lt, rec, cfr in [
    ("CSV main (versionado)", csv_main, "lead_time_a_hours", "recovery_hours", "cfr_a"),
    ("CSV #56 (cópia)", csv_56, "lead_time_a_hours", "recovery_hours", "cfr_a"),
    ("Recalculado (releases/ + runs/)", rc, "lt_a", "rec_h", "cfr_a"),
]:
    tl = "lead_time_tier" if "lead_time_tier" in df else "lt_tier"
    tr = "recovery_tier" if "recovery_tier" in df else "rec_tier"
    n_lt, n_rec, n_cfr = df[lt].isna().sum(), df[rec].isna().sum(), df[cfr].isna().sum()
    low_lt, low_rec = (df[tl] == "Low").sum(), (df[tr] == "Low").sum()
    print(f"{nome}: lead_time nulo={n_lt} (Low total={low_lt}; {100*n_lt/low_lt:.0f}% dos Low são nulos) | "
          f"recovery nulo={n_rec} (Low total={low_rec}; {100*n_rec/low_rec:.0f}% dos Low são nulos) | cfr_a nulo={n_cfr}")

print("\n== 2. Distribuição das faixas: como está (nulo→Low) × nulo como n/d (recalculado) ==")
for col, tier, val in [("Lead time", "lt_tier", "lt_a"), ("Recuperação", "rec_tier", "rec_h")]:
    atual = dist(rc[tier])
    sem = dist(rc[tier].where(rc[val].notna()))
    print(f"{col}: atual={atual}\n{' ' * len(col)}  nulo=n/d={sem}")

print("\n== 3. Motivo dos nulos de recuperação (recalculado) ==")
nr = rc[rc.rec_h.isna()]
print("sem nenhum episódio de falha (total_episodes==0):", int((nr.rec_total == 0).sum()))
print("só episódios censurados (nunca recuperou):       ", int((nr.rec_total > 0).sum()))
print(nr[["full_name", "rec_total", "rec_resolved", "rec_censored", "cfr_a"]].to_string(index=False))

print("\n== 4. Efeito na nota geral (mediana das 4 notas, arredondada para baixo) ==")
base = rc.overall_tier.value_counts().reindex(ORDEM, fill_value=0).to_dict()
print("atual (nulo→Low):", base)


def reclassifica(row, regra: str) -> str:
    dep, lt, cfr, rec = (TIER[row.dep_tier], TIER[row.lt_tier], TIER[row.cfr_tier], TIER[row.rec_tier])
    s = [dep, lt, cfr, rec]
    if regra == "descartar":                     # nulo sai do cálculo da mediana
        s = [dep, cfr]
        if pd.notna(row.lt_a):
            s.append(lt)
        if pd.notna(row.rec_h):
            s.append(rec)
    elif regra == "sem_falha_elite":              # sem episódios de falha → recuperação Elite (nada a recuperar)
        if pd.isna(row.rec_h) and row.rec_total == 0:
            s = [dep, lt, cfr, 4]
    return INV[overall(s)]


for regra in ("descartar", "sem_falha_elite"):
    novo = rc.apply(lambda r: reclassifica(r, regra), axis=1)
    muda = int((novo != rc.overall_tier).sum())
    print(f"regra={regra}: mudam de faixa geral={muda}; nova distribuição="
          f"{novo.value_counts().reindex(ORDEM, fill_value=0).to_dict()}")
print("repositórios com ao menos um nulo (lead time ou recuperação):",
      int((rc.lt_a.isna() | rc.rec_h.isna()).sum()))

print("\n== 5. Tamanho que cada análise perderia se o nulo fosse excluído ==")
print("RQ02 lead time (n válido):", int(rc.lt_a.notna().sum()), "de", len(rc))
print("RQ04 recuperação (n válido):", int(rc.rec_h.notna().sum()), "de", len(rc))
print("RQ03(b) CFR (b) (n válido):", int(rc.cfr_b.notna().sum()), "de", len(rc),
      "(cfr_b nulo já NÃO é mapeado para Low: cfr_b_tier fica vazio)")
```

### A.4 `truncamento.py`

```python
# arquivo: truncamento.py
"""Detecta, a partir dos runs persistidos, os intervalos que o coletor leu truncados em 1000 runs.

Replica `pipeline.workflow_runs`: divisão mensal da janela, bisseção adaptativa
(`threshold_ceiling=1000`, `min_interval_seconds=2 dias`, `max_depth=3`) e, na folha, no máximo 10 páginas
de 100 runs (= 1000). Como o `total_count` verdadeiro não foi persistido, a simulação usa a contagem
*observada* em cada intervalo (que só é inferior à real nas folhas truncadas, e nelas vale 1000 menos
duplicatas de fronteira). A data usada é `run_started_at` (proxy de `created_at`).

Uso (de dentro de lab03/):  PYTHONPATH=. uv run python cache/issue69/scripts/truncamento.py
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from pipeline.workflow_runs import split_window_into_months

D = Path("cache/issue69")
START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, tzinfo=timezone.utc)
CEIL, MIN_SECONDS, MAX_DEPTH = 1000, 86400.0 * 2, 3


def folhas(ts: np.ndarray, s: datetime, e: datetime, depth: int = 0):
    """Folhas (início, fim, contagem observada, profundidade) da bisseção para `ts` (datetime64[us])."""
    sn, en = np.datetime64(s.replace(tzinfo=None), "us"), np.datetime64(e.replace(tzinfo=None), "us")
    n = int(((ts >= sn) & (ts <= en)).sum())
    if n >= CEIL and (e - s).total_seconds() > MIN_SECONDS and depth < MAX_DEPTH:
        mid = s + (e - s) / 2
        return folhas(ts, s, mid, depth + 1) + folhas(ts, mid, e, depth + 1)
    return [(s, e, n, depth)]


def analisar(full_name: str):
    t = pq.read_table(D / "runs" / f"{full_name.replace('/', '__')}.parquet", columns=["id", "run_started_at"])
    df = t.to_pandas().drop_duplicates("id")
    ts = df.run_started_at.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy().astype("datetime64[us]")
    saida = []
    for ms, me in split_window_into_months(START, END):
        for s, e, n, depth in folhas(ts, ms, me):
            if depth == MAX_DEPTH and n >= CEIL - 5:  # só a folha de profundidade máxima trunca; tolera duplicatas de fronteira
                sn, en = np.datetime64(s.replace(tzinfo=None), "us"), np.datetime64(e.replace(tzinfo=None), "us")
                sel = ts[(ts >= sn) & (ts <= en)]
                tmin = sel.min()
                span_obs = (en - tmin) / np.timedelta64(1, "s")
                span_perdido = (tmin - sn) / np.timedelta64(1, "s")
                perdidos = n * span_perdido / span_obs if span_obs > 0 else float("nan")
                saida.append(dict(full_name=full_name, inicio=s, fim=e, depth=depth, observados=n,
                                  cobertura_s=span_obs, perdido_s=span_perdido, perdidos_estimados=perdidos))
    return saida, len(df)


if __name__ == "__main__":
    csv = pd.read_csv(D / "repositorios.csv")
    linhas, totais = [], {}
    for name in csv.full_name:
        s, n = analisar(name)
        linhas.extend(s)
        totais[name] = n
    ints = pd.DataFrame(linhas)
    ints.to_pickle(D / "truncados.pkl")
    janela_s = (END - START).total_seconds()
    certos = ints[ints.observados >= CEIL]
    print("folhas truncadas (observados >= 1000):", len(certos), "| ambíguas (995-999):", len(ints) - len(certos))
    print("repositórios afetados:", ints.full_name.nunique(), "de", len(csv),
          "| com >=1 folha certa:", certos.full_name.nunique())
    por_repo = ints.groupby("full_name").agg(
        folhas=("inicio", "count"), nao_observado_dias=("perdido_s", lambda x: x.sum() / 86400))
    por_repo["runs_persistidos"] = por_repo.index.map(totais)
    por_repo["tempo_nao_observado_pct"] = 100 * por_repo.nao_observado_dias * 86400 / janela_s
    print(por_repo.sort_values("tempo_nao_observado_pct", ascending=False).round(1).to_string())
    print("runs persistidos nos 330 repositórios:", sum(totais.values()),
          "| nos repositórios afetados:", int(por_repo.runs_persistidos.sum()))
    print("faixa do tempo não observado (mediana, min, max) %:",
          por_repo.tempo_nao_observado_pct.median().round(1), por_repo.tempo_nao_observado_pct.min().round(1),
          por_repo.tempo_nao_observado_pct.max().round(1))
```

### A.5 `truncamento_sensibilidade.py`

```python
# arquivo: truncamento_sensibilidade.py
"""Quanto o truncamento (só os `c` mais recentes de cada folha de 3,875 dias) distorce CFR (a) e recuperação?

Em repositórios NÃO afetados, descarta os runs mais antigos de cada bloco de 3,875 dias (comprimento da folha de
profundidade 3 de um mês de 31 dias) e recalcula as métricas. `c` é a fração do bloco que sobra (mais recentes).
Isto mede o viés esperado do mecanismo, não corrige os 21 repositórios afetados.

Uso (de dentro de lab03/; requer truncamento.py já executado):
    PYTHONPATH=. uv run python cache/issue69/scripts/truncamento_sensibilidade.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from metricas.dora import classify_change_failure_rate, classify_recovery_time
from metricas.schemas import WorkflowRun
from metricas.stability import calculate_cfr_a, calculate_recovery_time

D = Path("cache/issue69")
BLOCO = 3.875 * 86400
csv = pd.read_csv(D / "repositorios.csv")
afetados = set(pd.read_pickle(D / "truncados.pkl").full_name)
ini = pd.Timestamp("2025-10-01", tz="UTC")

linhas = []
for n in csv.full_name:
    if n in afetados:
        continue
    d = pq.read_table(D / "runs" / f"{n.replace('/', '__')}.parquet").to_pandas()
    if len(d) < 1500:      # repositórios pequenos não são o caso de interesse
        continue
    pos = ((d.run_started_at - ini).dt.total_seconds() % BLOCO) / BLOCO   # 0 = início do bloco, 1 = fim
    def runs(x):
        return [WorkflowRun(r.workflow_id, None if pd.isna(r.conclusion) else r.conclusion,
                            r.run_started_at, r.updated_at) for r in x.itertuples()]
    base_cfr, base_rec = calculate_cfr_a(runs(d)), calculate_recovery_time(runs(d)).median_hours
    for c in (0.8, 0.56, 0.3):
        s = d[pos >= 1 - c]                                               # mantém os mais recentes de cada bloco
        cfr, rec = calculate_cfr_a(runs(s)), calculate_recovery_time(runs(s)).median_hours
        linhas.append(dict(repo=n, c=c, d_cfr=(cfr or 0) - (base_cfr or 0),
                           tier_cfr_muda=classify_change_failure_rate(cfr) != classify_change_failure_rate(base_cfr),
                           rec_ratio=(rec / base_rec) if rec and base_rec else np.nan,
                           tier_rec_muda=classify_recovery_time(rec) != classify_recovery_time(base_rec)))
r = pd.DataFrame(linhas)
print("repositórios simulados (não afetados, >=1500 runs):", r.repo.nunique())
for c, g in r.groupby("c"):
    print(f"c={c}: |Δ CFR(a)| mediana={g.d_cfr.abs().median():.4f} P95={g.d_cfr.abs().quantile(.95):.4f} | "
          f"faixa do CFR(a) muda em {100*g.tier_cfr_muda.mean():.1f}% | "
          f"recuperação (razão sub/total) mediana={g.rec_ratio.median():.2f} P5-P95="
          f"{g.rec_ratio.quantile(.05):.2f}-{g.rec_ratio.quantile(.95):.2f} | "
          f"faixa da recuperação muda em {100*g.tier_rec_muda.mean():.1f}%")
```

### A.6 `cfr_b_mensagens.py`

```python
# arquivo: cfr_b_mensagens.py
"""Achado 7: mensagens de commit só com o assunto (`git log --format=%s`) e o CFR (b) da heurística v1.

Raciocínio: `is_fix_message` faz `regex.search` na mensagem. A mensagem completa contém o assunto, logo ela só
pode ACRESCENTAR correspondências: nenhuma release marcada hoje como corretiva deixa de ser. Além disso a v1 só
olha as mensagens quando a versão é um *bump* de patch (ou fora de SemVer). Então só podem mudar de decisão as
releases "sensíveis": elegíveis pela versão, com commits, e sem palavra-chave no assunto.

Uso (de dentro de lab03/):  PYTHONPATH=. uv run python cache/issue69/scripts/cfr_b_mensagens.py
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

from metricas.cfr_b import (FAILURE_HORIZON, HEURISTICS, calculate_cfr_b, heuristic_v1, is_corrective_release,
                            is_fix_message, is_patch_bump)
from metricas.dora import classify_change_failure_rate
from metricas.schemas import Commit, Release, _parse_datetime

D = Path("cache/issue69")
WE = _parse_datetime("2026-09-30")
MERGE = re.compile(r"^Merge (pull request|branch|remote-tracking branch|pull)", re.I)
RNG = np.random.default_rng(42)


_CACHE = {}


def carregar(full_name):
    if full_name not in _CACHE:
        _CACHE[full_name] = _ler(full_name)
    return _CACHE[full_name]


def _ler(full_name):
    d = pq.read_table(D / "releases" / f"{full_name.replace('/', '__')}.parquet").to_pydict()
    rows = []
    for i, tag in enumerate(d["tag_name"]):
        if d["prerelease"][i]:
            continue
        cs = [Commit(c["sha"], c["committed_at"], c["message"]) for c in (d["commits"][i] or [])]
        rows.append(dict(rel=Release(tag, d["published_at"][i]), status=d["status"][i],
                         prev=d["previous_release"][i], commits=cs))
    return sorted(rows, key=lambda r: r["rel"].published_at)


def pares(rows):
    return [(r["rel"], r["commits"] if r["status"] == "ok" else None) for r in rows]


def sensivel(prev_tag, tag, commits):
    """Elegível pela versão, tem commits e nenhum assunto casa com a palavra-chave."""
    patch = is_patch_bump(prev_tag, tag)
    elegivel = patch is None or patch
    return elegivel and len(commits) > 0 and not any(is_fix_message(c.message) for c in commits)


# 1. Rótulos da Marcela (150 de 300 linhas têm tag "(pendente de persistência)" e ficam de fora)
m = pd.read_csv("validacao/rotulos_marcela.csv", encoding="utf-8-sig")
lab = []
for _, r in m.iterrows():
    rows = {x["rel"].tag_name: x for x in carregar(r.repo_name)}
    x = rows.get(r.tag_name)
    if x is None or x["status"] != "ok" or x["prev"] is None:
        continue
    pred = is_corrective_release(x["prev"], r.tag_name, x["commits"])
    lab.append(dict(repo=r.repo_name, tag=r.tag_name, humano=r.release_corretiva == "sim", v1=pred,
                    sensivel=sensivel(x["prev"], r.tag_name, x["commits"]),
                    tem_merge=any(MERGE.match(c.message) for c in x["commits"])))
lab = pd.DataFrame(lab)
print(f"Releases rotuladas avaliáveis: {len(lab)} (de 300; 150 sem tag persistida)")
print(pd.crosstab(lab.humano, lab.v1, rownames=["Marcela"], colnames=["v1"]).to_string())
s = lab[lab.sensivel]
fn, n = int(s.humano.sum()), len(s)
lo, hi = stats.beta.ppf([0.025, 0.975], fn + 0.5, n - fn + 0.5)  # Jeffreys
print(f"Estrato sensível: n={n}; Marcela marcou 'corretiva' em {fn} -> p̂={fn/n:.2f} (IC95% Jeffreys {lo:.2f}-{hi:.2f})")
print("  desses, com commit de merge no assunto:", int(s.tem_merge.sum()), "| p̂ entre os com merge:",
      f"{s[s.tem_merge].humano.mean():.2f}" if s.tem_merge.any() else "n/d", "| sem merge:",
      f"{s[~s.tem_merge].humano.mean():.2f}")

# 2. População: decisões do CFR (b) nos 330 repositórios
csv = pd.read_csv(D / "repositorios.csv")
pop, sens_keys, base = [], {}, {}
n_commits = n_merge = 0
for name in csv.full_name:
    rows = carregar(name)
    base[name] = calculate_cfr_b(pares(rows), WE)
    chaves = set()
    for i, r in enumerate(rows):
        for c in r["commits"]:
            n_commits += 1
            n_merge += bool(MERGE.match(c.message))
    # a release i+1 é julgada quando vem até 7 dias depois da i, i não é censurada e os commits de i+1 são conhecidos
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if a["rel"].published_at > WE - FAILURE_HORIZON or b["rel"].published_at - a["rel"].published_at > FAILURE_HORIZON:
            continue
        if b["status"] != "ok":
            continue
        v1 = heuristic_v1(a["rel"].tag_name, b["rel"].tag_name, b["commits"])
        patch = is_patch_bump(a["rel"].tag_name, b["rel"].tag_name)
        if v1:
            cat = "corretiva (v1)"
        elif patch is False:
            cat = "imune (bump não é de patch)"
        elif not b["commits"]:
            cat = "imune (sem commits novos)"
        else:
            cat = "sensível (patch/fora de SemVer, sem palavra-chave no assunto)"
            chaves.add(b["rel"].tag_name)
        pop.append(dict(repo=name, tag=b["rel"].tag_name, cat=cat,
                        tem_merge=any(MERGE.match(c.message) for c in b["commits"])))
    sens_keys[name] = chaves
pop = pd.DataFrame(pop)
print("\nDecisões julgadas (release seguida por outra em ≤ 7 dias):", len(pop), "em", pop.repo.nunique(), "repositórios")
print(pop.cat.value_counts().to_string())
sens = pop[pop.cat.str.startswith("sensível")]
print("sensíveis:", len(sens), "em", sens.repo.nunique(), "repositórios; com commit de merge:", int(sens.tem_merge.sum()))
print(f"Commits persistidos: {n_commits}; assunto de merge (sem o título do PR): {n_merge} ({100*n_merge/n_commits:.1f}%)")
tot_eval = sum(b.evaluated_releases for b in base.values())
print("Releases avaliadas no CFR (b):", tot_eval, "| marcadas como falha (v1):", sum(b.failed_releases for b in base.values()))


# 3. Limite superior e cenário calibrado
def cfr_com_flips(flipper):
    out = {}
    for name in csv.full_name:
        rows = carregar(name)
        HEURISTICS["_t"] = lambda p, t, cs, name=name: heuristic_v1(p, t, cs) or flipper(name, t)
        out[name] = calculate_cfr_b(pares(rows), WE, version="_t")
    return out


def resumo(res, rotulo):
    mudou_cfr = sum(1 for k in res if res[k].cfr_b != base[k].cfr_b)
    def tier(r): return None if r.cfr_b is None else classify_change_failure_rate(r.cfr_b).value
    mudou_tier = sum(1 for k in res if tier(res[k]) != tier(base[k]))
    med0 = np.nanmedian([base[k].cfr_b if base[k].cfr_b is not None else np.nan for k in res])
    med1 = np.nanmedian([res[k].cfr_b if res[k].cfr_b is not None else np.nan for k in res])
    falhas = sum(r.failed_releases for r in res.values()) - sum(r.failed_releases for r in base.values())
    print(f"{rotulo}: releases que passam a falha={falhas}; repositórios com CFR (b) diferente={mudou_cfr}; "
          f"com faixa diferente={mudou_tier}; mediana CFR (b) {med0:.3f} -> {med1:.3f}")
    return falhas, mudou_cfr, mudou_tier


print("\nCenários (apenas as releases sensíveis podem mudar; mudança sempre para cima):")
resumo(cfr_com_flips(lambda n, t: t in sens_keys[n]), "Limite superior (todas as sensíveis viram corretivas)")
resultados = []
for _ in range(200):
    p = RNG.beta(fn + 0.5, n - fn + 0.5)           # incerteza sobre p̂ (posteriori de Jeffreys)
    flip = {(k, t) for k, ts in sens_keys.items() for t in ts if RNG.random() < p}
    res = cfr_com_flips(lambda nme, t: (nme, t) in flip)
    mudou_tier = sum(1 for k in res if (None if res[k].cfr_b is None else classify_change_failure_rate(res[k].cfr_b).value)
                     != (None if base[k].cfr_b is None else classify_change_failure_rate(base[k].cfr_b).value))
    resultados.append((p, len(flip), mudou_tier,
                       sum(1 for k in res if res[k].cfr_b != base[k].cfr_b)))
r = np.array(resultados)
q = lambda c: np.percentile(r[:, c], [5, 50, 95]).round(1)
print(f"Cenário calibrado (200 sorteios; p ~ Beta posteriori de p̂): p mediano={np.median(r[:,0]):.2f}; "
      f"releases que viram falha (P5/P50/P95)={q(1)}; repositórios com faixa de CFR (b) diferente={q(2)}; "
      f"com CFR (b) diferente={q(3)}")
```

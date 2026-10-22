# Regeneração final do dataset (Issue #56)

Relatório gerado em 2026-10-22 por `pipeline.regenerar`. Compara o dataset anterior (versionado antes da regeneração) com o regenerado, coluna a coluna.

## Resumo

- Repositórios: 330 (conjunto congelado; a seleção não foi refeita).
- Janela de observação: 2025-10-01 a 2026-09-30 (fim do dia incluído).
- Heurística de CFR (b): `v1`.
- Colunas do esquema: 44 (8 de metadados preservadas, 36 de métricas recalculadas).
- Colunas de métricas com alguma linha alterada: 34.
- Repositórios com a faixa geral (`overall_dora_tier`) alterada: 25.
- Runs coletados (soma de `total_workflow_runs`): 2,289,119 antes, 3,962,858 depois (a divisão recursiva sem piso recuperou os runs que a coleta anterior truncava em 1.000 por intervalo).

## Invariantes

- 330 linhas, mesmos repositórios na mesma ordem: OK
- Colunas de metadados idênticas às do dataset anterior: OK
- Esquema completo (CSV e Parquet com as mesmas colunas): OK

## Colunas: antes × depois

| Coluna | Linhas alteradas | Nulos antes | Nulos depois | Passou a nulo | Passou a preenchido |
|---|---:|---:|---:|---:|---:|
| `releases_count_window` | 60 | 0 | 0 | 0 | 0 |
| `total_releases` | 45 | 0 | 0 | 0 | 0 |
| `workflow_runs_count_window` | 221 | 0 | 0 | 0 | 0 |
| `total_workflow_runs` | 222 | 0 | 0 | 0 | 0 |
| `deployment_frequency` | 330 | 0 | 0 | 0 | 0 |
| `deployment_tier` | 0 | 0 | 0 | 0 | 0 |
| `lead_time_a_hours` | 187 | 61 | 1 | 0 | 60 |
| `lead_time_b_hours` | 199 | 61 | 1 | 0 | 60 |
| `lead_time_tier` | 47 | 0 | 1 | 1 | 0 |
| `cfr_a` | 214 | 0 | 0 | 0 | 0 |
| `cfr_tier` | 1 | 0 | 0 | 0 | 0 |
| `recovery_hours` | 92 | 18 | 18 | 0 | 0 |
| `recovery_tier` | 18 | 0 | 0 | 0 | 0 |
| `censored_episodes_ratio` | 88 | 0 | 0 | 0 | 0 |
| `overall_dora_score` | 25 | 0 | 0 | 0 | 0 |
| `overall_dora_tier` | 25 | 0 | 0 | 0 | 0 |
| `prereleases_count_window` | 2 | 1 | 0 | 0 | 1 |
| `total_prereleases` | 24 | 1 | 0 | 0 | 1 |
| `tags_count_window` | 2 | 1 | 0 | 0 | 1 |
| `total_tags` | 33 | 1 | 0 | 0 | 1 |
| `c2_deployment_frequency` | 2 | 1 | 0 | 0 | 1 |
| `c2_lead_time_b_hours` | 2 | 2 | 1 | 0 | 1 |
| `c3_deployment_frequency` | 2 | 1 | 0 | 0 | 1 |
| `c3_lead_time_b_hours` | 1 | 1 | 0 | 0 | 1 |
| `cfr_b` | 50 | 2 | 2 | 0 | 0 |
| `cfr_b_tier` | 2 | 2 | 2 | 0 | 0 |
| `cfr_b_failed_releases` | 19 | 0 | 0 | 0 | 0 |
| `cfr_b_evaluated_releases` | 54 | 0 | 0 | 0 | 0 |
| `cfr_b_censored_releases` | 67 | 0 | 0 | 0 | 0 |
| `cfr_b_skipped_releases` | 0 | 0 | 0 | 0 | 0 |
| `c2_cfr_b` (nova) | 328 | 330 | 2 | 0 | 328 |
| `c2_cfr_b_tier` (nova) | 328 | 330 | 2 | 0 | 328 |
| `c2_cfr_b_failed_releases` (nova) | 330 | 330 | 0 | 0 | 330 |
| `c2_cfr_b_evaluated_releases` (nova) | 330 | 330 | 0 | 0 | 330 |
| `c2_cfr_b_censored_releases` (nova) | 330 | 330 | 0 | 0 | 330 |
| `c2_cfr_b_skipped_releases` (nova) | 330 | 330 | 0 | 0 | 330 |

## Transições de faixa (tier)

### `lead_time_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| Low | Medium | 20 |
| Medium | Low | 6 |
| Low | High | 5 |
| Elite | Low | 3 |
| High | Low | 3 |
| Elite | High | 2 |
| Elite | Medium | 2 |
| High | Medium | 2 |
| Medium | High | 2 |
| High | Elite | 1 |
| Low | (nulo) | 1 |

### `cfr_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| High | Elite | 1 |

### `recovery_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| Low | Elite | 14 |
| Medium | High | 2 |
| Elite | High | 1 |
| High | Elite | 1 |

### `overall_dora_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| Medium | High | 6 |
| Low | Medium | 5 |
| High | Elite | 3 |
| High | Medium | 3 |
| Low | High | 3 |
| Elite | High | 2 |
| Medium | Low | 2 |
| High | Low | 1 |

### `cfr_b_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| High | Elite | 1 |
| High | Medium | 1 |

### `c2_cfr_b_tier`

| Antes | Depois | Repositórios |
|---|---|---:|
| (nulo) | Elite | 160 |
| (nulo) | High | 60 |
| (nulo) | Low | 60 |
| (nulo) | Medium | 48 |

## Repositórios com a faixa geral alterada

| Repositório | Antes | Depois | Nota antes | Nota depois |
|---|---|---|---:|---:|
| react/react | High | Medium | 3 | 2 |
| openai/codex | Medium | High | 2 | 3 |
| mrdoob/three.js | Low | Medium | 1 | 2 |
| axios/axios | Medium | Low | 2 | 1 |
| addyosmani/agent-skills | Low | High | 1 | 3 |
| thedotmack/claude-mem | High | Elite | 3 | 4 |
| louislam/uptime-kuma | High | Medium | 3 | 2 |
| PaddlePaddle/PaddleOCR | Medium | Low | 2 | 1 |
| vitejs/vite | Elite | High | 4 | 3 |
| typicode/json-server | Medium | High | 2 | 3 |
| openbq-org/OpenBB | Low | Medium | 1 | 2 |
| expressjs/express | High | Low | 3 | 1 |
| socketio/socket.io | Elite | High | 4 | 3 |
| BerriAI/litellm | High | Elite | 3 | 4 |
| typst/typst | Low | Medium | 1 | 2 |
| ionic-team/ionic-framework | Medium | High | 2 | 3 |
| usebruno/bruno | High | Medium | 3 | 2 |
| microsoft/monaco-editor | Low | Medium | 1 | 2 |
| MadsLorentzen/ai-job-search | Medium | High | 2 | 3 |
| DeusData/codebase-memory-mcp | High | Elite | 3 | 4 |
| react-hook-form/react-hook-form | Medium | High | 2 | 3 |
| JustVugg/colibri | Medium | High | 2 | 3 |
| appsmithorg/appsmith | Low | High | 1 | 3 |
| aseprite/aseprite | Low | Medium | 1 | 2 |
| preactjs/preact | Low | High | 1 | 3 |

## Repositórios fora dos critérios mínimos da seleção

A amostra é congelada: estes repositórios permanecem no dataset mesmo que a recoleta (janela até o fim do dia, divisão recursiva de runs) os deixe abaixo de 5 releases ou 50 runs válidos na janela.

Nenhum.

## Repositórios mantidos com os valores anteriores

Nenhum: todos os repositórios foram recoletados.

## Coleta dos runs: reconciliação com a API

Modo de obtenção dos runs por repositório: completo: 4, reconciliar: 326.

No modo `reconciliar`, os runs de `dados/runs/` do dataset anterior (janela até 2026-09-30T00:00Z) foram conferidos por intervalo mensal: a API informa só o `total_count` (1 requisição) e, quando bate com os runs já coletados no intervalo, eles são mantidos (uma recoleta completa devolveria o mesmo conjunto); quando difere, o intervalo é recoletado com a divisão recursiva do coletor. O trecho final (2026-09-30T00:00:01Z a 23:59:59Z) é sempre coletado. Intervalos: 3620 mantidos, 292 recoletados, 326 do trecho final.

Intervalos recoletados (292):

| Repositório | Intervalo | Runs anteriores | Contagem da API | Motivo |
|---|---|---:|---:|---|
| BerriAI/litellm | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2566 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| BerriAI/litellm | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 4998 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ClickHouse/ClickHouse | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 553 | 555 | a API tem mais runs (novos, ou deslocados por reexecução) |
| ClickHouse/ClickHouse | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 586 | 584 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| ClickHouse/ClickHouse | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 857 | 894 | a API tem mais runs (novos, ou deslocados por reexecução) |
| ClickHouse/ClickHouse | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 1125 | 1090 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| ClickHouse/ClickHouse | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 1249 | 1247 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| Imbad0202/academic-research-skills | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 174 | 176 | a API tem mais runs (novos, ou deslocados por reexecução) |
| Kong/insomnia | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 619 | 620 | a API tem mais runs (novos, ou deslocados por reexecução) |
| Kong/insomnia | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 416 | 415 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| NousResearch/hermes-agent | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 4323 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| NousResearch/hermes-agent | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 5900 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| NousResearch/hermes-agent | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 4556 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| NousResearch/hermes-agent | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 4051 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| NousResearch/hermes-agent | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7040 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| NousResearch/hermes-agent | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 7999 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 8001 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 7300 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 7709 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 8001 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| PostHog/posthog | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| XTLS/Xray-core | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 159 | 160 | a API tem mais runs (novos, ou deslocados por reexecução) |
| XTLS/Xray-core | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 181 | 180 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| aaif-goose/goose | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2549 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| aaif-goose/goose | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1621 | 1627 | intervalo truncado em 1.000 runs na coleta anterior |
| anomalyco/opencode | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 3488 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 4743 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 5530 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 5449 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 5471 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 6724 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 7490 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 6013 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| anomalyco/opencode | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 3715 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/airflow | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2892 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 4226 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 3170 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 4706 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 5643 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 6302 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 6070 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 6530 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 6877 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7846 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| apache/superset | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| astral-sh/ruff | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 557 | 558 | a API tem mais runs (novos, ou deslocados por reexecução) |
| astral-sh/ruff | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 709 | 708 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| astral-sh/ruff | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 862 | 863 | a API tem mais runs (novos, ou deslocados por reexecução) |
| babel/babel | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 92 | 93 | a API tem mais runs (novos, ou deslocados por reexecução) |
| babel/babel | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 76 | 75 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| ccxt/ccxt | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 3165 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 2940 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2690 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3600 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2550 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 3273 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 6677 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 6167 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7644 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ccxt/ccxt | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 6808 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| codewhale-hq/Codewhale | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 2558 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| codewhale-hq/Codewhale | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3985 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 4232 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 3642 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 2987 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 3015 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3573 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2565 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 2545 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 3286 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2740 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| curl/curl | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3479 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| electron/electron | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 522 | 523 | a API tem mais runs (novos, ou deslocados por reexecução) |
| electron/electron | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 192 | 191 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| expo/expo | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 1459 | 1460 | intervalo truncado em 1.000 runs na coleta anterior |
| expo/expo | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2619 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| expo/expo | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2568 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| expo/expo | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 4035 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| expo/expo | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 2550 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| expo/expo | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2387 | 2394 | intervalo truncado em 1.000 runs na coleta anterior |
| expo/expo | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3265 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| facebookresearch/faiss | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 63 | 64 | a API tem mais runs (novos, ou deslocados por reexecução) |
| facebookresearch/faiss | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 79 | 78 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| getsentry/sentry | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 7856 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 7160 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 5880 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 6576 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 7512 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 7953 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7044 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| getsentry/sentry | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 7207 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3263 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 4452 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 5782 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 6451 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 6092 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7811 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ggml-org/llama.cpp | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 7626 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| github/spec-kit | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 848 | 849 | a API tem mais runs (novos, ou deslocados por reexecução) |
| github/spec-kit | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 957 | 956 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| go-gitea/gitea | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 474 | 475 | a API tem mais runs (novos, ou deslocados por reexecução) |
| godotengine/godot | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 49 | 50 | a API tem mais runs (novos, ou deslocados por reexecução) |
| godotengine/godot | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 48 | 47 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| google-gemini/gemini-cli | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2525 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| google-gemini/gemini-cli | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2735 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 7242 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 5600 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 6945 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 7381 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 7618 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| grafana/grafana | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 6725 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| hashicorp/terraform | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 91 | 92 | a API tem mais runs (novos, ou deslocados por reexecução) |
| hashicorp/terraform | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 69 | 68 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| headroomlabs-ai/headroom | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 2853 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| headroomlabs-ai/headroom | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 4412 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| headroomlabs-ai/headroom | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 3553 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| headroomlabs-ai/headroom | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 2514 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| heygen-com/hyperframes | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 3311 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| heygen-com/hyperframes | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 4431 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| heygen-com/hyperframes | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2452 | 2458 | intervalo truncado em 1.000 runs na coleta anterior |
| heygen-com/hyperframes | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 4696 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| jellyfin/jellyfin | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 326 | 328 | a API tem mais runs (novos, ou deslocados por reexecução) |
| koala73/worldmonitor | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2510 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| koala73/worldmonitor | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 3720 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| koala73/worldmonitor | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 4945 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| koala73/worldmonitor | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 6738 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| lobehub/lobehub | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 2610 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| lobehub/lobehub | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3623 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mastodon/mastodon | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 2014 | 2016 | intervalo truncado em 1.000 runs na coleta anterior |
| mastodon/mastodon | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 1470 | 1477 | intervalo truncado em 1.000 runs na coleta anterior |
| mastodon/mastodon | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 1410 | 1416 | intervalo truncado em 1.000 runs na coleta anterior |
| mastodon/mastodon | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1984 | 1989 | intervalo truncado em 1.000 runs na coleta anterior |
| mermaid-js/mermaid | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 263 | 264 | a API tem mais runs (novos, ou deslocados por reexecução) |
| mermaid-js/mermaid | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 223 | 222 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| metabase/metabase | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 5295 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 4900 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 5217 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 5702 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 5720 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 6367 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 6712 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 6627 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 7115 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 6981 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 6194 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| metabase/metabase | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 4827 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/playwright | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2626 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2691 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 3170 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 5098 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 7179 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 4482 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 4300 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 4617 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 5000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| microsoft/vscode | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 5663 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mozilla/pdf.js | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 1001 | 1008 | intervalo truncado em 1.000 runs na coleta anterior |
| mozilla/pdf.js | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 1231 | 1239 | intervalo truncado em 1.000 runs na coleta anterior |
| mozilla/pdf.js | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 1408 | 1417 | intervalo truncado em 1.000 runs na coleta anterior |
| mozilla/pdf.js | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1234 | 1241 | intervalo truncado em 1.000 runs na coleta anterior |
| mudler/LocalAI | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2558 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2955 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 4068 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 4491 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 5451 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 4703 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| mudler/LocalAI | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 4557 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| netdata/netdata | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 2503 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| nexu-io/open-design | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 3008 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| nodejs/node | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 4248 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| nodejs/node | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 4033 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| nuxt/nuxt | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 297 | 298 | a API tem mais runs (novos, ou deslocados por reexecução) |
| nuxt/nuxt | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 450 | 449 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| nuxt/nuxt | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 716 | 717 | a API tem mais runs (novos, ou deslocados por reexecução) |
| nuxt/nuxt | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 804 | 811 | a API tem mais runs (novos, ou deslocados por reexecução) |
| nvm-sh/nvm | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 64 | 65 | a API tem mais runs (novos, ou deslocados por reexecução) |
| nvm-sh/nvm | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 241 | 240 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| openai/codex | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 3708 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 5325 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 5085 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 6048 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 5659 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 5438 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2528 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openai/codex | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3090 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 6592 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 7208 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| openclaw/openclaw | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pandas-dev/pandas | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 2859 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| penpot/penpot | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 921 | 926 | a API tem mais runs (novos, ou deslocados por reexecução) |
| prettier/prettier | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 418 | 419 | a API tem mais runs (novos, ou deslocados por reexecução) |
| pytorch/pytorch | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 7997 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 6963 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 7546 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 7455 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 7999 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 7999 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 8002 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 7988 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 8006 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| pytorch/pytorch | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 7848 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| roboflow/supervision | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 659 | 663 | a API tem mais runs (novos, ou deslocados por reexecução) |
| scrapy/scrapy | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 54 | 56 | a API tem mais runs (novos, ou deslocados por reexecução) |
| scrapy/scrapy | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 50 | 48 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| scrapy/scrapy | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 86 | 88 | a API tem mais runs (novos, ou deslocados por reexecução) |
| scrapy/scrapy | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 146 | 144 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| spring-projects/spring-boot | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 457 | 458 | a API tem mais runs (novos, ou deslocados por reexecução) |
| spring-projects/spring-boot | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 486 | 485 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| storybookjs/storybook | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 1081 | 1082 | intervalo truncado em 1.000 runs na coleta anterior |
| storybookjs/storybook | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1015 | 1014 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| streamlit/streamlit | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 2604 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2619 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 2712 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3196 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 2618 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 2885 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 3608 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 3185 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| streamlit/streamlit | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3393 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3281 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 3511 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 3813 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 3186 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 3526 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 3097 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| supabase/supabase | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3977 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| tinyhumansai/openhuman | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 6227 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| tldraw/tldraw | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 2784 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| tldraw/tldraw | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 3030 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 4068 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 4308 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 4954 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 2791 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 2553 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 3564 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 5293 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 4202 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 7253 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 7366 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 7859 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| twentyhq/twenty | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 7921 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| ultralytics/ultralytics | 2025-12-01T00:00:00Z .. 2025-12-31T23:59:59Z | 354 | 355 | a API tem mais runs (novos, ou deslocados por reexecução) |
| ultralytics/ultralytics | 2026-01-01T00:00:00Z .. 2026-01-31T23:59:59Z | 538 | 537 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| ultralytics/ultralytics | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 317 | 319 | a API tem mais runs (novos, ou deslocados por reexecução) |
| ultralytics/ultralytics | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 490 | 488 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| ultralytics/ultralytics | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1157 | 1160 | intervalo truncado em 1.000 runs na coleta anterior |
| unslothai/unsloth | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 4554 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| unslothai/unsloth | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 7053 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| unslothai/unsloth | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 7418 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| unslothai/unsloth | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| unslothai/unsloth | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 8000 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| vercel/next.js | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 1722 | 1724 | intervalo truncado em 1.000 runs na coleta anterior |
| vercel/next.js | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 755 | 753 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| vercel/next.js | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 1827 | 1829 | intervalo truncado em 1.000 runs na coleta anterior |
| vercel/next.js | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 1602 | 1601 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| vercel/next.js | 2026-05-01T00:00:00Z .. 2026-05-31T23:59:59Z | 823 | 822 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| vercel/next.js | 2026-06-01T00:00:00Z .. 2026-06-30T23:59:59Z | 1169 | 1170 | intervalo truncado em 1.000 runs na coleta anterior |
| vercel/next.js | 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z | 1153 | 1154 | intervalo truncado em 1.000 runs na coleta anterior |
| vercel/next.js | 2026-08-01T00:00:00Z .. 2026-08-31T23:59:59Z | 1248 | 1246 | a API tem menos runs (removidos/expirados, ou deslocados por reexecução) |
| vercel/next.js | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 776 | 779 | a API tem mais runs (novos, ou deslocados por reexecução) |
| withastro/astro | 2026-09-01T00:00:00Z .. 2026-09-30T00:00:00Z | 1302 | 1304 | intervalo truncado em 1.000 runs na coleta anterior |
| zed-industries/zed | 2025-10-01T00:00:00Z .. 2025-10-31T23:59:59Z | 3477 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| zed-industries/zed | 2026-02-01T00:00:00Z .. 2026-02-28T23:59:59Z | 2826 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| zed-industries/zed | 2026-03-01T00:00:00Z .. 2026-03-31T23:59:59Z | 2828 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |
| zed-industries/zed | 2026-04-01T00:00:00Z .. 2026-04-30T23:59:59Z | 2613 | 2500 | a contagem da API chegou ao teto de 2.500 (intervalo muito grande, a coleta anterior estava truncada); recoletado com divisão recursiva |

## Diagnóstico da coleta de runs

Nenhum intervalo residual não divisível.

## Execução desacoplada

A coleta roda em `jao-pc` (`~/regen-lab03`) sob um supervisor que não depende de quem a iniciou: `supervisor.sh` (instância única por `flock`, reinício com espera crescente de 60 s a 10 min) executa `python -m pipeline.regenerar --resume --runs-modo reconciliar`, é lançado por `systemd-run --user --unit=regen-sup` (com `systemd-inhibit` quando permitido e orçamento de memória `MemoryHigh=6G`/`MemoryMax=8G`, `Nice=15`, E/S ociosa e `CPUWeight=20`, porque a máquina é compartilhada; o próprio pipeline também não inicia novos repositórios com menos de 3 GiB de RAM disponível, processa no máximo um repositório "pesado" por vez e usa 2 workers) e, ao concluir, ele mesmo gera `outputs-<data UTC>.tar.gz` (dataset, `runs/`, este relatório, resultado das invariantes, `git diff --stat` e `SHA256SUMS`) e o marcador `DONE`.

Como conferir e retomar (todos os comandos em `~/regen-lab03`):

- Estado em uma chamada: `cat status.json` (`state`, `done/total`, requisições, cota restante e reinício da cota, memória (`memory_mb`: RSS, pico, RAM disponível) e pico por repositório, repositórios em andamento, ETA e último erro; `updated_at` parado há mais de ~5 min indica travamento).
- Supervisor: `systemctl --user status regen-sup`; log em `supervisor.log`; log do pipeline em `regen.log`.
- Concluído quando existirem `DONE` e `outputs-*.tar.gz` (+ `.sha256`). Baixe o pacote e confira com `sha256sum -c`.
- Retomar manualmente: o progresso fica em `lab03/dados/.regenerar/checkpoint.jsonl`; `systemctl --user start regen-sup` (ou `bash supervisor.sh`) continua de onde parou. Nunca rode duas instâncias; o `flock` recusa a segunda.
- Não use `--fresh` para retomar: ele descarta o checkpoint.


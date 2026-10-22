# Avaliação da heurística de release corretiva (Issue #62)

**Código:** `analises/avaliar_heuristica.py` · **Testes:** `tests/test_avaliar_heuristica.py`
**Heurísticas:** `metricas/cfr_b.py` (`HEURISTICS`, `DEFAULT_HEURISTIC`)
**Referência:** `validacao/consenso.csv` (Issue #65) · **Dados de releases:** `dados/releases/*.parquet`

> Este documento descreve a **ferramenta e o protocolo** e traz, na seção 5, a tabela da execução real
> (21/10/2026). A análise completa (recortes, análise de erros, avisos de validade e reprodução) está em
> [`resultados_avaliacao_heuristica.md`](./resultados_avaliacao_heuristica.md). **A referência é um consenso automático
> majoritariamente de IA, não de pessoas** (`../validacao/PROVENIENCIA.md`).

## 1. Objetivo

Medir quanto a heurística automática que classifica uma release como *corretiva* (base do
CFR (b)) concorda com o julgamento humano de consenso, e decidir qual versão vai para o
pipeline. É o passo 5 da Seção 6 do Guia do Lab03 e sustenta a RQ 03 (b) e a seção de
ameaças à validade do artigo.

## 2. Método

* **Referência:** coluna `release_corretiva` (`sim`/`não`) do `validacao/consenso.csv`,
  uma linha por release sorteada (300 no total: 60 repositórios × 5 releases).
* **Classe positiva:** `sim` (release corretiva). Para cada release, a ferramenta aplica
  `is_corrective_release(previous_release, tag_name, commits, version=<versão>)`, usando o
  `previous_release` e os commits persistidos em `dados/releases/<dono>__<repo>.parquet`,
  exatamente como o pipeline faz no CFR (b). O consenso e a heurística nunca se influenciam:
  a heurística só enxerga tag anterior, tag atual e mensagens de commit.
* **Métricas:** `sklearn.metrics.precision_recall_fscore_support` (classe positiva):
  * **Precisão** = VP / (VP + FP): das releases que a heurística marcou, quantas eram corretivas;
  * **Recall** = VP / (VP + FN): das corretivas do consenso, quantas a heurística achou;
  * **F1** = 2·P·R / (P + R).

  VP, FP, FN, VN formam a matriz de confusão e são reportados junto. Se um denominador
  for zero (ex.: a heurística não marcou nenhuma release → precisão), a métrica é
  **indefinida** e aparece como `n/d` (`zero_division=nan`), em vez de 0: um 0 sugeriria
  uma medição que não houve.
* **Releases excluídas.** Uma release do consenso não pode ser avaliada quando:
  1. o repositório não tem arquivo em `dados/releases/` (falha de clone/coleta);
  2. a tag não está no arquivo de releases do repositório;
  3. `status != ok` (`first_release` ou `not_found`: os commits da release são desconhecidos);
  4. `previous_release` é nulo.

  Essas releases são **excluídas, contadas e discriminadas por motivo** na saída (console e
  Markdown). A exclusão não depende da versão da heurística, então **todas as versões são
  avaliadas sobre o mesmo conjunto**, e `N avaliadas + N excluídas = 300`. Uma release
  `status = ok` sem commits novos é avaliável (a heurística decide `não`). O número de
  exclusões deve ser reportado no artigo, pois restringe a validade da avaliação (as
  releases excluídas são justamente as de coleta problemática).
* **Dependência.** Usa-se `scikit-learn` porque o Guia e a issue pedem explicitamente
  `precision_recall_fscore_support`, o que torna a conferência com o enunciado direta;
  é uma implementação amplamente validada e evita fórmulas próprias. O custo é uma
  dependência a mais (adicionada com `uv add` em `lab03/`, `pyproject.toml` + `uv.lock`).
* **Meta:** F1 ≥ 0,70 (`--meta-f1` altera o limite). Abaixo disso, a heurística precisa ser
  refinada (seção 4).

## 3. Como executar (ponta a ponta, a partir de `lab03/`)

```bash
cd lab03 && uv sync

# 1. Persistir releases e commits da amostra-ouro (precisa de GITHUB_TOKEN e rede; retomável).
uv run python -m analises.persistir_amostra_ouro

# 2. Rotulação independente (#57, #61, #64) → validacao/rotulos_{joao,gabriel,marcela}.csv,
#    kappa e reunião de consenso (#65) → validacao/consenso.csv (sem pendências):
uv run python -m analises.concordancia kappa
uv run python -m analises.concordancia verificar-consenso

# 3. Avaliar todas as versões registradas contra o consenso.
uv run python -m analises.avaliar_heuristica \
    --saida dados/analises/avaliacao_heuristica.md \
    --saida-erros dados/analises/avaliacao_heuristica_erros.csv
```

Parâmetros:

| Parâmetro        | Padrão                  | Função                                                              |
|------------------|-------------------------|---------------------------------------------------------------------|
| `--consenso`     | `validacao/consenso.csv`| Rótulos de consenso (lido, nunca criado nem alterado)               |
| `--releases-dir` | `dados/releases`        | Parquet de releases por repositório                                 |
| `--versoes`      | todas de `HEURISTICS`   | Subconjunto de versões a avaliar (ex.: `--versoes v1 v2`)           |
| `--meta-f1`      | `0.70`                  | Limite do critério de decisão                                       |
| `--saida`        | (nenhuma)               | Tabela de resultados: `.csv` → CSV; outra extensão → Markdown       |
| `--saida-erros`  | (nenhuma)               | CSV com todos os falsos positivos/negativos                         |
| `--max-erros`    | `10`                    | Máximo de erros por tipo e versão impressos no console              |
| `--forcar`       | desligado               | Sobrescreve saídas existentes                                       |

Códigos de saída: `0` ok; `1` entrada inválida (consenso fora do formato, versão
desconhecida, nenhuma release avaliável, saída já existente); `2` entrada ausente
(`consenso.csv` ou diretório de releases). A ferramenta só grava em `--saida` e
`--saida-erros`, não sobrescreve sem `--forcar` e recusa gravar sobre o `consenso.csv`.

### 3.1 Saída

Console: contagem de releases avaliadas/excluídas (com motivos), a tabela por versão e,
para cada versão, as listas de falsos positivos e negativos. O CSV de erros tem as colunas
`versao, tipo, repo_name, tag_name, previous_release, consenso, heuristica, bump_patch,
n_commits, n_commits_fix, mensagens_fix, release_url`; `bump_patch` e `mensagens_fix`
mostram qual critério da regra v1 falhou, e `release_url` permite reabrir a release para
conferir se o erro é da heurística ou do rótulo.

### 3.2 Análise de erros

Para cada versão, ler o CSV de erros e classificar as causas (a lista abaixo é um roteiro,
não um resultado):

* **Falso positivo** (heurística diz `sim`, consenso `não`): palavras como `fix` em
  commits de manutenção rotineira numa release de patch que traz funcionalidade.
* **Falso negativo** (heurística diz `não`, consenso `sim`): correções em release *minor*,
  tags fora de SemVer, mensagens sem as palavras-chave, release corretiva sem commits de fix.

## 4. Como as versões são registradas e a regra de decisão

* Cada versão é uma função em `metricas/cfr_b.py` registrada em `HEURISTICS`
  (ex.: `"v1": heuristic_v1`). **A ferramenta avalia automaticamente todas as chaves de
  `HEURISTICS`** e usa a **primeira linha do docstring** da função como descrição da regra
  na tabela; portanto, ao criar uma versão nova, o docstring deve começar com `vN: <regra>`.
* A versão usada pelo pipeline é `DEFAULT_HEURISTIC`. Trocá-la é uma decisão humana,
  tomada depois desta avaliação, e deve ser feita em commit próprio.
* **Regra de decisão:**
  1. Avaliar todas as versões. Se alguma tiver **F1 ≥ 0,70**, escolher a de maior F1
     (empate: a mais simples); registrar a escolha na seção 5 e ajustar `DEFAULT_HEURISTIC`.
  2. Se **nenhuma** atingir 0,70, usar a análise de erros para propor `heuristic_v2`
     (nova função registrada em `HEURISTICS`, sem apagar a v1, para que todas as versões
     testadas continuem na tabela) e reavaliar. Repetir até atingir a meta.
  3. Para evitar ajuste excessivo às 300 releases, cada refinamento deve ser justificado
     por uma regra geral (e não por um caso isolado); se o grupo preferir, pode-se reservar
     parte dos repositórios só para a avaliação final.
  4. Cada versão testada, mesmo as que falharam, entra na tabela do artigo.

## 5. Resultados da execução real (Issue #62)

Data da execução: `21/10/2026` · commit do código: `11a80a5` · consenso: `validacao/consenso.csv`
(commit `76ff38b`, **consenso automático por maioria, majoritariamente de IA, sem reunião**) · releases no consenso: `300` ·
avaliadas: `298` · excluídas: `2`

Referência (a): o `consenso.csv` inteiro (janela padrão). Os recortes (b1) rótulo humano de Marcela, (b2) consenso nas
mesmas 150 linhas, (c) linhas unânimes e (d) linhas só de IA estão em
[`resultados_avaliacao_heuristica.md`](./resultados_avaliacao_heuristica.md), seção 3.

| Versão          | Regra                                                          | Precisão | Recall |   F1  | N avaliadas | N excluídas |  VP |  FP |  FN |  VN | F1 ≥ 0,70 |
|-----------------|----------------------------------------------------------------|---------:|-------:|------:|------------:|------------:|----:|----:|----:|----:|:---------:|
| v1              | só o patch muda E algum commit cita revert/hotfix/fix          |    0,614 |  0,638 | 0,625 |         298 |           2 |  81 |  51 |  46 | 120 | não       |
| v1_full_message | igual à v1, lendo a mensagem completa (assunto + corpo)        |    0,599 |  0,646 | 0,621 |         298 |           2 |  82 |  55 |  45 | 116 | não       |
| v2              | _(a escrever por Gabriel, pois nenhuma versão atingiu a meta)_ |        _ |      _ |     _ |           _ |           _ |   _ |   _ |   _ |   _ | _         |

Exclusões por motivo: sem arquivo de releases `0` · tag ausente `0` · `status != ok` `2` (`first_release`) ·
sem release anterior `0`.

Contra o **rótulo humano** de Marcela (150 linhas, 30 repositórios): F1 de 0,437 (`v1`) e 0,443 (`v1_full_message`).

**Versão final para o pipeline:** `não definida` (F1 máximo = 0,667, em um recorte; 0,625 na janela padrão). Justificativa:
nenhuma versão atingiu F1 ≥ 0,70 em nenhuma das cinco referências; pela regra da seção 4 (passo 2) o próximo passo é a
`heuristic_v2`. `DEFAULT_HEURISTIC` continua `v1` até lá.

## 6. Estado atual e pendências humanas

Feito: rótulos (#57, #61, #64), kappa e consenso automático (#65, sem reunião), persistência de `dados/releases/` com
mensagens completas e execução real da avaliação (seção 5 e `resultados_avaliacao_heuristica.md`). Pendente:

* `heuristic_v2` por Gabriel (nenhuma versão atingiu 0,70) e reavaliação, de preferência com repositórios reservados só para
  o teste (a v2 será desenhada sobre as mesmas 300 releases);
* decisão da versão final (`DEFAULT_HEURISTIC`), em commit próprio, e registro no artigo;
* reunião de consenso e/ou segunda pessoa rotulando as 150 releases humanas, que reduziria a incerteza da referência;
* o texto do artigo deve citar a referência como consenso automático de avaliadores de IA (com uma avaliadora humana em
  metade da amostra) e reportar as exclusões e o IC95% por repositório.

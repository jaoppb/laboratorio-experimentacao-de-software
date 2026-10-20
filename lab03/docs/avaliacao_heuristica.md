# Avaliação da heurística de release corretiva (Issue #62)

**Código:** `analises/avaliar_heuristica.py` · **Testes:** `tests/test_avaliar_heuristica.py`
**Heurísticas:** `metricas/cfr_b.py` (`HEURISTICS`, `DEFAULT_HEURISTIC`)
**Referência:** `validacao/consenso.csv` (Issue #65) · **Dados de releases:** `dados/releases/*.parquet`

> Este documento descreve a **ferramenta e o protocolo**. Ele não traz números reais: o
> `consenso.csv` e os Parquet de releases só existem depois das etapas humanas (seção 6).
> A tabela da seção 5 é um **modelo** a ser preenchido com a saída real da ferramenta.

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

## 5. Modelo da tabela de resultados (preencher com a saída real)

Data da execução: `__/__/____` · commit do código: `_______` · consenso: `validacao/consenso.csv`
(commit `_______`) · releases no consenso: `300` · avaliadas: `___` · excluídas: `___`

| Versão | Regra                                                          | Precisão | Recall | F1  | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0,70 |
|--------|----------------------------------------------------------------|---------:|-------:|----:|------------:|------------:|---:|---:|---:|---:|:---------:|
| v1     | só o patch muda E algum commit cita revert/hotfix/fix          | _        | _      | _   | _           | _           | _  | _  | _  | _  | _         |
| v2     | _(preencher se a v1 ficar abaixo da meta)_                     | _        | _      | _   | _           | _           | _  | _  | _  | _  | _         |

Exclusões por motivo: sem arquivo de releases `_` · tag ausente `_` · `status != ok` `_` ·
sem release anterior `_`.

**Versão final para o pipeline:** `____` (F1 = `____`). Justificativa: `____`.

## 6. Estado atual e pendências humanas

Nada neste repositório contém resultados reais. Pendente:

* rotulação independente de `rotulos_joao.csv` e `rotulos_gabriel.csv` (#57, #61); já existe `rotulos_marcela.csv` (#64);
* cálculo do kappa, reunião de consenso e commit de `validacao/consenso.csv` (#65);
* persistência de `dados/releases/` da amostra-ouro (`analises.persistir_amostra_ouro`, com token e rede);
* execução real da avaliação e preenchimento da tabela da seção 5;
* se o F1 da v1 for < 0,70: análise de erros, `heuristic_v2` e reavaliação;
* decisão da versão final (`DEFAULT_HEURISTIC`) e registro no artigo.

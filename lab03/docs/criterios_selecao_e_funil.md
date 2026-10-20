# Metodologia de Seleção e Funil de Amostragem (Lab03 - Sprint 1)

**Responsável:** Marcela Campos  
**Referência:** Issue #31 (Gerar funil de seleção automático) e Seção 7 (Requisitos de Engenharia) do [guialab03.md](../guialab03.md).

---

## 1. Etapas do Funil de Seleção

Para construir uma amostra reprodutível de 330 repositórios open-source populares que utilizam esteiras de CI/CD (`amostra.tamanho_final` em `config.yaml`), o pipeline aplica os filtros sequenciais abaixo.

> **O que a primeira linha do funil conta.** O pipeline avalia os candidatos da busca em ordem decrescente de estrelas e **para ao atingir a meta** de repositórios aceitos. Por isso a primeira linha de `funil.csv` (753 na amostra atual) conta os candidatos *avaliados*, e não todos os resultados que a Search API retornaria. Os repositórios que ficaram abaixo do corte de estrelas, depois da meta, não entram na contagem. O rótulo da etapa no CSV traz essa ressalva: "candidatos avaliados até atingir a meta".

1. **Busca Fatiada por Faixas de Estrelas (Search API):**
   - Como a API de busca do GitHub impõe um teto de no máximo 1.000 resultados por consulta, a busca foi fatiada em intervalos de estrelas (`1000..1500`, `1501..2500`, `2501..5000`, `5001..10000`, `>10000`).
   - Repositórios duplicados entre faixas são automaticamente consolidados pela chave única `owner/name`.

2. **Filtro de Uso Ativo de CI/CD (GitHub Actions):**
   - É consultado o endpoint `GET /repos/{owner}/{repo}/actions/workflows`.
   - Se `total_count == 0`, o repositório não utiliza Actions (ou possui workflows desabilitados) e é descartado imediatamente, evitando chamadas desnecessárias de releases e commits.

3. **Critério Mínimo de Releases na Janela de Observação (≥ 5 releases):**
   - Consideram-se apenas **releases publicadas** (`draft = false` e `prerelease = false`) dentro da janela de 12 meses fixada em `config.yaml`.
   - Repositórios com menos de 5 releases publicadas na janela são descartados.

4. **Critério Mínimo de Workflow Runs no Default Branch (≥ 50 runs):**
   - Consideram-se execuções do *default branch* disparadas por evento `push` (`event = push`).
   - Execuções com conclusão `cancelled`, `skipped` ou em andamento são ignoradas.
   - Repositórios com menos de 50 runs válidos na janela são descartados.

5. **Integridade do Clone Local (Git Blobless):**
   - Os commits de cada release vêm de um clone local *blobless*. Repositórios cujo `git clone` falha de forma irrecuperável são descartados (2 na amostra atual).

6. **Critério de Seleção dos 330 Finais:**
   - Dentre todos os repositórios candidatos que atendem a todos os critérios (Actions ativas + ≥ 5 releases + ≥ 50 runs), os **330 repositórios finais são selecionados ordenando-se por maior número de estrelas (popularidade decrescente)**.
   - *Justificativa:* Priorizar os repositórios mais populares garante maior relevância empírica e alinhamento com a Questão de Pesquisa 01 (*"Qual a frequência de deploys dos repositórios populares que usam CI/CD?"*).

---

## 2. Estrutura do Arquivo `dados/funil.csv`

O arquivo gerado automaticamente pelo módulo `pipeline.funnel` contém o formato tabular exigido pela Tabela T4 do artigo:

| Coluna | Descrição |
|---|---|
| `etapa` | Nome descritivo da fase de filtragem |
| `quantidade_restante` | Número de repositórios que avançaram para a próxima fase |
| `descartados` | Quantidade de repositórios excluídos na etapa |
| `motivo_descarte` | Regra operacional que justificou o descarte |

### 2.1 Invariantes de consistência

O funil é sempre aritmeticamente consistente. Isso é garantido por `pipeline.orchestrator.export_funnel_summary` e verificado por testes (`tests/test_funnel.py`, inclusive sobre o `funil.csv` versionado):

- a primeira linha é o total de candidatos avaliados, calculado como **aceitos + todos os descartes** (`count_evaluated_candidates`); ela inclui os repositórios aceitos em execuções anteriores retomadas;
- cada etapa seguinte é igual à anterior menos os descartes da própria etapa;
- a última linha ("Amostra final selecionada") é igual ao tamanho da amostra final (`quantidade_restante` da etapa anterior).

Na amostra atual: 753 avaliados − 56 − 315 − 50 − 2 = 330.

### 2.2 Correção do funil (issue #66)

A versão anterior do `funil.csv` terminava a cadeia em 230, mas a amostra final tem 330 (653 − 423 = 230; 423 descartes + 330 aceitos = 753, ou seja, 100 a mais que a primeira linha).

- **Causa:** o total de avaliados era um contador persistido à parte em `dados/.pipeline_state.json` (arquivo ignorado pelo git). Sem esse arquivo, o contador reiniciava em 0 (o fallback `len(evaluated_names)` nunca era usado, pois `_load_state` já devolvia `total_evaluated = 0`). A coleta de 330 repositórios foi retomada a partir de um dataset com 100 repositórios aceitos (coleta anterior, #47) e, ao ser retomada sem o estado, os 100 aceitos antes da retomada não entraram na contagem; os contadores de descarte (423) vieram só da execução final.
- **Evidência:** o commit `e0f6a4f` (#53) adicionou exatamente 230 linhas a `repositorios.csv` (101 → 331 linhas, nenhuma removida), e 653 = 230 aceitos + 423 descartes da execução final. Os 100 aceitos antes da retomada ficaram fora. O contador de erros de clone caiu de 3 (#47) para 2, o que não ocorreria se os descartes fossem acumulados do estado anterior.
- **Correção no código:** `total_evaluated` deixou de ser persistido; a primeira linha agora é derivada de `aceitos + descartes`.
- **Correção dos dados:** a primeira linha do `funil.csv` foi recalculada como 330 aceitos + 423 descartes = 753, sem nova busca e sem alterar `repositorios.*`. As demais linhas permanecem iguais, exceto os valores restantes (697, 382, 332, 330), obtidos pela subtração dos descartes originais.
- **Limitação:** o estado original não foi versionado, então o mecanismo exato da perda do estado é inferido da aritmética e do histórico do git, não observado diretamente. Existem 3 arquivos em `dados/runs/` sem linha em `repositorios.csv` (`elastic__elasticsearch`, `home-assistant__core`, `ueberdosis__tiptap`), contra 2 erros de clone contados; a diferença não altera os 753, pois a identidade avaliados = aceitos + descartes vale para a execução final.

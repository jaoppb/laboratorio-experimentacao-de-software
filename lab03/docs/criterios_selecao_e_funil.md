# Metodologia de Seleção e Funil de Amostragem (Lab03 - Sprint 1)

**Responsável:** Marcela Campos  
**Referência:** Issue #31 (Gerar funil de seleção automático) e Seção 7 (Requisitos de Engenharia) do [guialab03.md](../guialab03.md).

---

## 1. Etapas do Funil de Seleção

Para construir uma amostra reprodutível de 100 repositórios open-source populares que utilizam esteiras de CI/CD, o pipeline aplica cinco filtros sequenciais:

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

5. **Critério de Seleção dos 100 Finais:**
   - Dentre todos os repositórios candidatos que atendem a todos os critérios (Actions ativas + ≥ 5 releases + ≥ 50 runs), os **100 repositórios finais são selecionados ordenando-se por maior número de estrelas (popularidade decrescente)**.
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

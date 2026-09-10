# Ambiente do Experimento e Métricas Estáticas — Lab02 S01

Entrega do **João Pedro** na Sprint 1: padronização do ambiente experimental,
fixação do assistente de IA, documentação de reprodutibilidade e implementação
do script de métricas estáticas de código para a **RQ3** (Passos 2 e 3 do
[enunciado](enunciado.md), referente à Issue
[#19](https://github.com/jaoppb/laboratorio-experimentacao-de-software/issues/19)).

---

## 1. Padronização do Ambiente Experimental

Para garantir que as comparações entre os tratamentos (**Com IA** vs. **Sem IA /
Manual**) sejam válidas e livres de fatores de confusão decorrentes de tooling
diferente, o grupo adotou um ambiente único e rigorosamente documentado.

### 1.1 Linguagem de Programação

- **Linguagem:** Python 3 (versão `>= 3.12`, ambiente de referência testado em
  Python `3.14.7`).
- **Motivação:** Compatibilidade com a suíte oficial de métricas estáticas
  (`radon` para complexidade McCabe, LOC e Maintainability Index; `jscpd` para
  detecção de duplicação), além de excelente suporte pelos katas (I/O padrão
  `stdin`/`stdout`).

### 1.2 Gerenciador de Dependências e Ambiente Virtual: `uv`

Todas as dependências e ferramentas do projeto são gerenciadas de forma
determinística via [`uv`](https://github.com/astral-sh/uv), garantindo
reprodutibilidade exata em qualquer máquina:

- Arquivo de manifesto: [`lab02/pyproject.toml`](../pyproject.toml)
- Lockfile determinístico: [`lab02/uv.lock`](../uv.lock)

#### Instalação do ambiente

```bash
# 1. Instalar uv (se ainda não possuir)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. A partir da raiz do laboratório ou da pasta lab02:
cd lab02
uv sync
```

O comando `uv sync` criará e sincronizará automaticamente o ambiente virtual
`.venv/` com as versões exatas de `radon`, `pytest` e `ruff`.

---

## 2. Assistente de IA Fixado: Gemini 3.8 Flash

Conforme definido na Issue #19 e no desenho experimental (Passo 1 / Issue #21),
todos os integrantes do grupo utilizam o **mesmo assistente de IA**:

- **Modelo:** `Gemini 3.8 Flash`
- **Fornecedor:** Google DeepMind / Google AI Studio / Google Cloud.

### 2.1 Protocolo de Interação nos Trials "Com IA"

Para evitar viés de histórico acumulado, vazamento de contexto entre katas ou
contaminação de soluções anteriores:

1. **Sessão isolada:** Antes de iniciar cada trial com IA, o participante deve
   abrir uma **nova conversa limpa** (novo chat) no Gemini. Nenhuma mensagem ou
   contexto de katas anteriores pode estar presente no histórico.
2. **Prompt inicial:** O participante fornece apenas o enunciado em português do
   kata (disponível em `katas/<nome-do-kata>/statement.md`).
3. **Proibição de vazamento de testes:** É estritamente vedado colar gabaritos
   ou a suíte completa de testes de aceitação (`test01` a `test20`) no prompt do
   modelo. Apenas os exemplos públicos contidos no enunciado (`statement.md`)
   podem ser compartilhados.
4. **Refinamento interativo:** O participante pode dialogar livremente com o
   modelo para tirar dúvidas, pedir correções de bugs, solicitar explicações ou
   refatorações, desde que dentro do time-box de 35 minutos.

### 2.2 Protocolo para os Trials "Sem IA" (Manual)

Nos trials designados como manuais:

- Todos os recursos de autocompletar baseados em LLMs (como GitHub Copilot,
  Cursor AI, Supermaven, Codeium) **devem estar desativados**.
- É permitido apenas o autocompletar sintático/LSP padrão da IDE (ex: Pyright,
  Jedi) e consulta a documentações oficiais de sintaxe da linguagem (Python
  Docs).

---

## 3. IDE e Configuração de Reprodutibilidade

- **IDEs recomendadas:** VS Code, Cursor, Neovim ou PyCharm.
- **Linter & Formatter:** [`ruff`](https://github.com/astral-sh/ruff),
  configurado em [`pyproject.toml`](../pyproject.toml) com linha máxima de 88
  caracteres.
- **Configuração do interpretador na IDE:** apontar para o virtualenv gerado por
  `uv`: `lab02/.venv/bin/python`.

---

## 4. Ferramentas de Métricas Estáticas (RQ3)

A Questão de Pesquisa **RQ3** investiga: _"O assistente de IA muda a
complexidade, a duplicação ou o tamanho do código?"_

O script [`scripts/collect_metrics.py`](../scripts/collect_metrics.py) coleta de
forma automatizada as seguintes quatro dimensões métricas:

| Dimensão             | Métrica                                                   | Ferramenta                                 | Interpretação                                                                                                                                                                                                 |
| -------------------- | --------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LOC** (Controle)   | `loc`, `sloc`, `lloc`, comentários, vazias                | `radon.raw`                                | **Métrica de controle obrigatória**. LOC mede tamanho bruto; SLOC exclui comentários e linhas vazias; LLOC mede instruções lógicas. Evita conclusões distorcidas de verbosidade gerada por IA.                |
| **Complexidade**     | Complexidade Ciclomática média por função/método (McCabe) | `radon.complexity`                         | Média do número de caminhos linearmente independentes no grafo de fluxo de controle por função. Para scripts procedurais sem funções, calcula o CC no corpo do módulo via AST.                                |
| **Duplicação**       | % de Linhas Duplicadas e contagem de clones               | `jscpd` (com fallback nativo `python-cpd`) | Percentual de linhas que pertencem a blocos de código repetidos ($\ge 4$ linhas). O script executa `jscpd` via CLI e faz fallback transparente para detector Python nativo se Node.js não estiver disponível. |
| **Manutenibilidade** | Índice de Manutenibilidade (MI) e Rank (A/B/C)            | `radon.metrics`                            | Métrica composta: $MI = 171 - 5.2 \ln(V) - 0.23 CC - 16.2 \ln(LOC)$. Escala de 0 a 100 (Rank A: $\ge 20$).                                                                                                    |

---

## 5. Como Usar o Script de Métricas (`collect_metrics.py`)

### 5.1 Execução Básica (Tabela no Terminal)

Análise de um único arquivo de solução:

```bash
uv run python scripts/collect_metrics.py katas/gabaritos/01-bario-world.py
```

Análise de uma pasta inteira de soluções (ex.: gabaritos ou pasta de trials):

```bash
uv run python scripts/collect_metrics.py katas/gabaritos/
```

**Exemplo de saída no terminal:**

```text
=== Relatório de Métricas Estáticas (Lab02 — RQ3) ===

Arquivo / Kata                   | LOC   | SLOC  | CC Médio | CC Max | Funções | % Duplicada | MI   | Rank MI | Tool Dupl.
---------------------------------+-------+-------+----------+--------+---------+-------------+------+---------+-----------
01-bario-world                   | 46    | 38    | 7.00     | 12     | 2       | 0.0%        | 55.2 | A       | jscpd
02-cards                         | 36    | 29    | 6.00     | 6      | 1       | 0.0%        | 52.8 | A       | jscpd
03-exploring-terrain             | 52    | 45    | 10.00    | 10     | 1       | 0.0%        | 44.3 | A       | jscpd
04-garment-groups                | 3     | 3     | 1.00     | 1      | 0       | 0.0%        | 84.7 | A       | jscpd
05-dish-rack                     | 65    | 49    | 4.67     | 7      | 3       | 0.0%        | 54.2 | A       | jscpd
06-n-checkers                    | 39    | 31    | 5.00     | 5      | 1       | 0.0%        | 48.9 | A       | jscpd
```

### 5.2 Exportação para CSV com Metadados (Para Análise da Sprint 3)

Na Sprint 2 (Execução) e Sprint 3 (Análise Estatística com Wilcoxon), os dados
precisam estar etiquetados com participante, tratamento e kata. O script aceita
esses metadados via flags:

```bash
uv run python scripts/collect_metrics.py solucao_trial.py \
  --format csv \
  --participant joao \
  --treatment ai \
  --kata 01-bario-world \
  --trial-id trial-01 \
  -o resultados/trial_01.csv
```

### 5.3 Exportação em JSON Estruturado

```bash
uv run python scripts/collect_metrics.py katas/gabaritos/ --format json -o metricas_gabaritos.json
```

### 5.4 Forçar Engine de Duplicação (jscpd ou Fallback Python)

```bash
# Força o motor nativo em Python (sem dependência de Node/npx)
uv run python scripts/collect_metrics.py katas/gabaritos/ --engine python

# Ajusta o limiar de linhas para clone (padrão: 4 linhas)
uv run python scripts/collect_metrics.py katas/gabaritos/ --min-lines 3
```

---

## 6. Testes Automatizados

A robustez do coletor de métricas foi verificada por testes automatizados em
[`tests/test_collect_metrics.py`](../tests/test_collect_metrics.py):

- Verificação de cálculo de LOC, SLOC, comentários e linhas em branco.
- Verificação da complexidade ciclomática média, máxima e por função.
- Suporte a scripts procedural/top-level sem declaração de funções (AST
  visitor).
- Teste de detecção de duplicação em código limpo vs. código com clones
  intencionais.
- Teste de conformidade dos 6 gabaritos oficiais da Maratona Mineira de
  Programação 2026.
- Validação das saídas em formatos Table, JSON e CSV.

Para executar os testes:

```bash
cd lab02
uv run pytest -v
```

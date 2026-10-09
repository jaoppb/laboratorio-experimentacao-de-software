# Lab03 - Mineração de Métricas DORA em Repositórios Open-Source

Este projeto implementa um pipeline reprodutível para mineração e análise empírica das métricas **DORA** (*DevOps Research and Assessment*) em repositórios open-source populares no GitHub que utilizam CI/CD (GitHub Actions).

---

## 📄 Artigo Científico (Template SBC)
- **Link do projeto no Overleaf:** `[Inserir link do projeto Overleaf compartilhado]`
- O artigo segue o modelo da SBC (Sociedade Brasileira de Computação) e inclui a introdução com as hipóteses teóricas e empíricas da Sprint 01.

---

## 🚀 Como Rodar do Zero

O projeto utiliza o gerenciador de pacotes e ambientes virtuais [uv](https://github.com/astral-sh/uv) e Python 3.12+.

### 1. Clonar o repositório e entrar na pasta do laboratório
```bash
git clone https://github.com/jaoppb/laboratorio-experimentacao-de-software.git
cd laboratorio-experimentacao-de-software/lab03
```

### 2. Instalar dependências e preparar o ambiente
```bash
uv sync
```

### 3. Configurar token de acesso ao GitHub
Para executar a coleta com a API REST do GitHub sem ser bloqueado pelos limites de requisição (*rate limit*), defina a variável `GITHUB_TOKEN`:

- **Linux / macOS (Bash):**
  ```bash
  export GITHUB_TOKEN="seu_personal_access_token"
  # Ou utilize o token autenticado pelo GitHub CLI:
  export GITHUB_TOKEN=$(gh auth token)
  ```
- **Windows (PowerShell):**
  ```powershell
  $env:GITHUB_TOKEN = "seu_personal_access_token"
  ```

*(Nota: O cliente também detecta automaticamente o token via `gh auth token` se a ferramenta GitHub CLI estiver instalada e autenticada no sistema).*

---

## ⚙️ Execução do Pipeline

A coleta completa e consolidação dos dados é executada com um único comando a partir da pasta `lab03`:

```bash
uv run python -m pipeline --config config.yaml
```

O comando executa automaticamente todo o fluxo:
1. **Seleção de candidatos:** Busca fatiada por estrelas (`>10000`, `5001..10000`, etc.) na Search API.
2. **Filtro de CI/CD:** Descarta repositórios sem workflows de GitHub Actions.
3. **Filtro de Releases:** Coleta releases e exige $\ge 5$ releases publicadas na janela de 12 meses.
4. **Filtro de Workflow Runs:** Coleta execuções de push no default branch e exige $\ge 50$ runs válidos.
5. **Metadados e Commits:** Coleta estrelas, linguagem, contribuidores e commits entre releases consecutivas.
6. **Cálculo de Métricas DORA:** Computa Deployment Frequency, Lead Time (a) e (b), Change Failure Rate (CFR a) e Tempo de Recuperação, além do tier DORA final.
7. **Exportação e Funil:** Salva incrementalmente `dados/repositorios.parquet`, `dados/repositorios.csv`, `dados/funil.csv` e `dados/runs/*.parquet`.

### Execução com Amostra Reduzida (`--limit`)
Para validar o pipeline ou realizar testes rápidos, utilize o argumento `--limit`:

```bash
uv run python -m pipeline --config config.yaml --limit 3
```

---

## 🔄 Testando a Retomada (Resumption)

O pipeline implementa tolerância a falhas através de dois níveis de persistência:
1. **Cache HTTP em SQLite (WAL mode):** Todas as respostas 2xx da API são persistidas imediatamente em `cache/http_cache.sqlite`.
2. **Checkpoint Incremental do Dataset:** Cada repositório qualificado é salvo em `dados/repositorios.parquet` assim que concluído.

### Procedimento para testar a retomada:
1. Inicie a execução:
   ```bash
   uv run python -m pipeline --limit 5
   ```
2. Após o primeiro repositório ser aceito, pressione `Ctrl+C` no terminal para interromper a execução no meio.
3. Observe que o repositório aceito já foi gravado em `dados/repositorios.parquet` e `dados/repositorios.csv`.
4. Execute novamente o comando:
   ```bash
   uv run python -m pipeline --limit 5
   ```
5. O pipeline detectará os repositórios já processados, ignorará o reprocessamento de rede para eles e continuará a coleta a partir do próximo candidato até atingir o limite estipulado.

---

## 🧪 Testes Automatizados e Cobertura

Os testes unitários e de integração cobrem o cliente HTTP, paginação Link, backoff exponencial, cálculo de métricas DORA, funil de seleção e o fluxo ponta a ponta com retomada:

```bash
uv run python -m pytest --cov=metricas --cov=pipeline --cov-report=term-missing --cov-fail-under=80
```

---

## 📁 Estrutura de Diretórios e Artefatos

```text
lab03/
├── config.yaml               # Configurações do pipeline (janela, limites e filtros)
├── pyproject.toml            # Dependências gerenciadas via uv
├── README.md                 # Guia de execução do zero e documentação do projeto
├── dados/                    # Diretório de saída dos dados (ignorado no git com exceção do funil/README)
│   ├── README.md             # Dicionário de dados completo de todas as colunas e métricas
│   ├── funil.csv             # Tabela do funil de amostragem com contagens e descartes (T4)
│   ├── repositorios.parquet  # Dataset consolidado em formato Parquet columnar (Snappy)
│   ├── repositorios.csv      # Dataset consolidado em CSV para replicação cruzada
│   └── runs/                 # Execuções brutas de workflow por repositório ({owner}__{repo}.parquet)
├── cache/                    # Cache local SQLite das requisições HTTP (ignorado no git)
├── pipeline/                 # Módulos do pipeline de extração e orquestração
│   ├── __main__.py           # Ponto de entrada CLI (python -m pipeline)
│   ├── orchestrator.py       # Orquestrador do fluxo ponta a ponta e checkpoints
│   ├── http_client.py        # Cliente HTTP com paginação Link, rate limit e backoff
│   ├── cache.py              # Cache em disco SQLite com WAL mode
│   ├── repo_selector.py      # Busca por estrelas e validação de Actions
│   ├── metadata.py           # Coleta de metadados e contagem de contribuidores
│   ├── releases.py           # Coleta de releases, tags e filtragem de janela
│   ├── commits.py            # Coleta de commits entre releases (compare)
│   ├── workflow_runs.py      # Coleta de runs com bissecção e armazenamento Parquet
│   └── funnel.py             # Rastreamento e exportação do funil de seleção
├── metricas/                 # Funções de cálculo das métricas DORA
│   ├── schemas.py            # Dataclasses tipadas (Repo, Release, Commit, WorkflowRun)
│   ├── dora.py               # Deployment Frequency e classificação DORA (RQ01 e tiers)
│   ├── lead_time.py          # Lead Time variantes (a) e (b) (RQ02)
│   └── stability.py          # CFR variante (a) e Tempo de Recuperação (RQ03a e RQ04)
└── tests/                    # Suíte de testes automatizados com fixtures e mocks
    ├── test_pipeline_integration.py # Testes de integração E2E e retomada
    ├── test_lead_time.py
    ├── test_cfr_recovery.py
    ├── test_dora.py
    ├── test_releases.py
    ├── test_commits.py
    ├── test_workflow_runs.py
    ├── test_repo_selector.py
    ├── test_metadata.py
    ├── test_funnel.py
    ├── test_cache.py
    └── test_http_client.py
```

Para mais detalhes sobre as colunas e fórmulas das métricas DORA, consulte o [Dicionário de Dados](file:///home/jao/facul/Experimenta%C3%A7%C3%A3o/laboratorio-experimentacao-de-software/lab03/dados/README.md).

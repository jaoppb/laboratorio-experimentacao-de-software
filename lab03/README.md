# Lab03 - Mineração de Métricas DORA em Repositórios Open-Source

Este projeto implementa um pipeline reprodutível para mineração e análise empírica das métricas **DORA** (*DevOps Research and Assessment*) em repositórios open-source populares no GitHub que utilizam CI/CD (GitHub Actions).

---

## 📄 Artigo Científico (Template SBC)
- **Link do projeto no Overleaf:** `[Inserir link do projeto Overleaf compartilhado]`
- O artigo segue o modelo da SBC (Sociedade Brasileira de Computação) e inclui a introdução com as hipóteses teóricas e empíricas da Sprint 01.

---

## 🚀 Requisitos e Configuração

O projeto utiliza o gerenciador de pacotes e ambientes virtuais [uv](https://github.com/astral-sh/uv) e Python 3.12+.

### 1. Clonar o repositório e entrar na pasta
```bash
cd lab03
```

### 2. Instalar dependências
```bash
uv sync
```

### 3. Configurar token de acesso ao GitHub
Para executar a coleta com a API REST do GitHub sem ser bloqueado pelos limites de requisição (*rate limit*), defina a variável `GITHUB_TOKEN`:

- **Windows (PowerShell):**
  ```powershell
  $env:GITHUB_TOKEN = "seu_personal_access_token"
  ```
- **Linux / macOS (Bash):**
  ```bash
  export GITHUB_TOKEN="seu_personal_access_token"
  ```

*(O token nunca deve ser versionado no Git; a pasta `cache/` e arquivos `.env` já estão inclusos no `.gitignore`)*.

---

## ⚙️ Execução do Pipeline

A coleta e geração dos artefatos é executada com um único comando a partir da raiz do laboratório:

```bash
uv run python -m pipeline --config config.yaml
```

O arquivo `config.yaml` parametriza:
- **Janela de observação:** 12 meses definidos no experimento (`inicio` e `fim`).
- **Amostra:** Critério de 100 repositórios finais.
- **Critérios de inclusão mínima:** `>= 5` releases publicadas e `>= 50` workflow runs válidos no default branch.
- **Busca fatiada:** Faixas de estrelas para contornar o limite de 1.000 resultados da Search API.

---

## 🧪 Testes Automatizados e Cobertura

Os testes unitários cobrem a camada de cliente HTTP, seleção de repositórios, metadados, funil e o cálculo das métricas DORA:

```bash
uv run python -m pytest --cov=metricas --cov-report=term-missing --cov-fail-under=80
```

---

## 📁 Estrutura do Projeto

```text
lab03/
├── config.yaml               # Configurações do pipeline (janela, limites e filtros)
├── pyproject.toml            # Dependências gerenciadas via uv
├── .python-version           # Versão padrão do Python
├── README.md                 # Documentação e instruções de execução
├── dados/                    # Dados coletados, funil de seleção e datasets finais
│   └── funil.csv             # Registro do funil de seleção com contagens e descartes
├── cache/                    # Cache local das requisições da API (ignorado pelo git)
├── pipeline/                 # Módulos de coleta e orquestração
│   ├── __main__.py           # Ponto de entrada CLI (python -m pipeline)
│   ├── http_client.py        # Cliente HTTP com paginação Link, rate limit e backoff
│   ├── repo_selector.py      # Busca por estrelas e validação de Actions
│   ├── metadata.py           # Coleta de metadados e contagem de contribuidores
│   └── funnel.py             # Rastreamento e exportação do funil de seleção
├── metricas/                 # Funções de cálculo e regras operacionais DORA
│   ├── __init__.py           # Exportação das métricas
│   ├── schemas.py            # Dataclasses tipadas (Repo, Release, Commit, WorkflowRun)
│   ├── dora.py               # Deployment Frequency e classificação DORA (RQ01, faixas e notas)
│   └── stability.py          # CFR (a) e Tempo de Recuperação (RQ03a e RQ04)
└── tests/                    # Suíte de testes automatizados com fixtures e casos de borda
    ├── test_cfr_recovery.py
    ├── test_dora.py
    ├── test_http_client.py
    └── test_pipeline_components.py
```

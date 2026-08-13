# Lab01 - Características de repositórios populares + Setup do Kanban

**Status:** Em andamento

## Objetivo
Estudar características de sistemas populares open-source (top 1000 repositórios
com mais estrelas no GitHub) através de 7 Questões de Pesquisa (RQs), além de
configurar o processo (GitHub Projects) que será usado pelo grupo durante o
semestre.

## Estrutura

```
lab01/
├── main.py              # ponto de entrada: roda as extrações via CLI
├── pyproject.toml       # dependências do projeto (gerenciadas via uv)
├── uv.lock
├── queries/             # queries GraphQL (.graphql) e resultados brutos (.json)
│   ├── rq01.graphql ... rq06.graphql
│   └── unified.graphql  # query unificada (todas as RQs de uma vez)
├── src/                 # código-fonte da aplicação
│   ├── config.py         # configurações (tokens, URL da API, etc.)
│   ├── github_client.py  # cliente de conexão com a API GraphQL do GitHub
│   ├── query.py
│   ├── query_loader.py   # carrega os arquivos .graphql do disco
│   ├── query_runner.py   # executa as queries
│   └── token_manager.py  # gerencia múltiplos tokens (rate limit)
└── dados/               # CSVs gerados pela extração
    ├── rq01_sample.csv ... rq06_sample.csv
    ├── rq03_rq04_sample.csv, rq05_rq06_sample.csv
    ├── unified_sample.csv
    └── all_results.csv  # merge de todos os resultados
```

## Como rodar

Este projeto usa [uv](https://docs.astral.sh/uv/) para gerenciamento de
dependências. Instale o `uv` antes de continuar.

```bash
cd lab01
uv sync
```

Rodar uma extração específica:
```bash
uv run main.py --rq 1        # roda apenas RQ01
uv run main.py --rq all      # roda todas as RQs (1 a 6)
uv run main.py --rq unified  # roda a query unificada
uv run main.py --rq all --merge  # roda todas e junta em all_results.csv
```

É necessário um GitHub Token com escopo `public_repo`, definido no arquivo
`.env` na raiz do projeto:
```
GITHUB_TOKEN=seu_token_aqui
```

## Sprints
- **S01:** Consulta GraphQL para 100 repositórios + GitHub Projects criado
- **S02:** Paginação (1000 repositórios) + primeira versão do relatório
- **S03:** Análise e visualização de dados para as 7 RQs
- **Relatório Final:** documento consolidado

## Snapshot do board
O script que gera o snapshot do GitHub Projects (usado para acompanhar a
evolução semanal do Kanban) está em `board-snapshots/`, na raiz do
repositório — não é específico deste lab, pois é reutilizado durante todo o
semestre.

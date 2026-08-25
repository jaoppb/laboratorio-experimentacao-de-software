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
├── dados/               # CSVs gerados pela extração
│   ├── rq01_sample.csv ... rq06_sample.csv
│   ├── rq03_rq04_sample.csv, rq05_rq06_sample.csv
│   ├── unified_sample.csv
│   ├── unified_sample.parquet  # unified_sample.csv convertido (scripts/csv_to_parquet.py)
│   └── all_results.csv  # merge de todos os resultados
├── scripts/
│   └── csv_to_parquet.py  # converte unified_sample.csv -> .parquet para o dashboard
└── dashboard/           # dashboard (RQ01-RQ07), lê o .parquet ao vivo no navegador
    ├── index.html
    ├── styles.css
    ├── dashboard.js
    ├── package.json      # dependência: hyparquet (leitor de Parquet em JS puro)
    └── node_modules/     # gerado por `npm install` (não versionado)
```

### Dashboard (Lab01S03)
As 7 RQs têm um dashboard visual em `dashboard/`. Ele busca
`unified_sample.parquet` **direto do GitHub** (`raw.githubusercontent.com`,
branch `main`) via `fetch()` e recalcula todas as estatísticas em JavaScript
no navegador — nenhum número fica hardcoded. Por isso o `.parquet` é
commitado como blob normal do Git (não LFS: `raw.githubusercontent.com`
serve o ponteiro LFS, não o binário, para arquivos rastreados por LFS).
```bash
cd lab01/dashboard
npm install              # baixa o hyparquet (só precisa rodar uma vez)
python3 -m http.server 8000
# abrir http://localhost:8000
```
Para regenerar o `.parquet` após atualizar o CSV: `uv run scripts/csv_to_parquet.py`
(a partir de `lab01`), depois commitar e dar push — o dashboard sempre lê o
arquivo que está no branch `main` do GitHub, não uma cópia local.

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

# Lab04 — Testes de Hipótese por Dentro: Cenário, Simulação e Visualização

**Sprint 1:** Cenário, dados reais, simulação e visualização (G1 e G2 no dashboard).

## Descrição do Laboratório e Par de Testes

O objetivo deste laboratório é compreender o funcionamento interno e os limites práticos de testes de hipótese comparando dois métodos aplicados a uma mesma pergunta de Engenharia de Software.

- **Par escolhido:** **P1** — Teste $t$ de Welch (paramétrico para médias com variâncias heterogêneas) × Teste de Mann-Whitney $U$ (não paramétrico para postos e dominância estocástica).
- **Cenário:** Tempo até o merge de Pull Requests (em horas), comparando PRs revisados pelo bot **CodeRabbit** (`com_bot`) com PRs não revisados por bot (`sem_bot`).
- **Hipóteses:** Teste bicaudal ($\alpha = 0,05$), avaliando se há diferença no tempo de merge entre os grupos.
- **Distribuição na simulação:** Lognormal com parâmetros de localização (mediana) e escala ($\sigma_{\log}$) calibrados a partir dos dados reais coletados.
- **Semente fixa:** `numpy.random.default_rng(42)`, garantindo reprodução determinística byte a byte.

## Dados Reais

- **Fonte:** Repositório público [tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss).
- **Amostra:** 60 PRs mergeados (30 `com_bot` e 30 `sem_bot`).
- Para detalhes metodológicos completos sobre as janelas temporais e critérios de exclusão, consulte [dados/reais/FONTE.md](dados/reais/FONTE.md).

## Comando Único de Execução

Para rodar todo o pipeline da Sprint 1 do início ao fim (atualização da simulação, geração dos gráficos G1 e G2 e escrita da página estática do dashboard), execute a partir da pasta `lab04/`:

```bash
uv run python scripts/gerar_dashboard.py
```

O comando gera o arquivo `dashboard/index.html`, que pode ser aberto diretamente em qualquer navegador sem a necessidade de servidor web ou conexão com a internet.

## Como Rodar a Suíte de Testes

Os testes unitários e de integração são gerenciados com `pytest`:

```bash
uv run pytest
```

## Estrutura de Pastas

```text
lab04/
├── dados/
│   ├── parametros.json         # Parâmetros estimados dos dados reais
│   ├── reais/                  # pr_merge_time.csv e FONTE.md
│   └── simulado/               # exemplo.csv e exemplo_resultado.json
├── dashboard/
│   └── index.html              # Página web do dashboard (gerada por código)
├── docs/                       # Enunciado, decisões, cenário e interpretações
├── scripts/
│   ├── coletar_prs.py          # Coleta via GitHub CLI (executada na fase de dados)
│   ├── estimar_parametros.py   # Estimação dos parâmetros lognormais
│   ├── exemplo_simulado.py     # Execução do exemplo simulado (semente 42)
│   └── gerar_dashboard.py      # Comando único do laboratório
├── src/
│   ├── dashboard/              # Gerador de HTML do dashboard estático
│   ├── graficos/               # Módulos dos gráficos G1 e G2 (Plotly e Matplotlib)
│   ├── estilo.py               # Paleta de cores e padronização visual (Okabe-Ito)
│   ├── simulacao.py            # Geração de dados sintéticos lognormais
│   └── testes.py               # Implementação do teste t de Welch e Mann-Whitney
├── tests/                      # Suíte de testes automatizados com pytest
├── pyproject.toml              # Metadados e dependências gerenciadas pelo uv
└── uv.lock                     # Lockfile do uv garantindo reprodutibilidade
```

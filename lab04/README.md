# Lab04 — Testes de Hipótese por Dentro: Cenário, Simulação e Visualização

**Estado final:** dados reais, cenário, simulações Q1, Q2 e Q3 e dashboard completo com os gráficos G1 a G4 (Sprints 1 e 2 e entrega final).

- **Dashboard publicado:** <https://jaoppb.github.io/laboratorio-experimentacao-de-software/lab04/>
- **Repositório:** <https://github.com/jaoppb/laboratorio-experimentacao-de-software>
- **GitHub Projects:** <https://github.com/users/jaoppb/projects/3/views/1>

## Descrição do Laboratório e Par de Testes

O objetivo deste laboratório é compreender o funcionamento interno e os limites práticos de testes de hipótese comparando dois métodos aplicados a uma mesma pergunta de Engenharia de Software.

- **Par escolhido:** **P1** — Teste $t$ de Welch (paramétrico para médias com variâncias heterogêneas) × Teste de Mann-Whitney $U$ (não paramétrico para postos e dominância estocástica).
- **Cenário:** Tempo até o merge de Pull Requests (em horas), comparando PRs revisados pelo bot **CodeRabbit** (`com_bot`) com PRs não revisados por bot (`sem_bot`). Detalhes em [docs/cenario.md](docs/cenario.md).
- **Hipóteses:** Teste bicaudal ($\alpha = 0,05$), avaliando se há diferença no tempo de merge entre os grupos.
- **Distribuição na simulação:** Lognormal com parâmetros de localização (mediana) e escala ($\sigma_{\log}$) calibrados a partir dos dados reais coletados.
- **Semente fixa:** `numpy.random.default_rng(42)`, garantindo reprodução determinística byte a byte.

## Perguntas respondidas pela simulação

| Pergunta | O que mede | Script | Saída |
|---|---|---|---|
| Q1 | Erro tipo I (H₀ verdadeira, 10.000 repetições) | `scripts/simular_q1.py` | `dados/simulado/q1_erro_tipo1.csv` |
| Q2 | Poder com efeitos crescentes (razão de medianas de 1,0 a 8,0) | `scripts/simular_q2.py` | `dados/simulado/q2_poder.csv` |
| Q3 | Erro tipo I e poder com violação dos pressupostos (n pequeno, assimetria extrema, outliers); ver [docs/violacoes_q3.md](docs/violacoes_q3.md) | `scripts/simular_q3.py` | `dados/simulado/q3_erro_tipo1.csv` e `q3_poder.csv` |

Gráficos: **G1** (dados reais × simulados), **G2** (estatística sob H₀ e p-valor), **G3** (erro tipo I em cada situação, Q1 e Q3) e **G4** (curvas de poder, Q2 e Q3).

## Dados Reais

- **Fonte:** Repositório público [tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss).
- **Amostra:** 60 PRs mergeados (30 `com_bot` e 30 `sem_bot`).
- Para detalhes metodológicos completos sobre as janelas temporais e critérios de exclusão, consulte [dados/reais/FONTE.md](dados/reais/FONTE.md).

## Comando Único de Execução

A partir da pasta `lab04/` (requer [uv](https://docs.astral.sh/uv/)), o comando abaixo refaz **tudo** do início ao fim com semente fixa: testes nos dados reais, simulações Q1, Q2 e Q3 e geração do dashboard (leva alguns minutos por causa das 10.000 repetições).

```bash
uv run python scripts/reproduzir_tudo.py
```

O resultado final é `dashboard/index.html`, que abre diretamente em qualquer navegador, sem servidor web nem internet (o Plotly.js vai embutido na página).

Como a semente é fixa, rodar o comando duas vezes (ou em um clone limpo) gera os mesmos arquivos: `git status` não deve mostrar mudanças em `dados/` nem em `dashboard/`.

### Só o dashboard (rápido)

Os CSVs das simulações já estão versionados. Para apenas regenerar a página a partir deles:

```bash
uv run python scripts/gerar_dashboard.py
```

Este é o comando usado pelo workflow de GitHub Pages.

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
│   ├── reais/                  # pr_merge_time.csv, FONTE.md e resultado_testes.json
│   └── simulado/               # exemplo, q1_erro_tipo1, q2_poder, q3_erro_tipo1 e q3_poder
├── dashboard/
│   └── index.html              # Página web do dashboard (gerada por código)
├── docs/                       # Enunciado, decisões, cenário, interpretações e roteiro oral
├── scripts/
│   ├── coletar_prs.py          # Coleta via GitHub CLI (executada na fase de dados)
│   ├── estimar_parametros.py   # Estimação dos parâmetros lognormais
│   ├── exemplo_simulado.py     # Execução do exemplo simulado (semente 42)
│   ├── testar_dados_reais.py   # Welch e Mann-Whitney nos dados reais
│   ├── simular_q1.py           # Q1: erro tipo I
│   ├── simular_q2.py           # Q2: poder
│   ├── simular_q3.py           # Q3: violações dos pressupostos
│   ├── gerar_dashboard.py      # Gera apenas o dashboard a partir dos arquivos versionados
│   └── reproduzir_tudo.py      # Comando único: reproduz tudo e gera o dashboard
├── src/
│   ├── dashboard/              # Gerador de HTML do dashboard estático
│   ├── graficos/               # G1, G2, G3 e G4 (Plotly e Matplotlib)
│   ├── estilo.py               # Paleta de cores e padronização visual (Okabe-Ito)
│   ├── montecarlo.py           # Repetições de Monte Carlo e taxa de rejeição
│   ├── simulacao.py            # Geração de dados sintéticos lognormais
│   └── testes.py               # Implementação do teste t de Welch e Mann-Whitney
├── tests/                      # Suíte de testes automatizados com pytest
├── pyproject.toml              # Metadados e dependências gerenciadas pelo uv
└── uv.lock                     # Lockfile do uv garantindo reprodutibilidade
```

# Decisões do grupo e divisão de tarefas

## Decisões

- **Par de testes:** P1 — t de Welch × Mann-Whitney.
- **Cenário:** tempo até o merge de PRs, com e sem bot de revisão.
- **Dados reais:** ~30 PRs com bot e ~30 sem bot.
- **Simulação:** lognormal (o tempo de merge é assimétrico).
- **Semente fixa:** `numpy.random.default_rng(42)`.
- Tudo fica em `lab04/`, e cada integrante mexe só nos seus arquivos.
- `dados/reais/pr_merge_time.csv` (Gabriel): colunas `repo, pr_number, grupo, tempo_merge_horas, url`; `grupo` é `com_bot` ou `sem_bot`.
- `dados/parametros.json` (Gabriel): `{"com_bot": {"n", "mediana", "sigma_log"}, "sem_bot": {...}}`.
- João usa valores provisórios (mediana 10 h, sigma 1,0) até o `parametros.json` chegar.
- Funções de gráfico devolvem `plotly.graph_objects.Figure`.
- **Todo commit cita o número da Issue** (ex.: `#12 adiciona gerador`). Sem isso o professor não conta.

## Gabriel — dados reais e cenário

- Coletar ~30 PRs com bot e ~30 sem bot (mesmo repo ou repos comparáveis). Entregar `pr_merge_time.csv` e `dados/reais/FONTE.md` (repositório, qual bot, data, como foi anotado).
- `scripts/estimar_parametros.py`: lê o CSV e gera `parametros.json`; imprime assimetria, mediana, outliers e n por grupo.
- `docs/cenario.md`: pergunta em uma frase, H0 e H1 (uni ou bicaudal), distribuição escolhida e por quê, e qual teste se espera que se saia melhor, com o motivo.
- ⚠️ Commitar o cenário com a expectativa **antes** de o João rodar qualquer simulação.
- Se não achar um repo com PRs com e sem bot comparáveis em 1 ou 2 dias, avisar: o plano B muda o par.

## João — simulação, testes e G2

- `src/simulacao.py`: `gerar_dados(rng, n_a, n_b, mediana_a, mediana_b, sigma_a, sigma_b)` → dois arrays lognormais.
- `src/testes.py`: `aplicar_welch(a, b)` e `aplicar_mannwhitney(a, b)`, cada uma devolvendo dict com `estatistica, p_valor, tamanho_efeito, alternativa` (rápidas e sem efeito colateral, reusadas nas 10.000 repetições).
- `scripts/exemplo_simulado.py`: semente 42, aplica os dois testes, salva `dados/simulado/exemplo.csv` e `exemplo_resultado.json`. Interpretação em `docs/interpretacao_exemplo.md` (Mann-Whitney compara postos/dominância estocástica, não medianas).
- G2 em `src/graficos/g2.py`, `figura_g2(...)`.
- Testes unitários com pytest (`tests/test_simulacao.py`, `tests/test_testes.py`).

## Marcela

- Estrutura do lab04: `pyproject.toml`, `config.yaml` e README com o comando único.
- G1 em `src/graficos/g1.py` (dados reais do Gabriel + simulados do João).
- Dashboard com o topo (links) e seções 1 a 3, com G1 e G2 e textos de 2 a 4 frases.
- Issues no GitHub Projects com Assignee e conferência dos commits.
- Rodar tudo do início ao fim com um comando e conferir a reprodução.

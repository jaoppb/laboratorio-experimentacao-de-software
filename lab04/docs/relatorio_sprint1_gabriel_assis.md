# Relatório individual — Lab04S01

**Integrante:** Gabriel Assis de Souza (@GabriAssiss)
**Sprint:** Lab04S01 — dados reais, cenário, simulação e G1/G2
**Papel na divisão do grupo:** dados reais e cenário

## 1. Escopo

| Issue | Título | Artefato |
|---|---|---|
| #102 | Coletar PRs reais com e sem bot (CSV + FONTE.md) | `scripts/coletar_prs.py`, `dados/reais/pr_merge_time.csv`, `dados/reais/FONTE.md` |
| #103 | Estimar parâmetros da simulação a partir dos dados reais | `scripts/estimar_parametros.py`, `dados/parametros.json` |
| #104 | Escrever o cenário (H0/H1, distribuição e expectativa) | `docs/cenario.md`, `docs/enunciado.md`, `docs/decisoes_do_grupo.md` |

Fora do escopo do Gabriel (João e Marcela): `src/simulacao.py`, `src/testes.py`, `scripts/exemplo_simulado.py`, G1, G2, dashboard e estrutura do projeto.

## 2. #102 — Dados reais

### 2.1 Busca do repositório

O cenário pede PRs com e sem bot de revisão em repositórios comparáveis. Testei vários repositórios públicos populares:

- **openreplay:** vários bots (Greptile, Cubic), mas o time faz merge dos próprios PRs em segundos (mediana de minutos), o que mascara qualquer efeito.
- **dotnet/aspire, microsoft/vscode, home-assistant/frontend:** o Copilot revisa quase 100% dos PRs, sem grupo de controle no mesmo período.
- **Outros (pandas, scikit-learn, cpython, airflow, godot, kubernetes, pytorch...):** sem bot de revisão relevante.
- **tailwindlabs/tailwindcss:** adoção nítida. Nenhum PR com CodeRabbit até ago/2025 e quase todos a partir de dez/2025. Tempos de merge assimétricos e variados. **Escolhido.**

### 2.2 Desenho e coleta

`scripts/coletar_prs.py` (CLI `gh`, só biblioteca padrão) busca os PRs mergeados via GraphQL e:

- descarta rascunhos e autores que não são usuários (Dependabot etc.);
- `sem_bot`: criados entre 2025-01-01 e 2025-08-31;
- `com_bot`: criados desde 2025-12-01, com comentário/review do `coderabbitai` antes do merge;
- sorteia 30 PRs por grupo entre os elegíveis (240 com bot, 349 sem bot), com `random.Random(42)`;
- `tempo_merge_horas = mergedAt − createdAt`.

Saída: `pr_merge_time.csv` (60 linhas; colunas `repo, pr_number, grupo, tempo_merge_horas, url`). Fonte, método e limitações em `FONTE.md`.

### 2.3 Limitação principal

Os grupos são de períodos diferentes (antes × depois do bot): a comparação é observacional e o efeito do bot se mistura com mudanças no projeto ao longo do tempo. Os dados servem para calibrar a simulação e ilustrar os testes, não para provar causalidade.

## 3. #103 — Parâmetros da simulação

`scripts/estimar_parametros.py` lê o CSV, imprime n, mediana, média, assimetria (bruta e do log) e outliers de Tukey por grupo, e grava `dados/parametros.json` com `{"com_bot"|"sem_bot": {"n", "mediana", "sigma_log"}}`. Numa lognormal, mediana = e^μ e σ_log = desvio-padrão de ln(tempo).

| Grupo | n | Mediana (h) | Média (h) | Máx (h) | Assimetria bruta | Assimetria do log | Outliers (Tukey) | σ_log |
|---|---|---|---|---|---|---|---|---|
| com_bot | 30 | 7,60 | 300,8 | 3.742 | 3,39 | 0,37 | 5 | 3,22 |
| sem_bot | 30 | 2,73 | 69,8 | 1.056 | 3,90 | 0,69 | 5 | 2,50 |

Leitura: os dados brutos são muito assimétricos à direita (média muito maior que a mediana), e depois do log a assimetria cai para perto de zero, o que sustenta a escolha da lognormal. O σ_log (2,5 a 3,2) é bem maior que o valor provisório de 1,0 usado pelo João, então ele deve atualizar a simulação.

## 4. #104 — Cenário

`docs/cenario.md` contém:

- **Pergunta:** o tempo até o merge difere entre PRs com e sem bot de revisão?
- **H₀/H₁:** mesma distribuição (médias iguais no Welch; P(X_com > X_sem) = 0,5 no Mann-Whitney) × diferença entre os grupos.
- **Bicaudal:** não há direção prevista a priori (o bot pode acelerar ou atrasar).
- **Distribuição:** lognormal por mediana e σ_log, justificada pelos dados reais.
- **Expectativa registrada antes de simular:** o Mann-Whitney deve ter mais poder, pois com σ_log alto a média do Welch é dominada por poucos PRs extremos; o Welch deve desviar de 5% no erro tipo I (provavelmente conservador).

Também adicionei `docs/enunciado.md` (enunciado completo, como no lab02) e `docs/decisoes_do_grupo.md` (decisões e divisão de tarefas).

## 5. Reprodução

```bash
python3 scripts/coletar_prs.py        # requer gh autenticado; regenera o CSV
python3 scripts/estimar_parametros.py # regenera dados/parametros.json
```

## 6. Pendências

- João: trocar os parâmetros provisórios pelos de `dados/parametros.json`.
- Marcela: usar o CSV e o JSON no G1 e no dashboard.

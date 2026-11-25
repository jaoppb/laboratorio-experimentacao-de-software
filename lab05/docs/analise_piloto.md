# Análise do piloto: pipeline e suficiência da amostra

**Issue:** #167 (atualizado no #171) · **Papel:** C (Análise e Impacto) · **Responsável:** Marcela Campos  
**Versão:** 1.1 (Lab05S01, piloto refeito com ordem contrabalanceada ABBA no #171)  
**Dados:** `dados/piloto/` (#171, Moodle 4.5.16 e 5.3.1 em Docker)  
**Código:** `scripts/analisar_piloto.py` · **Saída:** `dados/piloto/analise_piloto.json`  
**Documentos de referência:** `plano_analise.md` (#165) e `plano_coleta_instrumentacao.md` (#164/#166)

---

## 1. Objetivo e limites desta análise

O #167 responde a duas perguntas:

1. **O pipeline de análise funciona?** Os dados do piloto passam no validador e alimentam, sem ajuste manual, as estatísticas planejadas no #165: descritiva, Mann-Whitney, Δ de Cliff, Wilson, Fisher e Wilcoxon.
2. **A amostra prevista (N = 80 por tela e versão) parece suficiente**, dada a variância observada?

Esta análise **não** é resultado definitivo do estudo: o piloto tem n = 9 repetições `warm` por grupo (§2) em uma única passada. Após o contrabalanceamento ABBA implementado no `#171`, o viés de ordem fixa (P13) foi removido; ainda assim, os testes abaixo exercitam o pipeline e dimensionam a coleta da S02.

## 2. Decisões de método

| Tema | Decisão | Motivo |
|---|---|---|
| Cache | A análise principal usa só as repetições `warm` (repetições 2 a 10, n = 9 por tela e versão). A repetição `cold` (n = 1 por grupo) é só descrita, sem teste. | Com n = 1 não há teste nem tamanho do efeito. Misturar frio e quente faria o `login` frio (458 e 505 ms, contra medianas de 43 e 45 ms) dominar média e p95. Fecha o P11. |
| Teste de M1 | Mann-Whitney bicaudal (`scipy.stats.mannwhitneyu`, `method="auto"`), α = 0,05. | Plano #165 §3.1. |
| Múltiplas telas | Reporta o p bruto e o p ajustado por Holm sobre as 4 telas. | São 4 comparações sobre os mesmos dados de coleta. |
| Efeito | Δ de Cliff (5.3 contra 4.5), com IC 95% por bootstrap percentil (10.000 reamostras) e limiares de Romano et al. | Plano #165 §4. |
| Suficiência | Para cada tela, o menor n da grade (10, 20, 30, 40, 60, 80, 100, 120, 160, 200) com poder simulado >= 80%. A simulação reamostra com reposição os 9 valores `warm` de cada versão (2.000 simulações por n). | Usa a variância e o deslocamento observados, sem supor uma distribuição. |
| Reprodutibilidade | Semente 167, com fluxos independentes por tela: `numpy.random.default_rng([semente, índice da tela, 0])` para o bootstrap e `[semente, índice da tela, 1]` para a simulação de poder (mudar `--n-bootstrap` não altera a suficiência). Mesmos dados e mesmas versões de numpy e scipy dão o mesmo JSON. | |

## 3. Pipeline

`python scripts/analisar_piloto.py` roda `validar_piloto.py` sobre `dados/piloto/` e só continua se não houver problemas (sai com código 1 caso contrário). Em seguida calcula M1, M3 e M4 e grava `dados/piloto/analise_piloto.json`. Os testes (`tests/test_analisar_piloto.py`) conferem as estatísticas contra valores conhecidos e que o JSON versionado coincide com o recálculo a partir do CSV (a parte aleatória, bootstrap e simulação, é conferida pela coerência interna e pela reprodutibilidade com a mesma semente).

Resultado: **o pipeline funciona de ponta a ponta com os dados reais** (80 requisições e 8 relatórios axe) e trata os casos degenerados de M3 e M4 (§5). A execução completa leva cerca de 40 s, quase todo na simulação de poder.

## 4. M1: TTFB por tela (somente `warm`, n = 9 por grupo)

| Tela | Mediana 4.5 (IQR) | Mediana 5.3 (IQR) | Razão 5.3/4.5 | Δ de Cliff [IC 95%] | p | p Holm |
|---|---|---|---|---|---|---|
| login | 14,25 (1,79) | 15,97 (1,22) | 1,121 | 0,58 grande [0,01; 1,00] | 0,042 | 0,102 |
| dashboard | 62,28 (0,89) | 63,04 (6,89) | 1,012 | 0,46 médio [-0,06; 0,88] | 0,112 | 0,112 |
| curso | 51,07 (4,42) | 54,91 (4,09) | 1,075 | 0,60 grande [0,09; 1,00] | 0,034 | 0,102 |
| questionario (entrada do quiz) | 48,53 (1,94) | 53,87 (2,80) | 1,110 | 0,97 grande [0,85; 1,00] | 0,001 | 0,002 |

Valores em ms. Leitura:

- Em `questionario` (entrada do quiz), o p ajustado por Holm é `0,002` (< 0,05), com Δ de Cliff = `0,97` (IC 95% `[0,85; 1,00]`). Nas outras três telas (`login`, `dashboard`, `curso`), nenhum p ajustado por Holm fica abaixo de 0,05 (`0,102` a `0,112`).
- Os IC do Δ de Cliff nas telas `login`, `dashboard` e `curso` ainda são largos (amplitude de `0,91` a `0,99` numa escala de -1 a 1), com `dashboard` cruzando 0 (`[-0,06; 0,88]`). Com n = 9 por grupo, a precisão da estimativa de efeito segue limitada.
- **Variância observada.** Na 4.5, os desvios-padrão `warm` ficam entre `1,54` e `3,48` ms. Na 5.3, ficam entre `1,70` e `4,01` ms em `login`, `curso` e `questionario`, mas sobem para `67,40` ms em `dashboard` (p95 = `190,13` ms, razão de desvios `20,61`) por conta de um pico isolado. As dispersões desiguais reforçam a escolha por testes não paramétricos.
- **Cold (n = 1 por grupo, só descritivo).** A 1ª requisição levou de `1,9` a `31,3` vezes a mediana `warm` do mesmo grupo (`login`: `445,56` ms / `31,27×` na 4.5 e `488,40` ms / `30,58×` na 5.3; `dashboard`: `195,26` ms / `3,14×` e `190,54` ms / `3,02×`; `curso`: `123,30` ms / `2,41×` e `156,67` ms / `2,85×`; `questionario`: `93,09` ms / `1,92×` e `110,84` ms / `2,06×`). O frio é bem mais lento e mais variável, e o piloto não permite estimar o quanto.

## 5. M3 e M4: pipeline sobre dados degenerados

| Métrica | Dado do piloto | Teste e resultado |
|---|---|---|
| M3: erros HTTP (5xx) | 0 em 40 requisições por versão (todas com 200) | IC de Wilson 95% de 0 a 8,8% em cada versão. Fisher exato (contagens esperadas < 5): p = 1,0. |
| M4: violações axe | 0 violações nas 8 combinações (tela × versão) | Wilcoxon pareado **não aplicável**: as 4 diferenças são 0. |

O 0 de M3 vale **por construção**: o runner aborta a coleta em qualquer status diferente de 200 (`ErroColeta`) e em timeouts (`httpx.TimeoutException`, 60 s por requisição), e o validador exige `status_http = 200`. Um CSV válido do piloto não pode conter 5xx nem timeout, então M3 não foi realmente testado (a definição do GQM é "5xx e timeout"). Para a S02, o runner precisa gravar 5xx e timeouts como linhas de erro em vez de abortar (ver §7).

Nenhuma conclusão estatística sobre erro ou acessibilidade sai do piloto: o resultado é "nenhuma falha registrada" (por construção, ver acima) e "o axe não encontrou violações nas 4 telas", e só.

Um ponto de planejamento para a S02: com 4 telas pareadas, o Wilcoxon exato **nunca** chega a p < 0,05 (o menor p bicaudal possível é 2/2⁴ = 0,125). Para M4 ter poder de teste, o contraste precisa de mais unidades pareadas (por exemplo, por regra do axe ou por elemento afetado) ou de mais telas. Essa escolha fica para a S02 e não altera o plano #165 agora.

## 6. Suficiência da amostra (N = 80 por tela e versão)

| Tela | Δ de Cliff observado | n por grupo para poder >= 80% | Poder simulado em n = 80 | Faixa |
|---|---|---|---|---|
| login | 0,58 | 20 | 1,000 | folgado |
| dashboard | 0,46 | 30 | 1,000 | folgado |
| curso | 0,60 | 20 | 1,000 | folgado |
| questionario | 0,97 | 10 | 1,000 | folgado |

Faixas, com N planejado = 80: **folgado** quando o n necessário é <= 40 (o N planejado é pelo menos o dobro), **suficiente** quando 40 < n necessário <= 80, e **insuficiente** quando o n necessário supera 80 ou nenhum n da grade atinge 80% de poder. Todas as 4 telas ficam na faixa `folgado` (n necessário entre 10 e 30).

**Conclusão (provisória): N = 80 não é contradito pelo piloto e fica mantido como piso.** Pelos dados observados, 10 a 30 repetições `warm` por grupo já atingiriam 80% de poder. Esse número não autoriza reduzir N, por três motivos:

1. Em Δ de Cliff, o efeito observado (0,46 a 0,97) é alto porque a dispersão `warm` é pequena, mas o deslocamento relativo das medianas (1,2% a 12,1%) fica abaixo dos 15% a 25% supostos no #165 §5 (efeito médio, d ≈ 0,35, que exige 60 a 80 por grupo). Os IC 95% vão de -0,06 a 1,00. Estimar o n a partir de um efeito medido com n = 9 tende a ser otimista, e o Δ de Cliff do piloto não equivale ao d do plano.
2. A reamostragem de 9 valores repete valores e subestima a cauda.
3. A análise cobre só `warm`. Para `cold`, o piloto não dá nenhuma estimativa de variância (n = 1).

Consequências para a S02, que ficam como orientação e não alteram o #165:

- manter 80 repetições `warm` por tela e versão;
- planejar uma coleta `cold` à parte, com purga de cache entre as repetições e n próprio (a estimar com a variância observada na S02);
- manter a ordem contrabalanceada das versões dentro dos pares (implementada no #171) e medir a tentativa do quiz (follow-up #172).

## 7. Ameaças à validade desta análise

| Tipo | Ameaça | Tratamento |
|---|---|---|
| Interna | Ordem entre versões (P13): na versão 1.0 era fixa 4.5 → 5.3. | **Mitigada no #171:** pares contrabalanceados em padrão ABBA determinístico (5× cada ordem por tela). |
| Interna | Ruído de execução e picos isolados (ex.: cauda em `dashboard` 5.3 com n = 9). | Declarada. Em n = 9 um outlier eleva o desvio-padrão; na S02 o N = 80 reduz a sensibilidade. |
| Conclusão | n = 9 por grupo, uma passada, IC do Δ de Cliff de grande amplitude. | Conclusão sobre N provisória e N = 80 mantido como piso. |
| Conclusão | Quatro comparações. | p ajustado por Holm reportado ao lado do p bruto. |
| Construto | A tela `questionario` mede a **entrada do quiz** (quiz sem questões), não a tentativa em período de prova. | Rotulada como "entrada do quiz". Follow-up #172 para a S02. |
| Construto | O TTFB mede só o tempo de servidor, sem rede nem renderização. | Limite mantido do #163/#165. |
| Construto | M3 não captura falhas: o piloto aborta em qualquer status diferente de 200 e em timeouts, em vez de registrá-los. | Registrado em §5. Na S02, gravar 5xx e timeouts como erros em vez de abortar. |
| Externa | Um servidor local, dados sintéticos, sem plugins. | Sem extrapolação para instalações reais. |

## 8. Como reproduzir

```bash
cd lab05
pip install httpx numpy scipy pytest   # versões mínimas em pyproject.toml
python scripts/analisar_piloto.py
pytest tests/test_analisar_piloto.py
```

A análise lê `dados/piloto/` e não precisa de Docker nem de rede. Opções: `--dir`, `--saida`, `--semente`, `--n-bootstrap` e `--n-simulacoes`.

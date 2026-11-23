# Análise do piloto: pipeline e suficiência da amostra

**Issue:** #167 · **Papel:** C (Análise e Impacto) · **Responsável:** Marcela Campos  
**Versão:** 1.0 (Lab05S01)  
**Dados:** `dados/piloto/` (#166, Moodle 4.5.16 e 5.3.1 em Docker)  
**Código:** `scripts/analisar_piloto.py` · **Saída:** `dados/piloto/analise_piloto.json`  
**Documentos de referência:** `plano_analise.md` (#165) e `plano_coleta_instrumentacao.md` (#164/#166)

---

## 1. Objetivo e limites desta análise

O #167 responde a duas perguntas:

1. **O pipeline de análise funciona?** Os dados do piloto passam no validador e alimentam, sem ajuste manual, as estatísticas planejadas no #165: descritiva, Mann-Whitney, Δ de Cliff, Wilson, Fisher e Wilcoxon.
2. **A amostra prevista (N = 80 por tela e versão) parece suficiente**, dada a variância observada?

Esta análise **não** diz se a 5.3 é mais lenta ou mais rápida que a 4.5. O piloto tem n = 9 por grupo (§2), uma única passada e ordem fixa 4.5 → 5.3 (§7). As diferenças medidas (2 a 7 ms nas medianas) têm o tamanho do ruído entre execuções do próprio piloto (cerca de 6 ms, `plano_coleta_instrumentacao.md` §7.3). Os testes abaixo exercitam o pipeline e dimensionam a coleta. Não são resultado do estudo.

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
| login | 42,76 (2,68) | 45,22 (4,84) | 1,058 | 0,43 médio [-0,14; 0,93] | 0,133 | 0,267 |
| dashboard | 90,08 (10,68) | 92,30 (2,83) | 1,025 | 0,41 médio [-0,14; 0,85] | 0,158 | 0,267 |
| curso | 88,37 (9,96) | 95,03 (3,38) | 1,075 | 0,58 grande [0,04; 1,00] | 0,042 | 0,169 |
| questionario (entrada do quiz) | 82,27 (11,53) | 89,69 (5,85) | 1,090 | 0,58 grande [0,06; 1,00] | 0,042 | 0,169 |

Valores em ms. Leitura:

- Nenhum p ajustado por Holm fica abaixo de 0,05. Os dois p brutos de 0,042 não resistem ao ajuste.
- Os IC do Δ de Cliff são largos (amplitude de 0,94 a 1,06 numa escala de -1 a 1) e dois deles incluem 0. Com n = 9, o efeito é mal estimado. A direção (5.3 mais lenta nas 4 telas) é compatível com o viés da ordem fixa (§7), e não deve ser interpretada.
- **Variância observada.** Os desvios-padrão `warm` ficam entre 4,5 e 21,7 ms, e o desvio da 5.3 é menor que o da 4.5 em 3 das 4 telas (razão de 0,35 a 0,68). Só o `questionario` tem desvio maior na 5.3 (razão 1,23, com cauda até 153 ms). As variâncias desiguais confirmam a escolha por testes não paramétricos.
- **Cold (n = 1 por grupo, só descritivo).** A 1ª requisição levou de 1,1 a 11 vezes a mediana `warm` do mesmo grupo (login 4.5: 457,67 ms, razão 10,7; dashboard 4.5: 195,40 ms, razão 2,2; curso 5.3: 151,22 ms, razão 1,6). O frio é bem mais lento e mais variável, e o piloto não permite estimar o quanto.

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
| login | 0,43 | 30 | 0,997 | folgado |
| dashboard | 0,41 | 40 | 0,996 | folgado |
| curso | 0,58 | 20 | 1,000 | folgado |
| questionario | 0,58 | 20 | 1,000 | folgado |

Faixas, com N planejado = 80: **folgado** quando o n necessário é <= 40 (o N planejado é pelo menos o dobro), **suficiente** quando 40 < n necessário <= 80, e **insuficiente** quando o n necessário supera 80 ou nenhum n da grade atinge 80% de poder. O `dashboard` (n necessário = 40) está exatamente na fronteira entre folgado e suficiente.

**Conclusão (provisória): N = 80 não é contradito pelo piloto e fica mantido como piso.** Pelos dados observados, 20 a 40 repetições `warm` por grupo já atingiriam 80% de poder. Esse número não autoriza reduzir N, por quatro motivos:

1. Em Δ de Cliff, o efeito observado (0,41 a 0,58) é alto porque a dispersão `warm` é pequena, mas o deslocamento relativo das medianas (2,5% a 9%) fica abaixo dos 15% a 25% supostos no #165 §5 (efeito médio, d ≈ 0,35, que exige 60 a 80 por grupo). Os IC 95% vão de -0,14 a 1,00. Estimar o n a partir de um efeito medido com n = 9 tende a ser otimista, e o Δ de Cliff do piloto não equivale ao d do plano.
2. A reamostragem de 9 valores repete valores e subestima a cauda. O `questionario`, com a maior dispersão, tem poder 1,0 em n = 80 só porque o deslocamento observado é grande.
3. O deslocamento observado inclui o viés da ordem fixa 4.5 → 5.3 (P13) e a deriva entre execuções, que o piloto não separa do efeito da versão.
4. A análise cobre só `warm`. Para `cold`, o piloto não dá nenhuma estimativa de variância (n = 1).

Consequências para a S02, que ficam como orientação e não alteram o #165:

- manter 80 repetições `warm` por tela e versão;
- planejar uma coleta `cold` à parte, com purga de cache entre as repetições e n próprio (a estimar com a variância observada na S02);
- contrabalancear a ordem das versões dentro dos pares (follow-up #171) e medir a tentativa do quiz (follow-up #172).

## 7. Ameaças à validade desta análise

| Tipo | Ameaça | Tratamento |
|---|---|---|
| Interna | Ordem fixa 4.5 → 5.3 (P13): qualquer deriva cai sempre na 5.3. | Declarada. Não interpretamos o sentido da diferença. O piloto não foi alterado. Follow-up #171. |
| Interna | Ruído de execução: as medianas variaram até ~6 ms entre as duas execuções do piloto na mesma configuração. | Declarada. Tamanho do ruído é comparável às diferenças observadas. |
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

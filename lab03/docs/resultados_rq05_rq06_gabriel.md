# Resultados das Questões de Pesquisa 05 e 06 (Sprint 03)

**Autor:** Gabriel Assis de Souza (@GabriAssiss)  
**Papel no Guia:** Integrante B (RQ 05 e RQ 06)  
**Módulo Implementado:** [`../analises/analise_rq05_rq06.py`](../analises/analise_rq05_rq06.py)  
**Suíte de Testes:** [`../tests/test_analise_rq05_rq06.py`](../tests/test_analise_rq05_rq06.py)  
**Artefatos Gerados:** [`../dados/analises/rq05_rq06_metricas.json`](../dados/analises/rq05_rq06_metricas.json), tabelas `.tex`/`.md` e figuras em [`../dados/analises/figuras/`](../dados/analises/figuras/)

---

## 1. RQ 05 — Relação entre Frequência de Deploy e Taxa de Falha

### 1.1 Pergunta de Pesquisa
> *Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?*

Calculamos o coeficiente de correlação de postos de Spearman ($\rho$) separadamente para as duas variantes obrigatórias de CFR:
1. **CFR (a) — Proxy de CI:** $\frac{\text{runs push com falha}}{\text{runs push com sucesso ou falha}}$ no default branch ($n = 330$).
2. **CFR (b) — Proxy de Entrega:** proporção de releases seguidas por release corretiva em até 7 dias ($n = 328$).

### 1.2 Resultados Empíricos

| ID | Relacionamento | $n$ | Spearman ($\rho$) | $p$-valor | Significativo ($\alpha=0{,}05$) | Interpretação |
|---|---|---:|---:|---:|:---:|---|
| **RQ 05 (a)** | Freq. Deploy $\times$ CFR (a) [CI] | 330 | **+0,1612** | $3{,}32 \times 10^{-3}$ | **Sim** | Correlação fraca e positiva |
| **RQ 05 (b)** | Freq. Deploy $\times$ CFR (b) [Entrega] | 328 | **+0,4968** | $7{,}64 \times 10^{-22}$ | **Sim** | Correlação moderada a forte positiva |

Figura gerada: `dados/analises/figuras/rq05_spearman_dispersao.png` (e `.pdf`).

### 1.3 Confronto com a Hipótese Informal e Discussão Teórica
Na Sprint 01 (`docs/hipoteses_rq02_rq03_rq05.md`), hipotetizamos que:
1. Para o **CFR (a)**, haveria correlação fraca e positiva, decorrente do fato de projetos muito ativos executarem esteiras de CI mais frequentes e complexas, ampliando a exposição a falhas transitórias e *flaky tests*. O resultado empírico confirmou precisamente essa expectativa ($\rho = +0{,}161$, $p = 0{,}0033$).
2. Para o **CFR (b)**, alertamos para a existência de um **viés metodológico de acoplamento mecânico**: projetos com alta frequência de lançamentos têm espaçamento médio entre releases naturalmente inferior a 7 dias, aumentando a probabilidade matemática de uma release ser seguida por outra dentro da janela de 7 dias, independentemente da gravidade intrínseca de defeitos. O resultado empírico demonstrou um $\rho = +0{,}497$ ($p = 7{,}64 \times 10^{-22}$), ilustrando de forma contundente essa ameaça de construto do proxy de 7 dias em projetos open-source contínuos.
3. **Velocidade vs. Estabilidade no DORA:** No relatório *Accelerate*, afirma-se que equipes *Elite* não enfrentam trade-off entre velocidade e estabilidade. Em projetos open-source, nossos dados mostram que maior velocidade de entrega não acarreta redução da taxa de falha observada; pelo contrário, expõe mais o pipeline e amplifica o proxy de correções emergenciais.

---

## 2. RQ 06 — Fatores do Repositório e Desempenho DORA

### 2.1 Pergunta de Pesquisa
> *Quais características dos repositórios estão associadas a um melhor desempenho DORA?*

Analisamos **5 fatores** estruturais e organizacionais contra as 5 métricas DORA (`deployment_frequency`, `lead_time_b_hours`, `cfr_a`, `cfr_b`, `recovery_hours`), totalizando **25 testes de Kruskal-Wallis**, ajustados para comparações múltiplas via **método de Holm-Bonferroni** ($\text{FWER} \le 0{,}05$) e quantificados pelo tamanho de efeito **Epsilon-quadrado** ($\epsilon^2 = \frac{H}{n - 1}$):
- **Popularidade:** Quartis de estrelas (Q1: $<2{,}5$k; Q2: $2{,}5\text{--}5{,}9$k; Q3: $5{,}9\text{--}18{,}7$k; Q4: $>18{,}7$k).
- **Tamanho da Equipe:** Quartis de contribuidores (Q1: $1\text{--}10$; Q2: $11\text{--}40$; Q3: $41\text{--}150$; Q4: $>150$).
- **Maturidade do Projeto:** Quartis de idade em anos (Q1: $<2$a; Q2: $2\text{--}5$a; Q3: $5\text{--}8$a; Q4: $>8$a).
- **Linguagem Principal:** Top linguagens (TypeScript, Python, Go, Rust, JavaScript, C++ e Outras).
- **Tipo de Projeto:** Aplicação/Serviço ($n=151$), Biblioteca/Framework ($n=95$), Ferramenta CLI ($n=63$) e Outro ($n=21$).

### 2.2 Resultados dos Testes de Kruskal-Wallis com Correção de Holm

| Fator | Métrica DORA | $k$ | $n$ | $H$ | $p$-valor bruto | $p$-valor (Holm) | $\epsilon^2$ | Tamanho de Efeito | Rejeita $H_0$? |
|---|---|---:|---:|---:|---:|---:|---:|---|:---:|
| **Tamanho da Equipe** | **Lead Time (b)** | 4 | 329 | **69,30** | $6{,}04 \times 10^{-15}$ | **$1{,}45 \times 10^{-13}$** | **0,2113** | **Grande** | **Sim (*)** |
| **Maturidade (Idade)** | **Freq. Deploy** | 4 | 330 | **32,81** | $3{,}54 \times 10^{-7}$ | **$7{,}79 \times 10^{-6}$** | **0,0997** | **Médio** | **Sim (*)** |
| **Maturidade (Idade)** | **Lead Time (b)** | 4 | 329 | **116,04** | $5{,}48 \times 10^{-25}$ | **$1{,}37 \times 10^{-23}$** | **0,3538** | **Grande** | **Sim (*)** |
| **Maturidade (Idade)** | **CFR (b) Entrega** | 4 | 328 | **60,18** | $5{,}37 \times 10^{-13}$ | **$1{,}24 \times 10^{-11}$** | **0,1840** | **Grande** | **Sim (*)** |
| **Linguagem** | **Freq. Deploy** | 7 | 330 | **20,90** | $1{,}91 \times 10^{-3}$ | **$3{,}63 \times 10^{-2}$** | **0,0635** | **Médio** | **Sim (*)** |
| **Linguagem** | **Lead Time (b)** | 7 | 329 | **32,10** | $1{,}56 \times 10^{-5}$ | **$3{,}29 \times 10^{-4}$** | **0,0979** | **Médio** | **Sim (*)** |
| **Tipo de Projeto** | **Lead Time (b)** | 4 | 329 | **23,26** | $3{,}56 \times 10^{-5}$ | **$7{,}12 \times 10^{-4}$** | **0,0709** | **Médio** | **Sim (*)** |
| Popularidade | Freq. Deploy | 4 | 330 | 5,66 | 0,1295 | 1,0000 | 0,0172 | Pequeno | Não |
| Popularidade | Lead Time (b) | 4 | 329 | 1,84 | 0,6053 | 1,0000 | 0,0056 | Desprezível | Não |
| Popularidade | CFR (a) CI | 4 | 330 | 3,57 | 0,3119 | 1,0000 | 0,0108 | Pequeno | Não |
| Popularidade | CFR (b) Entrega | 4 | 328 | 2,32 | 0,5091 | 1,0000 | 0,0071 | Desprezível | Não |
| Popularidade | Tempo Recuperação | 4 | 312 | 0,52 | 0,9136 | 1,0000 | 0,0017 | Desprezível | Não |

### 2.3 Principais Achados Empíricos
1. **O número de contribuidores e a idade inflacionam drasticamente o Lead Time:**
   - Repositórios com mais de 150 contribuidores (Q4) e projetos com mais de 8 anos (Q4) exibem tempos de lead substancialmente superiores ($\epsilon^2 = 0{,}211$ e $\epsilon^2 = 0{,}354$, ambos de magnitude **Grande**). Em projetos distribuídos maduros, o tempo de trânsito dos commits reflete a burocracia de code review, validações em matrizes extensas de CI e cadências de congelamento de versões.
2. **A popularidade (estrelas) NÃO discrimina o desempenho DORA:**
   - Nenhuma das 5 métricas DORA apresentou variação estatisticamente significante por faixas de estrelas ($p_{\text{Holm}} = 1{,}0000$). Um repositório com 50.000 estrelas pode ter cadência de deploy e estabilidade idênticas às de um repositório com 1.500 estrelas.
3. **Linguagem e Ferramentas Modernas:**
   - Projetos nos ecossistemas JavaScript/TypeScript e Python mantêm frequência de deploy estatisticamente mais elevada e menor lead time mediano do que ecossistemas de linguagens compiladas de baixo nível (C/C++), validando a hipótese preliminar formulada na Sprint 01.
4. **Tipo de Projeto:**
   - Aplicações/serviços e utilitários CLI apresentam lead time significativamente menor do que bibliotecas/frameworks ($p_{\text{Holm}} = 7{,}12 \times 10^{-4}$, $\epsilon^2 = 0{,}0709$), dado que alterações em bibliotecas requerem rigor acrescido para salvaguardar compatibilidade retroativa com clientes externos.

---

## 3. Comandos de Reprodução

Para regenerar todos os cálculos, tabelas e gráficos da parte do Gabriel:
```bash
uv run python -m analises.analise_rq05_rq06
```

Para rodar a suíte de testes correspondente:
```bash
uv run pytest tests/test_analise_rq05_rq06.py -v
```

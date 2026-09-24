# Laboratório de Experimentação de Software — Relatório Final

| Campo | Valor |
|---|---|
| **Curso** | Engenharia de Software |
| **Disciplina** | Laboratório de Experimentação de Software |
| **Turno / Período** | Noite / 6º |
| **Professor(a)** | Danilo Maia |
| **Laboratório** | Lab02 — Assistentes de IA vs. Codificação Manual: Um Experimento Controlado |
| **Grupo (trio)** | Marcela Mendes Campos (@marcelacamposm) · João Pedro Peres (@jaoppb) · Gabriel Assis de Souza (@GabriAssiss)|
| **Link do Repositório** | [Repositório GitHub](https://github.com/jaoppb/laboratorio-experimentacao-de-software) |
| **Link do GitHub Projects** | [GitHub Projects (v2)](https://github.com/users/jaoppb/projects/3) |
| **Link do Dashboard** | [Dashboard Interativo](https://jaoppb.github.io/laboratorio-experimentacao-de-software/lab02/) |
| **Data de Entrega** | 24/09/2026 |

---

## 1. Introdução

A crescente adoção de assistentes de inteligência artificial generativa (como ChatGPT, Claude Sonnet 5 e Gemini Flash) no ciclo de desenvolvimento de software transformou as práticas de programação. Contudo, a literatura e a indústria ainda carecem de dados empíricos e controlados sobre os reais ganhos de produtividade e os eventuais impactos na qualidade estrutural e corretude do código produzido.

O objetivo deste laboratório é conduzir um **experimento controlado pareado (*within-subject crossover*)** para avaliar quantitativamente os efeitos do uso de assistentes de IA frente à codificação manual na resolução de tarefas algorítmicas (*katas*).

### Questões de Pesquisa (RQs do Enunciado — 70%)
- **RQ1:** O uso de assistente de IA reduz o tempo necessário para resolver uma tarefa de programação? (*Time-to-green* em segundos).
- **RQ2:** O uso de assistente de IA reduz a quantidade de defeitos (testes de aceitação que falham) no código produzido?
- **RQ3:** O uso de assistente de IA altera a complexidade ciclomática, a duplicação ou o tamanho do código produzido?

### Hipóteses Informais do Grupo (Formuladas antes da coleta)
- **RQ1 (Marcela):** O uso de IA reduzirá drasticamente o tempo de resolução, especialmente em problemas que exigem estruturas de dados clássicas, proporcionando um *speedup* mediano superior a 5x em relação ao desenvolvimento manual.
- **RQ2 (Gabriel):** A taxa de acerto funcional com IA será próxima a 100% no primeiro ou segundo prompt, empatando com a codificação manual, já que ambos os tratamentos são submetidos a testes automatizados rigorosos antes da entrega dentro do time-box de 35 minutos.
- **RQ3 (João Pedro):** O código gerado por IA apresentará maior verbosidade (maior LOC bruto) e maior complexidade ciclomática pontual devido à geração de código defensivo e tratamento extensivo de casos de borda, embora a manutenibilidade geral (Índice MI) se mantenha alta.

### Inovações Propostas pelo Grupo (Fatia de 30% da Nota)
1. **Benchmarking Multimodelo:** Comparação cruzada de desempenho entre três modelos de linguagem de ponta distintos (**Gemini Flash 3.8**, **Claude Sonnet 5** e **GPT-4o**) pareados contra o desenvolvimento manual de cada integrante.
2. **Análise de Densidade de Complexidade e Manutenibilidade Composta:** Normalização da complexidade ciclomática por linhas lógicas de código ($\text{CC}/\text{SLOC}$) e avaliação do Índice de Manutenibilidade de Halstead/McCabe ($\text{Radon MI}$).
3. **Dashboard Web Interativo SPA:** Construção de uma aplicação interativa moderna (React + TypeScript + TailwindCSS + Recharts) com visualização em tempo real de distribuições, *boxplots* pareados e cálculo dinâmico de Wilcoxon e *speedup*.

---

## 2. Contexto

Este trabalho representa o **Laboratório 02** da disciplina de Laboratório de Experimentação de Software, dando continuidade ao processo de medição empírica e acompanhamento via quadro Kanban (GitHub Projects v2) iniciado no Lab01.

O objeto de estudo consiste na resolução de **6 katas de programação competitiva** extraídos da **XIII Maratona Mineira de Programação (2026)**. A escolha dessa base de problemas teve como critério central o fato de serem exercícios recentes e de baixa indexação pública prévia, mitigando a ameaça à validade de "memorização" (quando a LLM apenas reproduz soluções idênticas decoradas de sua base de treinamento em vez de sintetizar a lógica).

A metodologia baseia-se no framework **Goal-Question-Metric (GQM)** de Basili et al. (1994), estruturada da seguinte forma:
- **Goal:** Analisar o uso de assistentes de IA generativa com o propósito de comparar seu efeito frente à codificação manual, quanto ao tempo de resolução, qualidade funcional e qualidade estrutural do código produzido, sob a perspectiva da equipe de desenvolvimento, em katas de complexidade uniforme sob protocolo controlado (*crossover within-subject*, *time-boxed* em 35 minutos).

---

## 3. Metodologia

### 3.1 Principais Desafios
1. **Controle Estrito de Tempo e Automação (*Time-to-Green*):** Evitar imprecisões de cronometragem humana. Foi desenvolvido um runner CLI (`scripts/time_trial.py`) que executa os testes de aceitação a cada ciclo e registra automaticamente o timestamp exato do primeiro momento em que 100% dos testes passam.
2. **Prevenção de Efeito de Aprendizado (*Order Effect*):** Ao resolver o mesmo kata manualmente e com IA, a ordem de resolução poderia introduzir viés de aprendizado. Para mitigar, foi adotado o contrabalanceamento estrito entre os participantes e tratamentos.
3. **Mitigação de Memorização por LLMs:** Katas amplamente conhecidos do LeetCode/Codeforces facilitariam a IA. A utilização da prova oficial de 2026 da Maratona Mineira garantiu novidade de enunciado para os modelos.
4. **Padronização das Métricas Estáticas:** A ferramenta CK opera exclusivamente em Java. Como o grupo utilizou Python 3.12, foi estabelecido o pipeline de métricas estáticas utilizando o **Radon** (para CC, raw LOC e MI) e algoritmo de detecção de clones estruturais (CPD).

### 3.2 Tomadas de Decisão
- **Design Experimental:** *Within-subject crossover* balanceado. Cada um dos 3 integrantes executou os 6 katas em ambos os tratamentos (18 trials com IA e 18 trials manuais, totalizando $N = 36$ trials).
- **Time-box Rígido:** A atividade previa 35 minutos (2.100 segundos) por trial, porém a escolha dos katas recentes da XIII Maratona Mineira de Programação aumentou a complexidade de cada um dos problemas e inviabilizou um time-box rígido.
- **Modelos Utilizados:** 
  - Gabriel: Gemini Flash 3.8
  - João Pedro: Claude Sonnet 5
  - Marcela: ChatGPT (GPT-4o)
- **Política de WIP do Kanban:** Limite de WIP fixado em **6 cartões** na coluna *Doing* (exatamente 2 cartões por integrante ativo), prevenindo gargalos e garantindo fluxo contínuo.

### 3.3 Etapas do Processo de Desenvolvimento

| Sprint / Fase | Entregas Principais | Responsável(is) | Issue(s) |
|---|---|---|---|
| **Lab02S01** | Script de cronometragem automática (`time_trial.py`) e runner | Marcela | `#18` |
| **Lab02S01** | Setup do ambiente Python/uv + Script de métricas estáticas Radon (`collect_metrics.py`) | João Pedro | `#19` |
| **Lab02S01** | Seleção dos 6 katas da Maratona Mineira 2026 + 120 testes de aceitação e suites | Gabriel | `#20` |
| **Lab02S01** | Formalização do desenho experimental, GQM e ameaças à validade | Marcela | `#21` |
| **Lab02S02** | Execução de trials com Gemini Flash 3.8 + Trials Manuais | Gabriel | `#22` |
| **Lab02S02** | Execução de trials com Claude Sonnet 5 + Trials Manuais | João Pedro | `#23` |
| **Lab02S02** | Execução de trials com GPT-4o + Trials Manuais | Marcela | `#24` |
| **Lab02S03** | Desenvolvimento do Dashboard interativo de visualização | João Pedro | `#26` |
| **Lab02S03** | Consolidação estatística (Wilcoxon pareado, IQR, outliers) via `analyze_stats.py` | Marcela / Gabriel | `#27` |
| **Relatório Final** | Redação do documento final consolidado e submissão | João Pedro / Marcela / Gabriel | `#25` |

#### Configuração do Processo (GitHub Projects)
O quadro Kanban foi configurado com as colunas: `Backlog → To Do → Doing (WIP: 6) → In Review → Done`. Todas as atividades foram mapeadas em issues com assignees definidos e commits vinculados pelo identificador (`#número`).

### 3.4 Ferramentas Utilizadas
- **Linguagem & Runtime:** Python 3.12 gerenciado via `uv`.
- **Análise Estática de Código:** `radon` (Radon CC, Radon Raw, Radon MI) e clone detector integrado (`python-cpd`).
- **Execução e Testes de Aceitação:** `pytest` e runner CLI customizado com subprocessos isolados.
- **Análise Estatística:** `scipy.stats` (para Teste de Postos Sinalizados de Wilcoxon) e `pandas`.
- **Dashboard Web:** React, TypeScript, TailwindCSS, Recharts e Vite.
- **Gestão Ágil:** GitHub Projects (v2) e script GraphQL para extração semanal de snapshots em CSV.

### 3.5 Tabela de Métricas

| RQ | Métrica | Definição Operacional | Unidade | Ferramenta / Fonte |
|---|---|---|---|---|
| **RQ1** | Tempo até o Verde (*Time-to-green*) | $\Delta t = t_{\text{pass\_all}} - t_{\text{start}}$ (tempo até passar nos 20 testes de aceitação) | Segundos ($s$) | `scripts/time_trial.py` |
| **RQ2** | Taxa de Sucesso Funcional | $\frac{\text{Testes Aprovados}}{\text{Total de Testes (20)}}$ | Proporção ($[0, 1]$) | `scripts/time_trial.py` |
| **RQ2** | Defeitos Residuais | Contagem absoluta de testes com falha ou erro ao final do trial | Contagem | `scripts/time_trial.py` |
| **RQ3** | Complexidade Ciclomática Média | Média de $\text{CC} = E - N + 2P$ por função/método no arquivo | Valor escalar | `radon cc` (`collect_metrics.py`) |
| **RQ3** | Linhas de Código (LOC / SLOC) | Contagem física e lógica de linhas de código-fonte | Linhas | `radon raw` (`collect_metrics.py`) |
| **RQ3** | Duplicação de Código | Percentual de linhas contidas em blocos de clones idênticos | Porcentagem ($\%$) | `python-cpd` |
| **RQ3** | Índice de Manutenibilidade (MI) | $MI = 171 - 5.2 \ln(V) - 0.23(CC) - 16.2 \ln(LOC)$ | Escala ($0-100$) | `radon mi` (`collect_metrics.py`) |
| **Inovação**| Densidade de Complexidade | Razão entre a complexidade total e linhas de código: $\frac{\text{CC}}{\text{SLOC}}$ | $\text{CC}/\text{Linha}$ | `collect_metrics.py` |
| **Inovação**| Fator de Aceleração (*Speedup*) | Razão entre tempo manual e tempo com IA: $\frac{t_{\text{manual}}}{t_{\text{ai}}}$ | Fator ($x$) | `analyze_stats.py` |

### 3.6 Inovações Propostas pelo Grupo (30% da Nota)
Para cumprir a exigência dos 30% de inovação, o grupo implementou três contribuições adicionais:

1. **Benchmarking Comparativo Multimodelo (Gemini vs Claude vs GPT):** Em vez de utilizar apenas uma única ferramenta de IA como a maioria dos estudos, estruturamos a coleta para comparar 3 provedores líderes sob os mesmos 6 problemas e mesmos testes, permitindo avaliar a consistência da assistência entre diferentes famílias de LLMs.
2. **Métricas Estáticas Avançadas ($\text{CC}/\text{SLOC}$ e Radon MI):** Indo além do LOC e CC brutos, incorporamos o Índice de Manutenibilidade composto de Halstead e a normalização de complexidade por linha de código, o que evita conclusões errôneas decorrentes apenas do tamanho do código gerado.
3. **Aplicação Web Dashboard Completa:** Desenvolvemos um frontend interativo modularizado com design moderno, permitindo ao usuário filtrar dados por participante, kata, modelo de IA e inspecionar gráficos de distribuição, boxplots e estatísticas de Wilcoxon em tempo real.

---

## 4. Resultados

[Dashboard](https://jaoppb.github.io/laboratorio-experimentacao-de-software/lab02/)

### 4.1 Coleta de Dados
A amostra final é composta por **36 trials completos** (100% de integridade):
- **18 trials com Assistente de IA** (6 Gemini Flash 3.8 + 6 Claude Sonnet 5 + 6 GPT-4o)
- **18 trials Manuais** (6 Gabriel + 6 João Pedro + 6 Marcela)
- **Zero trials censurados:** todos os 36 trials atingiram 100% de sucesso nos 20 testes de aceitação bem antes do time-box de 35 minutos (2.100s).

### 4.2 Estatísticas Descritivas e Visualização Gráfica

Abaixo está a síntese descritiva calculada rigorosamente sobre o dataset consolidado:

| Questão | Métrica Analisada | IA (Mediana) | IA (IQR) | Manual (Mediana) | Manual (IQR) | Teste de Wilcoxon ($W$, $p$-value) |
|---|---|---|---|---|---|---|
| **RQ1** | **Tempo até o verde ($s$)** | **43.69 s** | 142.18 s | **982.76 s** | 314.18 s | $W = 0.0, p < 0.0001$ *(Significativo)* |
| **RQ2** | **Taxa de Sucesso** | **1.00 (100%)** | 0.00 | **1.00 (100%)** | 0.00 | Diferenças nulas ($p = 1.0$) |
| **RQ2** | **Defeitos (testes falhando)** | **0** | 0.00 | **0** | 0.00 | Diferenças nulas ($p = 1.0$) |
| **RQ3** | **Complexidade Ciclomática (CC)**| **7.00** | 5.50 | **5.50** | 4.75 | $W = 8.0, p = 0.0259$ *(Significativo)* |
| **RQ3** | **Tamanho do Código (LOC)** | **53.00** | 22.75 | **41.00** | 17.50 | $W = 0.0, p = 0.0003$ *(Significativo)* |
| **RQ3** | **Manutenibilidade (MI)** | **56.84** | 21.83 | **48.71** | 9.53 | $W = 37.0, p = 0.0342$ *(Significativo)* |
| **RQ3** | **Duplicação (%)** | **0.00%** | 0.00% | **0.00%** | 0.00% | Diferenças nulas |

#### Detecção de Outliers (Regra de Tukey 1.5x IQR)
- No tempo manual, o kata `04-garment-groups` foi identificado como outlier inferior ($42.43s$, $65.10s$ e $252.89s$), devido à simplicidade extrema da sua lógica ($N + G$).
- No tempo com IA, o kata `01-bario-world` com Claude ($448.53s$) figurou como outlier superior, decorrente de uma formulação inicial ambígua no prompt sobre a mecânica de saltos.

---

### 4.3 Discussão

#### RQ1 — Redução do Tempo de Resolução
- **Hipótese Informal:** Confirmada com extrema robustez.
- **Discussão:** O tempo mediano de resolução despencou de **982.76 segundos (~16,4 minutos)** na codificação manual para apenas **43.69 segundos** com o uso de IA — representando um **fator de aceleração (speedup) mediano de 22,5x**. O teste não-paramétrico pareado de Wilcoxon indicou significância estatística absoluta ($W = 0.0, p < 0.0001$). Quando analisado individualmente por participante, os três apresentaram $W = 0.0, p = 0.0312$, provando que o ganho de tempo independe da habilidade prévia individual do programador.

#### RQ2 — Taxa de Defeitos e Corretude
- **Hipótese Informal:** Confirmada.
- **Discussão:** Tanto a codificação manual quanto a guiada por IA atingiram 100% de aprovação nos testes em todos os trials ($20/20$). Em tarefas com especificação precisa e testes de aceitação automatizados rápidos, o desenvolvedor itera com a IA até a solução atingir o verde sem deixar defeitos residuais.

#### RQ3 — Estrutura e Qualidade do Código (CC, LOC, MI)
- **Hipótese Informal:** Confirmada e aprofundada.
- **Discussão:** 
  1. **LOC e Verbosidade:** O código gerado por IA é estatisticamente mais longo ($53$ vs $41$ linhas, $p = 0.0003$). A IA tende a incluir docstrings, tipagem estática e decomposição de variáveis intermediárias.
  2. **Complexidade Ciclomática:** A CC média do código de IA foi ligeiramente superior ($7.0$ vs $5.5$, $p = 0.0259$). As IAs frequentemente inserem checagens de guarda defensivas (`if not data: return`, validações de limites).
  3. **Índice de Manutenibilidade:** Apesar da maior complexidade pontual, o MI do código com IA foi significativamente melhor ($56.84$ vs $48.71$, $p = 0.0342$), pois a modularização e clareza das variáveis compensaram o tamanho adicional.

#### Análise das Inovações (30%)
- **Comparação entre Modelos:** Claude Sonnet 5, Gemini Flash 3.8 e GPT-4o apresentaram desempenho similar em taxa de sucesso (100%). O Gemini Flash destacou-se pela menor latência na geração e maior concisão em problemas de busca em grafo, enquanto Claude e GPT-4o geraram estruturas com nomes de métodos mais semânticos.
- **Ameaças à Validade:** O uso dos problemas da Maratona Mineira 2026 eliminou a memorização pura. O desenho *crossover* minimizou o efeito de aprendizado.

---

## 5. Conclusão

O experimento controlado demonstrou de forma inequívoca que os assistentes de IA generativa atuam como **potencializadores de produtividade de ordem de grandeza**, reduzindo o tempo de resolução de algoritmos em mais de 95% sem qualquer degradação na corretude funcional.

Em termos de qualidade de código, as soluções assistidas por IA são mais verbosas e contêm mais estruturas condicionais defensivas, mas resultam em código com excelente manutenibilidade estrutural. 

Como recomendação prática para a engenharia de software, o uso de assistentes de IA deve ser incentivado em conjunto com **testes automatizados de aceitação contínuos**, permitindo que o desenvolvedor usufrua da aceleração brutal de escrita mantendo garantias formais de qualidade.

---

## 6. Referências

- BASILI, Victor R.; CALDIERA, Gianluigi; ROMBACH, H. Dieter. *The Goal Question Metric Approach*. Encyclopedia of Software Engineering, p. 528-532, 1994.
- MCCABE, Thomas J. *A Complexity Measure*. IEEE Transactions on Software Engineering, v. SE-2, n. 4, p. 308-320, 1976.
- RADON. *Code Metrics in Python*. Disponível em: <https://radon.readthedocs.io/>.
- ZUSE, Horst. *A Framework of Software Measurement*. Walter de Gruyter, 2013.

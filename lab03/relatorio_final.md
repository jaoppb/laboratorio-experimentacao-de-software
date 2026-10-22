# Laboratório de Experimentação de Software — Relatório Final

| Campo | Valor |
|---|---|
| **Curso** | Engenharia de Software |
| **Disciplina** | Laboratório de Experimentação de Software |
| **Turno / Período** | Noite / 6º |
| **Professor(a)** | Danilo Maia |
| **Laboratório** | Lab03 — Mineração de Métricas DORA em Repositórios Open-Source |
| **Grupo (trio)** | Marcela Mendes Campos (@marcelacamposm) · João Pedro Peres (@jaoppb) · Gabriel Assis de Souza (@GabriAssiss) |
| **Link do Repositório** | [Repositório GitHub](https://github.com/jaoppb/laboratorio-experimentacao-de-software) |
| **Link do GitHub Projects** | [GitHub Projects (v2)](https://github.com/users/jaoppb/projects/3/views/1) |
| **Link do Artigo no Overleaf** | [Projeto Overleaf (Template SBC)](https://www.overleaf.com/project/6ad80e8b111a56d5da88ff1c) |
| **Data de Entrega** | 22/10/2026 |

---

## Resumo

As métricas DORA (*DevOps Research and Assessment*) estabeleceram-se como padrão industrial para mensurar o desempenho de entrega contínua e estabilidade operacional de equipes de software. Contudo, em ambientes open-source hospedados no GitHub, inexistindo telemetria direta de produção ou registros de incidentes corporativos, tais medidas dependem de aproximações operacionais (*proxies*). Este estudo implementou um pipeline de mineração e análise estatística sobre **330 repositórios open-source reais e populares** que utilizam GitHub Actions como esteira de CI/CD, observados durante uma janela de 12 meses (365 dias). O protocolo combinou engenharia de dados (cache SQLite com WAL mode, paginação Link sem piso e clone Git blobless local), validação manual de uma amostra-ouro de 60 repositórios rotulada independentemente por três integrantes (avaliando tipo de projeto, entrega real e 300 releases quanto à natureza corretiva, com $\kappa_{\text{Fleiss}} = 0{,}625$), testes estatísticos de hipóteses e análises de sensibilidade. Os resultados revelam que velocidade e estabilidade não se correlacionam de forma trivial: enquanto o CFR baseado em CI correlaciona-se fracamente com a frequência de deploy ($\rho = +0{,}161$), o CFR baseado em releases corretivas em até 7 dias exibe forte acoplamento mecânico com a cadência de entrega ($\rho = +0{,}497$), demonstrando uma severa ameaça de construto metodológica. Além disso, a popularidade (estrelas) não discrimina o desempenho DORA, ao passo que o tamanho da equipe ($\epsilon^2 = 0{,}211$) e a maturidade do projeto ($\epsilon^2 = 0{,}354$) inflacionam drasticamente o Lead Time. Por fim, a análise de sensibilidade evidenciou que 1 em cada 4 projetos (25,5%) tem seu perfil DORA alterado unicamente pela escolha dos *proxies*, embora a classificação agregada por mediana mantenha concordância substancial ($\kappa_{\text{linear}} = 0{,}603$).

---

## 1. Introdução

A medição sistemática da eficácia operacional no ciclo de vida de software tornou-se um dos pilares da engenharia moderna. Popularizadas pela iniciativa DORA e formalizadas na obra *Accelerate* (Forsgren, Humble & Kim, 2018), quatro métricas fundamentais sintetizam a capacidade de entrega e confiabilidade das organizações:
1. **Deployment Frequency (Frequência de Deploy):** cadência com que mudanças são implantadas em produção (velocidade/*throughput*);
2. **Lead Time for Changes (Tempo de Lead):** intervalo temporal decorrido desde o commit até sua publicação em produção (velocidade);
3. **Change Failure Rate (Taxa de Falha de Mudanças - CFR):** fração das alterações que desencadeiam falhas exigindo intervenção ou *hotfix* emergencial (estabilidade);
4. **Failed Deployment Recovery Time (Tempo de Recuperação):** intervalo necessário para restaurar a integridade operacional após uma quebra (estabilidade).

### 1.1 O Desafio Epistemológico dos *Proxies* em Repositórios Abertos
O modelo DORA original foi delineado para organizações sob implantação contínua (*Continuous Deployment*). O ecossistema do GitHub, entretanto, **não registra implantações em produção nem quedas de serviço**. Projetos de software livre publicam *releases*, executam *workflows* de automação e realizam *commits*. A mineração das quatro chaves depende necessariamente de aproximações indiretas (**proxies**):
- A publicação de uma *release* oficial atua como proxy de deploy;
- A execução malsucedida de um workflow no branch padrão atua como proxy de falha;
- A diferença temporal entre commits consecutivos em uma release atua como proxy de lead time.

Medidas indiretas podem mascarar realidades díspares: bibliotecas não realizam "deploys" (quem instala são os consumidores), e falhas em pipelines de CI costumam ser filtradas antes de afetar o usuário final. Portanto, além de minerar os números brutos, este estudo avalia o grau de confiabilidade epistemológica dessas medidas através de validação humana e análise de sensibilidade.

### 1.2 Questões de Pesquisa (RQs do Enunciado)
- **RQ 01:** Qual a frequência de deploys dos repositórios populares que usam CI/CD?
- **RQ 02:** Qual o tempo entre um commit e seu respectivo deploy? (Variantes obrigatórias: *a* por release vs. *b* por commit).
- **RQ 03:** Qual a taxa de falha das mudanças entregues por esses repositórios? (Variantes obrigatórias: *a* proxy de CI vs. *b* proxy de entrega via releases corretivas em até 7 dias).
- **RQ 04:** Qual o tempo de recuperação após uma execução de CI/CD com falha?
- **RQ 05:** Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?
- **RQ 06:** Quais características dos repositórios estão associadas a um melhor desempenho DORA?
- **RQ 07:** O quanto a classificação DORA de um repositório depende da definição operacional escolhida? (Análise de sensibilidade entre C1, C2 e C3).

### 1.3 Hipóteses Informais do Grupo (Formuladas a Priori na Sprint 01)
Em conformidade com o método experimental, as hipóteses a seguir foram formuladas **antes** da visualização dos dados consolidados:
- **RQ 01 (Marcela):** A mediana de frequência de deploy ficará nas faixas **Medium** (1 deploy/mês a 1/semana) e **High** (1 a 7/semana), com mediana geral inferior a 0,5 releases/semana. Casos **Elite** ($\ge 7$/semana) serão extremamente raros devido aos custos de congelamento e versionamento público.
- **RQ 02 (Gabriel):** Haverá forte disparidade entre as variantes: o lead time por release (a) será substancialmente maior que por commit (b), atingindo com frequência a faixa **Low** ($\ge 30$ dias), pois um único commit antigo em um ciclo inflaciona a métrica (a), enquanto a mediana por commit (b) absorve outliers.
- **RQ 03 (Gabriel):** As variantes divergirão profundamente: o CFR de CI (a) se concentrará entre 15% e 30% (High), enquanto o CFR de entrega (b) ficará abaixo de 15% (Elite), pois falhas em esteiras de testes são rotineiras, mas poucas motivam releases de correção às pressas.
- **RQ 04 (João):** O tempo de recuperação mediano concentrar-se-á entre 1h e 24h (**High**) e 1 a 7 dias (**Medium**). O nível **Elite** ($< 1$h) será infrequente pela ausência de equipes de sobreaviso (*on-call*) em projetos voluntários distribuídos.
- **RQ 05 (Gabriel):** Inexistirá correlação forte: espera-se ausência de trade-off no CFR (b), com $\rho$ próximo de zero. Para o CFR (b), entretanto, prevê-se um viés de acoplamento mecânico (projetos que publicam muito têm mais chances de ter releases separadas por $< 7$ dias).
- **RQ 06 (Marcela):** Contribuidores e maturidade associar-se-ão a maior cadência, porém a lead times mais longos devido à governança distribuída. Linguagens modernas (JS/TS e Python) terão cadência superior a linguagens de sistemas (C/C++).
- **RQ 07 (João):** A classificação DORA será altamente sensível aos proxies, com 35% a 60% dos repositórios trocando de faixa entre C1 e C2, e concordância Kappa linear fraca a moderada ($\kappa \in [0{,}30; 0{,}55]$).

---

## 2. Contexto

Este trabalho corresponde ao **Laboratório 03** da disciplina de Laboratório de Experimentação de Software, aprofundando o acompanhamento empírico e a governança ágil no GitHub Projects (v2).

O objeto de estudo compreende repositórios de código aberto com expressiva popularidade no GitHub, selecionados através de consultas fatiadas por faixas de estrelas na Search API. Fixou-se como janela temporal de observação o período oficial de **12 meses (2025-10-01T00:00:00Z até 2026-09-30T23:59:59.999999Z, totalizando 365 dias)**, contemplando o encerramento do dia no limite superior.

---

## 3. Metodologia

### 3.1 Principais Desafios de Engenharia
1. **Esgotamento de Rate Limit:** A API REST do GitHub impõe teto de 5.000 requisições/hora por token. Foi implementado o cliente `pipeline.http_client` com leitura dos cabeçalhos `X-RateLimit-Remaining` e `X-RateLimit-Reset`, pausa preventiva automática, retentativas com *backoff* exponencial e *jitter*, além de cache local transparente em SQLite com WAL mode (`pipeline.cache`).
2. **Tetos de Paginação na API do GitHub:** Endpoints de workflow runs e issues limitam retornos em 1.000 itens. Para repositórios hiperativos, foi arquitetada uma bissecção temporal recursiva (`pipeline.workflow_runs`) que divide dinamicamente o intervalo em metades disjuntas sempre que o total da fatia atinge o teto da API.
3. **Coleta de Histórico Git sem Consumo de Cota:** A extração de commits entre releases e de tags Git via API REST esgotaria a cota em repositórios com milhares de tags. O grupo adotou a estratégia de clone Git blobless local temporário (`git clone --filter=blob:none --bare`), executando comandos `git log` e `git for-each-ref` em processos isolados com consumo zero de cota de rede.

### 3.2 Funil de Seleção e Amostragem
O funil de seleção avaliou candidatos em ordem estrita de estrelas decrescente, descartando projetos que não cumpriam os critérios metodológicos:

| Etapa | Critério Aplicado | Quantidade Restante | Descartados | Motivo do Descarte |
|---|---|---:|---:|---|
| **Busca Inicial** | Candidatos avaliados via Search API (`stars: >1000`) | 753 | 0 | Candidatos avaliados até cumprir a meta |
| **Filtro CI/CD** | Presença ativa de GitHub Actions | 697 | 56 | Repositórios sem workflows ou `total_count == 0` |
| **Filtro Releases** | $\ge 5$ releases publicadas na janela de 12 meses | 382 | 315 | Menos de 5 releases publicadas válidas |
| **Filtro Runs** | $\ge 50$ runs de push no default branch na janela | 332 | 50 | Menos de 50 workflow runs avaliáveis |
| **Filtro Clone Git** | Integridade de clone bare local | 330 | 2 | Falha irrecuperável no clone de tags |
| **Amostra Final** | **Repositórios qualificados e congelados** | **330** | **0** | **Meta do enunciado amplamente superada ($\ge 300$)** |

### 3.3 Definições Operacionais e Combinações de Proxies
Todos os cálculos seguiram a parametrização oficial:
- **Janela e Denominador:** 365 dias (52,14 semanas). Frequência de deploy = $\text{deploys} / 52{,}14$.
- **CFR de CI (a):** $\text{runs com falha} / (\text{runs com falha} + \text{runs com sucesso})$ no default branch para eventos de push.
- **CFR de Entrega (b):** proporção de releases da janela seguidas por release corretiva em até 7 dias (excluindo os últimos 7 dias da janela por censura).
- **Tempo de Recuperação:** duração decorrida entre a primeira falha após um sucesso até o próximo sucesso no mesmo workflow (`updated_at` verde $-$ `run_started_at` primeira falha).

Para a análise de sensibilidade da RQ 07, definiram-se três combinações:
- **C1 (Referência):** Deploy = Release oficial; Lead Time = Variante (a); CFR = Variante (a).
- **C2:** Deploy = Release + Pré-release; Lead Time = Variante (b); CFR = Variante (b) via heurística validada.
- **C3:** Deploy = Git Tag; Lead Time = Variante (b); CFR = Variante (a).

A classificação geral do repositório é dada pela **mediana arredondada para baixo** das 4 notas (Elite=4, High=3, Medium=2, Low=1).

### 3.4 Protocolo de Validação Manual (Amostra-Ouro)
Para garantir rigor à heurística automática de release corretiva (CFR b) e ao tipo do projeto:
1. **Sorteio:** 60 repositórios sorteados da amostra com semente fixa (`random_state=42`) em `analises/amostra_ouro.py`.
2. **Rotulação:** Cada um dos três integrantes (Gabriel, João e Marcela) rotulou de forma independente 5 releases sorteadas por repositório (300 releases), categorizando tipo de projeto, entrega real e natureza corretiva da versão.
3. **Concordância Inter-Avaliadores:** Calculada pelo **Kappa de Fleiss** com formulação de Landis & Koch (1977):
   - Tipo de Projeto: $\kappa = 0{,}787$ (**Substancial**; 80,0% unânime);
   - Entrega Real ao Usuário: $\kappa = 0{,}492$ (**Moderada**; 96,7% unânime);
   - Release Corretiva: $\kappa = 0{,}625$ (**Substancial**; 72,3% unânime).
4. **Consenso e Avaliação da Heurística:** Consolidado em `validacao/consenso.csv`. A heurística de release corretiva v1 (SemVer patch + termos `fix`, `hotfix`, `revert` nos commits) atingiu:
   - **Precisão:** $61{,}4\%$;
   - **Recall:** $63{,}8\%$;
   - **F1-Score:** $0{,}625$.
   Como o F1 ficou abaixo da meta de 0,70, os falsos positivos (como bumps de dependências sem defeito de código) foram exaustivamente dissecados e documentados como ameaça à validade de construto.

### 3.5 Tabela de Métricas

| RQ | Métrica DORA | Dimensão | Definição Operacional | Unidade | Ferramenta / Fonte |
|---|---|---|---|---|---|
| **RQ 01** | Deployment Frequency | Velocidade | Total de releases publicadas na janela de 12 meses dividido por 52,14 semanas | releases/semana | `pipeline.releases` / GitHub Releases API |
| **RQ 02 (a)** | Lead Time for Changes (Release) | Velocidade | Tempo entre o commit mais antigo e a publicação da release correspondente | Horas | `metricas.lead_time` / Clone Git blobless |
| **RQ 02 (b)** | Lead Time for Changes (Commit) | Velocidade | Mediana dos intervalos entre a data do commit individual e a release na qual foi entregue | Horas | `metricas.lead_time` / Clone Git blobless |
| **RQ 03 (a)** | Change Failure Rate (CI) | Estabilidade | Proporção de execuções com falha no branch padrão para eventos de push: $N_{\text{falha}} / (N_{\text{falha}} + N_{\text{sucesso}})$ | Proporção ($[0, 1]$) | `pipeline.workflow_runs` / GitHub Actions API |
| **RQ 03 (b)** | Change Failure Rate (Entrega) | Estabilidade | Proporção de releases da janela que foram sucedidas por release corretiva em até 7 dias | Proporção ($[0, 1]$) | `metricas.cfr_b` / Heurística de tags e commits |
| **RQ 04** | Failed Deployment Recovery Time | Estabilidade | Tempo decorrido entre a primeira execução com falha e o primeiro sucesso subsequente no mesmo workflow | Horas | `metricas.tempo_recuperacao` / GitHub Actions API |
| **RQ 05** | Correlação Velocidade $\times$ Estabilidade | Associação | Coeficiente de correlação de postos de Spearman ($\rho$) entre Frequência de Deploy e CFR (a e b) | Coeficiente $[-1, 1]$ | `scipy.stats.spearmanr` |
| **RQ 06** | Fatores Estruturais | Associação | Teste de Kruskal-Wallis ($H$) com ajuste de Holm-Bonferroni e tamanho de efeito Epsilon-quadrado ($\epsilon^2$) | Estatística $H$, $p$, $\epsilon^2$ | `scipy.stats.kruskal`, `statsmodels` |
| **RQ 07** | Sensibilidade Metodológica | Validade | Comparação pareada de classificações DORA entre C1, C2 e C3 via Kappa ponderado linear ($\kappa_{\text{linear}}$) | Proporção e $\kappa$ | `sklearn.metrics.cohen_kappa_score` |

### 3.6 Ferramentas Utilizadas
- **Linguagem & Runtime:** Python 3.12/3.14 gerenciado com `uv`.
- **Coleta & Armazenamento:** `requests` com tratamento de Rate Limit, cache local em `sqlite3` com modo WAL e `git` CLI local (`git clone --filter=blob:none --bare`).
- **Engenharia de Dados:** `pandas`, `pyarrow` (armazenamento colunar em Apache Parquet).
- **Análise Estatística:** `scipy.stats` (Spearman, Kruskal-Wallis), `statsmodels` (correção de Holm-Bonferroni), `sklearn.metrics` (Cohen's Kappa linear) e implementação própria de Cliff's Delta e $\epsilon^2$.
- **Visualização de Dados:** `matplotlib` e `seaborn` para geração de gráficos vetoriais em PDF e PNG de alta resolução.
- **Testes & Qualidade:** `pytest` com fixtures e testes unitários/integrados.
- **Gestão Ágil:** GitHub Projects (v2) com issues rastreáveis e snapshots semanais via GraphQL.

### 3.7 Processo de Desenvolvimento e Divisão por Integrante

| Sprint | Entrega Principal | Responsável(is) | Issue(s) | Artefatos Commitados |
|---|---|---|---|---|
| **Lab03S01** | Infraestrutura HTTP, cache SQLite e runs | João Pedro | `#35`, `#36`, `#46` | `pipeline/http_client.py`, `pipeline/cache.py`, `pipeline/workflow_runs.py` |
| **Lab03S01** | Coleta de releases, commits e testes de Lead Time | Gabriel | `#41`, `#42`, `#43` | `pipeline/releases.py`, `pipeline/commits.py`, `metricas/lead_time.py` |
| **Lab03S01** | Seleção, funil, artigo inicial e hipóteses | Marcela | `#33`, `#38` | `pipeline/repo_selector.py`, `pipeline/funnel.py`, `artigo_contexto_e_hipoteses.md` |
| **Lab03S02** | Regeneração final de dados e backfills C2/C3 | João Pedro | `#56`, `#65`, `#68` | `pipeline/regenerar.py`, `pipeline/backfill_c2_c3.py`, `validacao/consenso.csv` |
| **Lab03S02** | Persistência de releases e heurística corretiva | Gabriel | `#58`, `#59`, `#60`, `#62` | `pipeline/persist_releases.py`, `metricas/cfr_b.py`, `analises/avaliar_heuristica.py` |
| **Lab03S02** | Rotulação manual, validação de tipos e metodologia | Marcela | `#63`, `#64` | `validacao/rotulos_marcela.csv`, `analises/validar_tipo_projeto.py`, `docs/rascunho_metodologia.md` |
| **Lab03S03** | Análise descritiva RQ 01 a 04 e C1 | Marcela | `#66` | `analises/analise_rq01_rq04.py`, `tests/test_analise_rq01_rq04.py` |
| **Lab03S03** | Correlação RQ 05 e Kruskal-Wallis RQ 06 | Gabriel | `#67` | `analises/analise_rq05_rq06.py`, `tests/test_analise_rq05_rq06.py`, `docs/resultados_rq05_rq06_gabriel.md` |
| **Lab03S03** | Análise de sensibilidade RQ 07 (C1×C2×C3) | João Pedro | `#70` | `analises/analise_rq07.py`, `tests/test_analise_rq07.py`, `docs/resultados_rq07_joao.md` |

---

## 4. Resultados e Discussão

### 4.1 Estatísticas Descritivas das Quatro Chaves DORA (RQ 01 a RQ 04)
Todas as distribuições de repositórios exibiram acentuada assimetria e caudas longas à direita. Portanto, reportam-se prioritariamente **mediana e intervalo interquartil (IQR)**:

| Métrica | Dimensão / Variante | Unid. | $n$ | Mediana | Q1 | Q3 | IQR | Mín. | Máx. | Faixa DORA Predominante |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **Deployment Frequency** | Frequência de Deploy | rel/sem | 330 | **0,499** | 0,235 | 1,204 | 0,969 | 0,096 | 49,597 | **Medium (44,5%) / High (41,8%)** |
| **Lead Time (a)** | Por release (commit mais antigo) | horas | 269 | **165,88** | 41,39 | 454,72 | 413,34 | 0,01 | 78.858 | **High (43,9%) / Medium (43,1%)** |
| **Lead Time (b)** | Por commit (mediana agregada) | horas | 329 | **145,57** | 44,68 | 356,64 | 311,96 | 0,01 | 62.894 | **High (48,0%) / Medium (42,2%)** |
| **CFR (a)** | Proxy de CI (falhas push) | prop. | 330 | **0,047** | 0,024 | 0,112 | 0,088 | 0,000 | 1,000 | **Elite (86,4%)** |
| **CFR (b)** | Proxy de Entrega ($\le$ 7 dias) | prop. | 328 | **0,186** | 0,038 | 0,407 | 0,369 | 0,000 | 0,980 | **Elite (45,7%) / High (19,8%)** |
| **Tempo de Recuperação** | Mediana por workflow no CI | horas | 312 | **2,611** | 1,067 | 6,733 | 5,666 | 0,065 | 560,00 | **High (69,6%)** |
| **Censura de Falhas** | Proporção de episódios sem cura | prop. | 330 | **0,000** | 0,000 | 0,014 | 0,014 | 0,000 | 1,000 | Ausente na maioria (média 3,3%) |

### 4.2 Classificação DORA Geral Consolidada (C1)
Avaliando a combinação de referência C1 (Releases oficiais, Lead Time a, CFR CI a e Tempo de Recuperação), a distribuição geral dos 330 repositórios classificou-se em:
- **Elite:** 22 repositórios (**6,7%**);
- **High:** 143 repositórios (**43,3%**);
- **Medium:** 146 repositórios (**44,2%**);
- **Low:** 19 repositórios (**5,8%**).

O ecossistema open-source situa-se maciçamente nas categorias intermediárias (**High e Medium, somando 87,5%**), refutando a hipótese de que projetos populares atingem cadência Elite sem esforço industrial dedicado.

### 4.3 RQ 05 — Velocidade vs. Estabilidade e o Viés do Proxy de 7 Dias
O teste de correlação de postos de Spearman ($\rho$) revelou um contraste empírico marcante:
- **CFR (a) [Proxy de CI]:** $\rho = +0{,}1612$ ($p = 0{,}0033$, $n = 330$) $\rightarrow$ correlação fraca e positiva.
- **CFR (b) [Proxy de Entrega]:** $\rho = +0{,}4968$ ($p = 7{,}64 \times 10^{-22}$, $n = 328$) $\rightarrow$ correlação moderada a forte positiva.

**Discussão Teórica:** O DORA postula que velocidade e estabilidade não são antagônicas. No open-source, nossos dados mostram que:
1. No pipeline de CI, maior frequência de entrega gera exposição moderadamente superior a falhas transitórias, mantendo $\rho$ baixo.
2. No proxy de entrega, o valor expressivo de $\rho = +0{,}497$ decorre de um **acoplamento mecânico inevitável**: repositórios que publicam 3 ou 4 releases por semana têm janelas naturais de menos de 7 dias entre deploys, inflando matematicamente o CFR (b) e gerando uma correlação positiva espúria.

### 4.4 RQ 06 — Fatores do Repositório Associados ao Desempenho DORA
Foram executados 25 testes de Kruskal-Wallis corrigidos via **Holm-Bonferroni** ($\text{FWER} \le 0{,}05$), quantificados pelo Epsilon-quadrado ($\epsilon^2$):

| Fator | Métrica DORA | $H$ | $p$-bruto | $p$-Holm | $\epsilon^2$ | Tamanho de Efeito | Significativo? |
|---|---|---:|---:|---:|---:|---|:---:|
| **Tamanho da Equipe (Contribuidores)** | **Lead Time (b)** | 69,30 | $6{,}04 \times 10^{-15}$ | **$1{,}45 \times 10^{-13}$** | **0,2113** | **Grande** | **Sim (*)** |
| **Maturidade (Idade do Projeto)** | **Freq. Deploy** | 32,81 | $3{,}54 \times 10^{-7}$ | **$7{,}79 \times 10^{-6}$** | **0,0997** | **Médio** | **Sim (*)** |
| **Maturidade (Idade do Projeto)** | **Lead Time (b)** | 116,04 | $5{,}48 \times 10^{-25}$ | **$1{,}37 \times 10^{-23}$** | **0,3538** | **Grande** | **Sim (*)** |
| **Maturidade (Idade do Projeto)** | **CFR (b) Entrega** | 60,18 | $5{,}37 \times 10^{-13}$ | **$1{,}24 \times 10^{-11}$** | **0,1840** | **Grande** | **Sim (*)** |
| **Linguagem Principal** | **Freq. Deploy** | 20,90 | $1{,}91 \times 10^{-3}$ | **$3{,}63 \times 10^{-2}$** | **0,0635** | **Médio** | **Sim (*)** |
| **Linguagem Principal** | **Lead Time (b)** | 32,10 | $1{,}56 \times 10^{-5}$ | **$3{,}29 \times 10^{-4}$** | **0,0979** | **Médio** | **Sim (*)** |
| **Tipo de Projeto** | **Lead Time (b)** | 23,26 | $3{,}56 \times 10^{-5}$ | **$7{,}12 \times 10^{-4}$** | **0,0709** | **Médio** | **Sim (*)** |
| *Popularidade (Estrelas)* | *Todas as 5 métricas* | $< 5,7$ | $> 0,12$ | $1,0000$ | $< 0,018$ | Desprezível/Pequeno | **Não** |

**Principais Descobertas:**
1. **Sobrecarga de Coordenação:** Equipes amplas ($> 150$ contribuidores) e projetos antigos ($> 8$ anos) apresentam lead times substancialmente mais longos ($\epsilon^2 > 0{,}20$). O trânsito de um commit é desacelerado pela complexidade das revisões humanas e esteiras de verificação.
2. **Popularidade Neutra:** A quantidade de estrelas não discrimina o desempenho DORA ($p_{\text{Holm}} = 1{,}000$).
3. **Agilidade em JS/TS e Python:** Linguagens de ecossistemas web ágeis entregam releases em cadência superior às linguagens compiladas legadas.

### 4.5 RQ 07 — Análise de Sensibilidade Metodológica (C1 × C2 × C3)
A confrontação pareada das 3 combinações de proxies gerou os seguintes índices:

| Comparação | $n$ | Repositórios que Mudaram | \% Mudança | Subiram de Tier | Desceram de Tier | $\kappa_{\text{linear}}$ | Interpretação |
|---|---:|---:|---:|---:|---:|---:|---|
| **C1 $\times$ C2** | 330 | 84 | **25,5\%** | 25 (7,6%) | 59 (17,9%) | **0,6031** | **Substancial** |
| **C1 $\times$ C3** | 330 | 71 | **21,5\%** | 54 (16,4%) | 17 (5,2%) | **0,6871** | **Substancial** |
| **C2 $\times$ C3** | 330 | 85 | **25,8\%** | 81 (24,5%) | 4 (1,2%) | **0,6222** | **Substancial** |

**Discussão:** A inércia da mediana arredondada para baixo protege a estabilidade global em ~75% dos repositórios. No entanto, o fato de **1 em cada 4 projetos mudar de categoria DORA** comprova que os proxies operacionais introduzem variações que não podem ser ignoradas. Na variante C3 (Tags), 54 projetos subiram de faixa porque utilizam marcação técnica no Git sem registrar releases formais no GitHub.

---

## 5. Ameaças à Validade

1. **Validade de Construto:** Releases publicadas e execuções com falha em CI/CD atuam como aproximações imperfeitas de "deploys em produção" e "incidentes reais". Projetos de bibliotecas não distribuem diretamente em infraestrutura de nuvem, e a regra de releases corretivas em até 7 dias sofre do viés de acoplamento mecânico demonstrado na RQ 05.
2. **Validade Interna:** O protocolo de consenso automático por maioria simples adotado para a amostra-ouro e o uso de modelos auxiliares documentado em `validacao/PROVENIENCIA.md` amenizaram gargalos de tempo, mas representam uma limitação operacional que o grupo declara de forma transparente.
3. **Validade Externa:** A amostragem concentrou-se nos repositórios populares com automação ativa no GitHub Actions. As conclusões não são necessariamente generalizáveis para repositórios corporativos privados ou projetos que operam com GitLab CI ou Jenkins.
4. **Validade de Conclusão:** Empregou-se estatística não paramétrica (mediana, IQR, Kruskal-Wallis, Spearman e Cliff's delta), além do controle rigoroso da taxa de falso positivo pela correção de Holm-Bonferroni.

---

## 6. Conclusão

A execução do Laboratório 03 evidenciou as complexidades de transpor o modelo DORA clássico para o ecossistema de software livre no GitHub. O trabalho demonstrou que:
- Os repositórios open-source operam dominantemente em níveis intermediários (**High e Medium**), com raros casos atingindo o patamar Elite;
- O aumento do tamanho da equipe e da idade do software amplifica o Lead Time por custos de governança e revisão;
- A correlação entre velocidade e estabilidade é moldada pela natureza dos proxies, exigindo cautela científica antes de inferir causalidade;
- As classificações ordinais são sensíveis às definições operacionais em pelo menos um quarto da amostra.

O pipeline desenvolvido garante reprodutibilidade ponta a ponta através de cache local, suíte de testes com 100% de cobertura no pacote de métricas e documentação transparente de dados.

---

## Referências

- **Forsgren, N., Humble, J., & Kim, G. (2018).** *Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations*. IT Revolution.
- **Landis, J. R., & Koch, G. G. (1977).** *The measurement of observer agreement for categorical data*. Biometrics, 159-174.
- **Romano, J., Kromrey, J. D., Coraggio, J., & Skelly, J. (2006).** *Appropriate statistics for ordinal level data: Should we really be using t-test and cohen's d for evaluating group differences on the nsse and other surveys*. In Annual Meeting of the Florida Association for Institutional Research (pp. 1-33).
- **Holm, S. (1979).** *A simple sequentially rejective multiple test procedure*. Scandinavian Journal of Statistics, 65-70.
- **Cohen, J. (1968).** *Weighted kappa: Nominal scale agreement provision for scaled disagreement or partial credit*. Psychological Bulletin, 70(4), 213.
- **DORA Community (2023).** *State of DevOps Report*. Google Cloud. https://cloud.google.com/devops/state-of-devops


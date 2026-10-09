# Hipóteses Informais — RQ 04 e RQ 07

> **Referência:** Issue #40 — Hipóteses RQ04 e RQ07  
> **Autor:** João Pedro Peres (jaoppb)  
> **Contexto:** Seção de Introdução do artigo científico (SBC / Overleaf).  
> **Protocolo:** Rascunho formulado *a priori*, **antes** de qualquer coleta ou análise dos dados da amostra, em conformidade com o guia metodológico do Lab03.

---

## RQ 04 — Qual o tempo de recuperação após uma execução de CI/CD com falha?

### Definição Operacional
O tempo de recuperação é calculado em horas a partir de episódios de falha ocorridos em um mesmo workflow executado no default branch (`main` ou `master`). Um episódio tem início na primeira execução com falha (`conclusion != 'success'`) imediatamente após uma execução bem-sucedida, e se encerra na primeira execução bem-sucedida subsequente do mesmo workflow. A métrica do episódio corresponde a:
$$\text{Tempo de Recuperação} = \text{updated\_at}_{\text{sucesso}} - \text{run\_started\_at}_{\text{primeira\_falha}}$$
O valor do repositório é determinado pela **mediana** de todos os episódios completados de todos os seus workflows na janela de 12 meses. Episódios que não atingem uma execução bem-sucedida até o término da janela são tratados como **censurados** (reportando-se a taxa de censura).

Faixas de referência DORA:
- **Elite:** $< 1$ hora
- **High:** $1$ hora a $< 1$ dia ($24$ horas)
- **Medium:** $1$ dia a $< 1$ semana ($168$ horas)
- **Low:** $\ge 1$ semana ($\ge 168$ horas)

### Hipótese Informal
- **Distribuição e Classificação:** Esperamos que a mediana do tempo de recuperação dos repositórios open-source populares se concentre prioritariamente nas faixas **High** ($1$h a $< 24$h) e **Medium** ($1$ dia a $< 7$ dias), com valor central típico entre algumas horas e 2 dias.
- **Raridade de Elite:** Repositórios com mediana geral no nível **Elite** ($< 1$ hora) serão raros. Embora correções pontuais quase imediatas ocorram para falhas triviais (ex.: revert rápido de commit ou correção de sintaxe/linter), a mediana agregada de múltiplos episódios e workflows raramente ficará abaixo de 1 hora.
- **Incidência de Low e Assimetria:** A faixa **Low** ($\ge 1$ semana) estará presente em uma parcela minoritária, concentrada em repositórios com workflows agendados (*cron/nightly*) ou não impeditivos. A distribuição intra-repositório apresentará forte assimetria positiva (cauda longa à direita com IQR amplo).
- **Episódios Censurados:** Esperamos uma proporção perceptível de episódios censurados (estimada entre 5% e 15% do total de episódios), decorrente de testes experimentais em matrizes de dependências ou workflows secundários abandonados/renomeados durante o ano.

### Por quê (Justificativa Teórica e Prática)
1. **Dinâmica Colaborativa Open-Source vs. Ambientes Corporativos:** A definição clássica do DORA (*Accelerate*) pressupõe equipes com cobertura de plantão (*on-call/SRE*) e metas contratuais de SLA para restabelecer sistemas em produção em minutos. No desenvolvimento em software livre, contribuidores e mantenedores atuam de forma voluntária, assíncrona e distribuída em fusos horários distintos. O ciclo de percepção da falha, discussão em issues/PRs e aprovação de revisão demanda tipicamente horas ou dias.
2. **Semântica do Proxy (CI/CD vs. Incidente de Produção):** Uma execução vermelha no default branch representa falha de integração/validação contínua, não necessariamente interrupção de serviço aos usuários finais (muitos projetos são bibliotecas ou utilitários CLI). Portanto, o senso de emergência para correção imediata ("código vermelho") é mitigado, salvo quando a quebra bloqueia merges essenciais ou releases pendentes.
3. **Heterogeneidade de Workflows:** Repositórios mantêm workflows com propósitos variados: pipelines críticos de build/teste rápido (corrigidos em poucas horas) coexistem com pipelines auxiliares de análise estática, checagem de documentação e matrizes de compatibilidade com dependências externas. Estes últimos são mais suscetíveis a testes instáveis (*flaky tests*) e podem permanecer em falha por dias sem comprometer o fluxo principal de desenvolvimento.

---

## RQ 07 — O quanto a classificação DORA de um repositório depende da definição operacional escolhida?

### Definição Operacional
Análise de sensibilidade comparando a classificação geral dos repositórios nas quatro categorias DORA (**Elite**, **High**, **Medium**, **Low**) sob pelo menos três combinações metodológicas de proxies:
- **C1 (Referência):** Deploy = Release oficial; Lead Time = Variante (a) [commit mais antigo da release]; CFR = Variante (a) [proxy de CI no default branch].
- **C2:** Deploy = Release oficial + pré-release; Lead Time = Variante (b) [mediana por commit entregue]; CFR = Variante (b) [proxy de entrega: release corretiva em até 7 dias].
- **C3:** Deploy = Git Tag; Lead Time = Variante (b); CFR = Variante (a).

Para cada combinação, cada métrica recebe pontuação de 1 a 4 (Low=1, Medium=2, High=3, Elite=4) e a categoria final do repositório é dada pela **mediana arredondada para baixo**. A estabilidade das conclusões é quantificada por:
1. Proporção (%) de repositórios que sofrem transição de categoria entre pares ($C1 \times C2$, $C1 \times C3$, $C2 \times C3$).
2. Coeficiente Kappa de Cohen ponderado linear ($\kappa_{\text{linear}}$) entre as classificações pareadas.

### Hipótese Informal
- **Alta Sensibilidade:** Esperamos que a classificação DORA de um repositório seja **altamente sensível** à definição operacional adotada, refutando a premissa de que os proxies operacionais em repositórios abertos sejam intercambiáveis.
- **Taxa Expressiva de Migração:** Esperamos que entre **35% e 60%** dos repositórios alterem sua categoria DORA geral ao confrontar a combinação C1 com as variantes C2 e C3.
- **Concordância Moderada a Fraca:** Esperamos que o coeficiente Kappa ponderado linear entre C1 e C2 fique na faixa **$\kappa \in [0{,}30; 0{,}55]$**, refletindo concordância apenas fraca a moderada. Entre C1 e C3, esperamos concordância moderada ($\kappa \in [0{,}45; 0{,}65]$).
- **Viés Sistemático de Otimismo em C2:** A combinação C2 tenderá a classificar os repositórios em níveis de maturidade DORA **sistematicamente superiores** à combinação C1:
  - O CFR (b) (releases corretivas $\le 7$ dias) tende a concentrar-se na faixa Elite ($\le 15\%$), enquanto o CFR (a) (falhas de CI) frequentemente atinge High ($15\text{--}30\%$) ou Medium;
  - O Lead Time (b) (mediana por commit) reduz expressivamente a métrica em comparação à variante (a) (commit mais antigo), que é facilmente inflada por commits residuais e backports;
  - A inclusão de pré-releases eleva o volume de eventos de entrega, favorecendo faixas superiores de Deployment Frequency.
- **Efeito de Tags em C3:** A utilização de tags (C3) resgatará projetos que empregam versionamento Git estrito mas não publicam *Releases* formais na interface do GitHub, elevando substancialmente a frequência de deploy desses casos específicos.

### Por quê (Justificativa Teórica e Metodológica)
1. **Distância Semântica dos Proxies em Relação ao Construto Teórico:** No modelo DORA original, as métricas foram concebidas a partir de surveys sobre serviços web com telemetria direta de produção e incidentes reais. Na mineração de repositórios, a ausência desses dados impõe o uso de aproximações indiretas que medem fenômenos ontologicamente distintos:
   - Lead Time (a) reflete a cadência de congelamento do ciclo de release, ao passo que (b) reflete o tempo de trânsito médio das contribuições individuais.
   - CFR (a) captura o ruído e a fricção dos testes no branch de integração, enquanto CFR (b) detecta crises de entrega pós-distribuição graves o bastante para justificar nova release emergencial.
   - Releases oficiais comunicam estabilidade para a comunidade externa, enquanto Git Tags representam marcadores puramente técnicos.
2. **Sensibilidade do Mecanismo de Agregação por Mediana Discreta:** A agregação das quatro métricas em faixas discretas (1 a 4) com corte por mediana arredondada para baixo introduz instabilidade em repositórios com notas limítrofes. A mudança de uma única métrica (por exemplo, CFR caindo de High para Elite) é suficiente para alternar o status global do projeto entre Medium e High.
3. **Implicações para Validade de Construto:** Demonstrar que as conclusões variam em função da parametrização do pipeline é fundamental para a integridade científica do estudo. A confirmação dessa hipótese reforça a necessidade de transparência metodológica e de cautela antes de transferir classificações DORA corporativas para o ecossistema open-source.

---

## Texto Formatado para o Artigo SBC (Overleaf / LaTeX)

O bloco a seguir está pronto para ser transposto diretamente para a seção de Introdução do artigo no Overleaf durante a consolidação da Issue #45:

```latex
\noindent \textbf{Hipótese da RQ 04 (Tempo de Recuperação).}
\textit{Qual o tempo de recuperação após uma execução de CI/CD com falha?}
Operacionalizado como a mediana da duração de episódios de falha em workflows do \textit{default branch} (tempo decorrido entre o início da primeira falha após um sucesso e a conclusão da primeira execução verde subsequente), espera-se que os repositórios concentrem-se predominantemente nas faixas \textbf{High} (1 hora a 24 horas) e \textbf{Medium} (1 a 7 dias), sendo a faixa \textbf{Elite} ($< 1$ hora) rara em nível de mediana agregada. Além disso, prevê-se uma proporção relevante de episódios censurados (entre 5\% e 15\%) e distribuição com acentuada cauda longa à direita.
\textit{Justificativa:} Diferente de ambientes corporativos com equipes de resposta a incidentes (\textit{on-call}) e SLAs imediatos, projetos de código aberto dependem de mantenedores voluntários atuando de forma assíncrona através de fusos horários distintos. Ademais, falhas em esteiras de CI/CD representam problemas de integração e validação que nem sempre paralisam serviços em produção, atenuando a urgência de intervenção em comparação a incidentes reais de infraestrutura. Workflows secundários ou de checagem periódica também tendem a permanecer em falha por períodos prolongados sem interromper a atividade central do repositório.

\vspace{0.8em}
\noindent \textbf{Hipótese da RQ 07 (Análise de Sensibilidade).}
\textit{O quanto a classificação DORA de um repositório depende da definição operacional escolhida?}
Avaliando a concordância entre a combinação de referência C1 (release oficial, lead time pelo commit mais antigo e CFR via falhas de CI) e as variantes C2 (inclusão de pré-releases, lead time por commit e CFR por releases corretivas em até 7 dias) e C3 (deploy via git tags), espera-se que a classificação geral dos repositórios seja \textbf{altamente sensível} às definições operacionais, com 35\% a 60\% dos projetos mudando de faixa e coeficiente Kappa de Cohen ponderado linear indicando concordância apenas fraca a moderada ($\kappa \in [0{,}30; 0{,}55]$ entre C1 e C2). Espera-se ainda que C2 resulte em classificações sistematicamente mais otimistas que C1.
\textit{Justificativa:} No ecossistema open-source do GitHub inexiste telemetria direta de produção, exigindo \textit{proxies} que capturam construtos qualitativamente distintos: falhas de CI mensuram a volatilidade dos testes no branch compartilhado, enquanto releases corretivas refletem apenas falhas severas percebidas pós-distribuição; similarmente, o lead time pelo commit mais antigo captura o tempo total de espera de um ciclo de versão, ao passo que a mediana por commit mede a latência típica de mudanças individuais. A agregação em categorias ordinais pela mediana amplifica oscilações nas fronteiras de corte, evidenciando uma ameaça primária à validade de construto que impede a adoção acrítica de classificações DORA em repositórios abertos.
```

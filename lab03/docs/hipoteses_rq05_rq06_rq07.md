# Hipóteses informais consolidadas — RQ 05, RQ 06 e RQ 07

> Consolidação para a Introdução do artigo (Issues #45 e #50): uma hipótese por RQ, com o mesmo
> formato e a mesma terminologia nas três.
> **Fontes (a priori, versionadas antes dos dados):**
> RQ 05 em `docs/hipoteses_rq02_rq03_rq05.md` (#44), RQ 06 em `artigo_contexto_e_hipoteses.md`
> (Marcela, #33) e RQ 07 em `docs/hipoteses_rq04_rq07.md` (João, #40).
> **Regra desta consolidação:** nenhuma previsão foi alterada, acrescentada ou removida. Mudou só a
> forma (ordem, termos, divisão em itens testáveis). Como o dataset já existe, qualquer mudança de
> conteúdo agora deixaria de ser *a priori*. O que foi mexido está na seção "Notas de consolidação".

## Termos usados nas três RQs

- **Frequência de deploy:** releases publicadas na janela ÷ 52,14 semanas (365/7) (RQ 01).
- **CFR (a):** proxy de CI, falha de *pipeline* no default branch. **CFR (b):** proxy de entrega,
  release seguida de release corretiva em até 7 dias (RQ 03).
- **Faixas DORA:** Elite, High, Medium, Low, pelos cortes fixos do guia; classificação geral pela
  mediana das quatro notas, arredondada para baixo.
- **C1, C2, C3:** combinações de definições da análise de sensibilidade (C1 = referência).

---

## RQ 05 — Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?

**Hipótese.** Esperamos **ausência de *trade-off*** entre velocidade e estabilidade, em linha com o
DORA, mas com sinais diferentes conforme a variante do CFR:

- **H5.1 (CFR b):** correlação de Spearman **fraca e negativa, ou próxima de zero**, entre
  frequência de deploy e CFR (b).
- **H5.2 (CFR a):** correlação de Spearman **fraca e positiva** entre frequência de deploy e CFR (a).

**Por quê.** Quem publica com frequência tende a ter automação madura (testes, release
automatizada), o que reduz as falhas que exigem release corretiva (H5.1). Já projetos muito ativos
executam mais *workflows*, e mais variados, o que aumenta a chance de falha de *pipeline* sem que a
entrega piore (H5.2). Há um viés conhecido no CFR (b): quem publica muitas releases tem mais chance
de ter duas releases a menos de 7 dias uma da outra, o que pode inflar o CFR (b) e gerar uma
correlação positiva espúria. Correlação não implica causalidade.

**Como será testada.** `scipy.stats.spearmanr`, separadamente para CFR (a) e CFR (b), reportando
ρ, p-valor e n (o n pode diferir entre as variantes, porque o CFR (b) é nulo quando nenhuma release
pôde ser avaliada). Gráfico de dispersão com eixo logarítmico na frequência de deploy.

---

## RQ 06 — Quais características dos repositórios estão associadas a um melhor desempenho DORA?

**Hipótese.** Esperamos que o desempenho DORA varie com o porte, a idade, o ecossistema e o tipo do
repositório, nas direções abaixo:

- **H6.1 (contribuidores):** repositórios com mais contribuidores têm **maior frequência de deploy**,
  mas tempo de recuperação **mais heterogêneo** (IQR mais largo).
- **H6.2 (popularidade):** repositórios com mais estrelas têm **maior frequência de deploy**, mas
  tempo de recuperação **mais heterogêneo**.
- **H6.3 (idade):** repositórios mais antigos têm **menor CFR (a)**.
- **H6.4 (linguagem):** ecossistemas com empacotamento e automação ágeis (JavaScript/TypeScript e
  Python) têm **maior frequência de deploy** que linguagens voltadas a sistemas legados ou de
  compilação extensa.
- **H6.5 (tipo do projeto):** aplicações/serviços e ferramentas CLI têm **maior frequência de deploy**
  que bibliotecas/frameworks. *Tipo rotulado por agentes de IA nos 330 (Issue #69; ver notas).*

**Por quê.** O tamanho da base colaborativa e o tipo de artefato moldam a governança do repositório.
Mais contribuidores e mais visibilidade dão mais vazão de mudanças, mas uma equipe distribuída e com
revisão mais lenta reage de forma desigual às falhas (H6.1, H6.2). Projetos antigos tiveram mais
tempo para estabilizar o CI (H6.3). Ecossistemas com publicação simples em registro de pacotes
facilitam releases frequentes (H6.4). Bibliotecas precisam de salvaguardas extras para não quebrar
a API ou a compatibilidade binária de quem depende delas, o que espaça as releases (H6.5).

**Como será testada.** Fatores numéricos agrupados por quartis. Kruskal-Wallis para fatores com 3 ou
mais grupos e Mann-Whitney para 2 grupos, sobre as métricas das RQ 01 a 04; p-valores corrigidos
por Holm; tamanho de efeito por ε² = H/(n − 1) e Cliff's δ (Romano et al., 2006). A parte
"heterogêneo" de H6.1 e H6.2 é sobre dispersão, que esses testes não medem: será avaliada pela
comparação descritiva do IQR entre os grupos.

---

## RQ 07 — O quanto a classificação DORA de um repositório depende da definição operacional escolhida?

**Hipótese.** Esperamos que a classificação geral seja **altamente sensível** à definição
operacional, isto é, que os proxies não sejam intercambiáveis:

- **H7.1 (migração):** entre **35% e 60%** dos repositórios mudam de categoria geral ao comparar C1
  com C2 e com C3.
- **H7.2 (concordância):** kappa de Cohen ponderado linear em **[0,30; 0,55]** entre C1 e C2
  (fraca a moderada) e em **[0,45; 0,65]** entre C1 e C3 (moderada).
- **H7.3 (otimismo de C2):** C2 classifica os repositórios em faixas **sistematicamente superiores**
  às de C1.
- **H7.4 (tags em C3):** C3 eleva a frequência de deploy dos projetos que versionam por tag mas não
  publicam releases formais no GitHub.

**Por quê.** Sem telemetria de produção, cada proxy mede um fenômeno diferente. O CFR (b) tende a
cair na faixa Elite e o CFR (a) em High ou Medium (RQ 03); o lead time (b) é bem menor que o (a),
que é inflado por commits antigos e *backports* (RQ 02); e incluir pré-releases aumenta o número de
entregas. Todos esses efeitos empurram C2 para cima (H7.3). Releases oficiais comunicam
estabilidade à comunidade, enquanto tags são marcadores técnicos (H7.4). Por fim, a agregação em
quatro faixas pela mediana arredondada para baixo amplifica oscilações perto dos cortes: basta uma
métrica mudar de faixa para a nota geral mudar (H7.1, H7.2).

**Como será testada.** Para cada combinação, classificação de cada repositório com as funções de
`metricas/dora.py`. Para cada par (C1×C2, C1×C3, C2×C3): porcentagem de repositórios que mudaram de
categoria e `cohen_kappa_score(..., weights='linear')`. H7.3 é verificada pela direção das mudanças
(quantos sobem × quantos descem de C1 para C2).

---

## Coerência entre as três hipóteses

- **RQ 05 e RQ 07 dependem da hipótese da RQ 03.** Se as duas variantes do CFR divergem como
  previsto (CFR b em Elite, CFR a em High), então a correlação com a frequência de deploy tem sinais
  diferentes (H5.1 × H5.2) e a troca de CFR (a) por CFR (b) puxa a classificação para cima em C2
  (H7.3). As três previsões vêm da mesma premissa: CFR (a) mede atrito de CI, CFR (b) mede falha de
  entrega.
- **RQ 05 e RQ 06 se complementam.** A RQ 05 olha a relação velocidade × estabilidade em toda a
  amostra; a RQ 06 pergunta quais características separam os repositórios. H6.1 e H6.2 preveem mais
  vazão sem prever pior estabilidade, o que é consistente com a ausência de *trade-off* da RQ 05.
- **A RQ 07 qualifica as RQ 01 a 06.** Se H7.1 e H7.2 se confirmarem, as conclusões das outras RQs
  valem só para a definição de referência (C1), e isso vai para as ameaças à validade de construto.

---

## Notas de consolidação (o que mudou em relação às fontes)

1. **Formato.** As três RQs seguem o mesmo molde: Hipótese (com sub-hipóteses numeradas H5.x, H6.x,
   H7.x), Por quê e Como será testada. Os textos originais tinham formatos diferentes (lista curta,
   lista longa, seções com justificativa em três itens).
2. **RQ 06, item 1 da fonte dividido em H6.1 e H6.2.** A fonte juntava contribuidores e
   popularidade numa só previsão. Como no guia eles são fatores separados (quartis de cada um), cada
   um virou uma sub-hipótese, com a mesma previsão.
3. **RQ 06, "heterogêneo".** A fonte prevê tempos de recuperação "mais heterogêneos". Kruskal-Wallis
   não testa dispersão, então registramos que isso será lido pelo IQR, de forma descritiva. A
   previsão em si não mudou.
4. **RQ 07, texto encurtado.** A justificativa do João foi resumida e ligada às hipóteses das
   RQ 02 e 03 (as mesmas premissas). Os intervalos numéricos (35–60%, κ em [0,30; 0,55] e
   [0,45; 0,65]) foram mantidos exatamente.
5. **Sem limiar para "fraca" na RQ 05.** A fonte não fixou um valor de ρ para "fraca". Não
   acrescentamos um agora, porque o dataset já existe e um corte escolhido depois dos dados não seria
   *a priori*. Na discussão, usar a leitura usual e dizer que ela não foi pré-registrada.
6. **Pendências que podem mudar o texto:**
   - **#69 (tipo do projeto).** O grupo decidiu (20/10/2026) rotular o tipo nos 330 repositórios com
     agentes de IA, então H6.5 fica. Se a acurácia dos agentes contra os rótulos humanos for baixa,
     H6.5 deve ser tratada como exploratória (Metodologia, 3.8). Ainda falta decidir o que fazer com a
     categoria `outro`.
   - **CFR (b) de C2.** O grupo decidiu calcular o CFR (b) de C2 sobre as unidades de C2 (releases +
     pré-releases; Metodologia, 3.5.6), como a H7.3 supõe.

---

## Texto para o artigo SBC (Overleaf / LaTeX)

Bloco pronto para a Introdução, no mesmo estilo do bloco da RQ 04 em `docs/hipoteses_rq04_rq07.md`.

```latex
\noindent \textbf{Hipótese da RQ 05 (velocidade $\times$ estabilidade).}
\textit{Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?}
Espera-se \textbf{ausência de \textit{trade-off}}, em linha com o DORA: correlação de Spearman fraca e negativa, ou próxima de zero, entre a frequência de deploy e o CFR (b), e fraca e positiva entre a frequência de deploy e o CFR (a).
\textit{Justificativa:} projetos que publicam com frequência tendem a ter automação madura, o que reduz as falhas que exigem uma release corretiva; ao mesmo tempo, projetos muito ativos executam mais \textit{workflows}, e mais variados, o que aumenta as falhas de \textit{pipeline} sem que a qualidade da entrega piore. Quem publica muitas releases também tem mais chance de ter duas releases a menos de 7 dias uma da outra, o que pode inflar o CFR (b) e gerar uma correlação positiva espúria. Correlação não implica causalidade.

\vspace{0.8em}
\noindent \textbf{Hipótese da RQ 06 (características dos repositórios).}
\textit{Quais características dos repositórios estão associadas a um melhor desempenho DORA?}
Espera-se que repositórios com mais contribuidores e mais estrelas apresentem maior frequência de deploy, porém com tempos de recuperação mais heterogêneos; que repositórios mais antigos apresentem menor CFR (a); que projetos em JavaScript/TypeScript e Python publiquem com mais frequência que projetos em linguagens voltadas a sistemas legados ou de compilação extensa; e que aplicações/serviços e ferramentas CLI publiquem com mais frequência que bibliotecas/frameworks.
\textit{Justificativa:} o tamanho da base colaborativa e o tipo de artefato moldam a governança do repositório. Mais contribuidores dão mais vazão de mudanças, mas uma equipe distribuída e com revisão mais lenta reage de forma desigual às falhas; projetos antigos tiveram mais tempo para estabilizar a integração contínua; ecossistemas com publicação simples em registros de pacotes facilitam releases frequentes; e bibliotecas exigem salvaguardas adicionais para não quebrar a API ou a compatibilidade binária de quem depende delas.

\vspace{0.8em}
\noindent \textbf{Hipótese da RQ 07 (análise de sensibilidade).}
\textit{O quanto a classificação DORA de um repositório depende da definição operacional escolhida?}
Comparando a combinação de referência C1 (release oficial, lead time pelo commit mais antigo e CFR por falhas de CI) com C2 (releases e pré-releases, lead time por commit e CFR por releases corretivas em até 7 dias) e C3 (deploy por \textit{git tags}), espera-se que a classificação geral seja \textbf{altamente sensível} à definição: entre 35\% e 60\% dos repositórios devem mudar de faixa, com kappa de Cohen ponderado linear entre 0,30 e 0,55 para C1 $\times$ C2 (concordância fraca a moderada) e entre 0,45 e 0,65 para C1 $\times$ C3 (moderada). Espera-se ainda que C2 produza classificações sistematicamente mais otimistas que C1, e que C3 eleve a frequência de deploy de projetos que versionam por tag sem publicar releases formais.
\textit{Justificativa:} sem telemetria de produção, cada \textit{proxy} mede um fenômeno diferente: falhas de CI medem o atrito dos testes no branch principal, enquanto releases corretivas captam só falhas de entrega graves o bastante para motivar uma nova versão; o lead time pelo commit mais antigo mede o ciclo de release, enquanto a mediana por commit mede a latência típica de cada mudança. A agregação em quatro faixas pela mediana amplifica oscilações perto dos cortes, o que torna a definição operacional uma ameaça direta à validade de construto.
```

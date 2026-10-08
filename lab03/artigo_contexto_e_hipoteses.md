# Texto para o Artigo SBC (Sprint 01)
**Autora:** Marcela Campos  
**Referência:** Issue #33 (Criar artigo SBC + contexto e hipóteses RQ01 e RQ06)

---

## 1. Introdução e Contextualização

### 1.1 Contexto Geral e Métricas DORA
A medição e melhoria contínua do desempenho de entrega de software consolidou-se como um dos pilares da engenharia de software moderna. Popularizadas pela iniciativa DORA (*DevOps Research and Assessment*) e formalizadas na obra *Accelerate* (Forsgren, Humble & Kim, 2018), quatro métricas fundamentais tornaram-se referências de mercado para avaliar a eficácia operacional de equipes de desenvolvimento:
1. **Deployment Frequency (Frequência de Deploy):** frequência com que alterações entram em produção (dimensão de velocidade/*throughput*);
2. **Lead Time for Changes (Tempo de Lead):** intervalo temporal transcorrido desde a concepção de um commit até a sua publicação em produção (dimensão de velocidade);
3. **Change Failure Rate (Taxa de Falha de Mudanças - CFR):** proporção de deploys que resultam em falhas com necessidade de correção ou intervenção emergencial (dimensão de estabilidade);
4. **Failed Deployment Recovery Time (Tempo de Recuperação):** tempo requerido para restaurar o serviço normal após uma interrupção ou falha (dimensão de estabilidade).

O paradigma DORA propõe que velocidade e estabilidade não constituem um *trade-off*, mas sim atributos sinérgicos em organizações de alto desempenho (*Elite performers*).

### 1.2 O Desafio dos Proxies em Ambientes Open-Source
Embora as definições do DORA tenham sido delineadas para o contexto corporativo e serviços sob implantação contínua (*Continuous Deployment*), este estudo investiga a mineração dessas métricas em **repositórios open-source reais hospedados no GitHub** com esteiras de CI/CD via GitHub Actions.

O GitHub **não registra formalmente "deploys em produção" nem "falhas em produção"**. Em projetos abertos, desenvolvedores publicam *releases*, acionam *workflows* de automação e realizam *commits*. Portanto, a inferência das quatro chaves depende necessariamente de aproximações operacionais (**proxies**):
- O evento de publicação de uma *release* oficial atua como **proxy de deploy**;
- A execução malsucedida de um workflow no branch principal atua como **proxy de falha**.

Reconhecendo que tais medidas indiretas podem suscitar distorções (por exemplo, bibliotecas distribuídas a terceiros versus microsserviços), o pipeline de medição incorpora critérios rigorosos de exclusão, protocolos de validação humana e análises de sensibilidade para estimar não apenas os valores pontuais, mas também o grau de confiança epistemológica dos resultados minerados.

### 1.3 Objetivo
O objetivo deste trabalho é extrair, caracterizar e analisar quantitativamente o perfil de desempenho DORA de repositórios open-source populares com automação ativa no GitHub Actions, respondendo a um conjunto de sete Questões de Pesquisa (RQs) estruturadas ao longo do ciclo empírico.

---

## 2. Hipóteses Informais Preliminares (Sprint 01)

As hipóteses a seguir foram formuladas a priori, **antes da inspeção empírica dos dados**, conforme o protocolo científico do estudo.

### Hipótese da RQ 01
- **Questão de Pesquisa 01:** *Qual a frequência de deploys dos repositórios populares que usam CI/CD?*
- **Definição Operacional:** Número de releases publicadas divididas por 52,1 semanas na janela de observação de 12 meses.
- **Hipótese Informal:** Espera-se que a grande maioria dos repositórios open-source populares se enquadre nas faixas **Medium** (entre 1 release por mês e 1 por semana) e **High** (entre 1 e 7 releases por semana), com mediana inferior a 0,5 releases/semana, e que a ocorrência de repositórios no nível **Elite** (≥ 7 releases por semana, ou seja, quase diária) seja extremamente rara.
- **Justificativa Teórica:** No ecossistema open-source, releases públicas implicam geração de artefatos estáveis, controle de versionamento semântico (SemVer) e testes de regressão mais extensos antes do lançamento público para a comunidade de usuários externos. Ao contrário de serviços web internos com integração e implantação contínuas totalmente automatizadas onde múltiplos deploys diários são habituais, o ciclo de empacotamento de bibliotecas e ferramentas públicas costuma ter cadência espaçada (quinzenal ou mensal).

---

### Hipótese da RQ 06
- **Questão de Pesquisa 06:** *Quais características dos repositórios estão associadas a um melhor desempenho DORA?*
- **Definição Operacional:** Comparação estatística não paramétrica (Kruskal-Wallis e Mann-Whitney com correção de Holm e tamanho de efeito Cliff's Delta / $\epsilon^2$) entre as métricas DORA e fatores do repositório: linguagem principal, número de contribuidores, popularidade (estrelas), idade do projeto e tipo de aplicação.
- **Hipótese Informal:**
  1. **Contribuidores e Popularidade:** Espera-se que repositórios com maior volume de contribuidores ativos e mais estrelas apresentem maior frequência de deploys (maior capacidade de vazão), porém com tempos de recuperação mais heterogêneos decorrentes da dispersão da equipe distribuída e processos de revisão mais lentos.
  2. **Idade do Repositório:** Repositórios mais antigos tenderão a apresentar processos de CI/CD mais consolidados, associando-se a menores taxas de falha em pipeline (CFR).
  3. **Linguagem:** Projetos em ecossistemas com ferramentas de automação e empacotamento altamente ágeis (como JavaScript/TypeScript e Python) devem apresentar maior frequência de releases do que projetos em linguagens voltadas a sistemas legados ou compilações extensas.
  4. **Tipo de Projeto:** Aplicações/serviços e ferramentas CLI devem apresentar maior cadência de entrega do que bibliotecas/frameworks, cujas mudanças exigem salvaguardas adicionais para evitar quebra de compatibilidade binária ou de API para dependentes.
- **Justificativa Teórica:** O tamanho da base colaborativa e o tipo de artefato gerado moldam a governança do repositório, impondo ritmos de entrega e esteiras de verificação com exigências distintas de estabilidade e rigor analítico.

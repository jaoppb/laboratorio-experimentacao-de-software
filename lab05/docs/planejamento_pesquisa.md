# Planejamento da pesquisa: Moodle

**Issue:** #163 · **Responsável:** Gabriel Assis de Souza · **Versão:** 1 (Lab05S01, a revisar nas S02 e S03)
**Software:** Moodle (ver `escolha_software.md`, entregue na #162)

> Os itens marcados como **[decisão do grupo]** são propostas do responsável pela issue e precisam ser validados pelo trio antes da coleta.

## 1. Caminho escolhido (enunciado, seção 2b)

| Caminho | Uso neste estudo |
|---|---|
| **Rodar o software no ambiente do grupo** (principal) | Subir o Moodle em contêineres Docker, com as mesmas configurações, nas duas versões LTS ainda mantidas: **4.5 LTS** e **5.3 LTS** |
| **Avaliar a qualidade do produto** (secundário) | Medir acessibilidade (WCAG, com axe) das mesmas telas nas duas versões, característica da ISO/IEC 25010 |

Não é o caminho "outro", então não há combinação extra a fazer com o professor. Não há teste de carga em sistema de terceiros, e nenhuma coleta usa repositório do GitHub como objeto. **[decisão do grupo]**

## 2. Pergunta de pesquisa

**PP:** Ao migrar o Moodle da versão 4.5 LTS para a 5.3 LTS, em ambiente controlado e com a mesma configuração, o tempo de resposta das páginas mais usadas por alunos muda? E a quantidade de violações de acessibilidade nessas páginas?

Perguntas derivadas:
- **PP1:** O tempo de resposta (TTFB) de login, painel, página de curso e tentativa de questionário difere entre as versões?
- **PP2:** A taxa de erros HTTP sob a mesma carga difere entre as versões?
- **PP3:** O número de violações do axe nas mesmas telas difere entre as versões?

## 3. GQM

**Objetivo (template de Basili):**
Analisar **o Moodle nas versões 4.5 LTS e 5.3 LTS**
com o propósito de **comparar**
com respeito a **desempenho (tempo de resposta e erros) e acessibilidade**
do ponto de vista de **quem administra e quem usa o Moodle (instituições e alunos)**
no contexto de **um ambiente controlado em Docker, com dados de curso sintéticos**.

| Pergunta | Métrica | Entidade e atributo | Escala | Medida |
|---|---|---|---|---|
| Q1: quanto tempo o servidor leva para responder cada página? | M1: TTFB por página (ms) | Produto, atributo externo | Razão | Direta |
| Q2: qual a variabilidade da resposta? | M2: percentis p50 e p95 do TTFB (ms) | Produto, atributo externo | Razão | Derivada |
| Q3: quantas requisições falham sob a mesma carga? | M3: taxa de erro HTTP 5xx e timeout (%) | Produto, atributo externo | Razão | Derivada |
| Q4: quantas barreiras de acessibilidade existem nas telas? | M4: violações do axe por tela, e por impacto (crítico, sério, moderado, leve) | Produto, atributo externo (ISO/IEC 25010, usabilidade) | Contagem (razão); o impacto é ordinal | Direta |

Cuidado de medição (Lei de Goodhart): o TTFB sozinho pode ser "jogado" por cache. Por isso a coleta registra o estado do cache (frio e quente) e o p95, e não só a média.

## 4. Hipóteses

- **H0₁:** a mediana do TTFB de cada página é igual na 4.5 LTS e na 5.3 LTS.
- **H1₁:** as medianas diferem (bicaudal).
- **H0₂:** a proporção de erros é igual nas duas versões.
- **H1₂:** a proporção de erros difere.
- **H0₃:** o número de violações do axe por tela é igual nas duas versões.
- **H1₃:** o número de violações difere.

Testes previstos (a confirmar na análise, S02): Mann-Whitney para M1 e M4 (tempos costumam ser assimétricos), teste de proporções para M3, e tamanho do efeito (delta de Cliff e razão das medianas). Reaproveita a escolha de teste e a discussão de erro tipo I e poder do Lab04.

## 5. Variáveis e design (resumo)

| Tipo | Variável |
|---|---|
| Independente (fator) | Versão do Moodle: 4.5 LTS e 5.3 LTS (2 níveis) |
| Dependentes | M1 a M4 |
| Controladas | Mesma versão de PHP aceita pelas duas (confirmar nos requisitos oficiais), mesmo banco e versão, mesma imagem base, mesmos limites de CPU e memória, mesmo curso e usuários sintéticos, mesma máquina |
| Possíveis confundidoras | Cache (frio e quente), ruído da máquina do grupo, ordem de execução |

Design: comparação entre dois tratamentos, com repetições e ordem alternada das execuções. Objetos: as 4 páginas mais usadas por alunos. A instrumentação é do papel B (#164) e roda só no ambiente do próprio grupo. Sem dados pessoais.

## 6. As 7 categorias da pesquisa (primeira versão)

| Categoria | Classificação | Justificativa |
|---|---|---|
| **Natureza** | Pesquisa aplicada | Resolve um problema prático: decidir se vale migrar de versão |
| **Objetivos** | Explicativa (comparativa) | Busca verificar se a versão causa diferença nas métricas, e não só descrever o desempenho |
| **Abordagem** | Quantitativa | Todas as métricas (TTFB, erro, violações) são numéricas e analisadas com estatística |
| **Procedimentos** | Experimento (de laboratório) | Há um fator manipulado (a versão) e medição em ambiente construído pelo grupo, não observação do sistema em produção |
| **Tempo** | Transversal | As medições são feitas em um período curto, sem acompanhar a evolução ao longo do tempo |
| **Controle** | Experimento controlado | Configuração, dados e hardware são fixados e só a versão varia. Não há participantes humanos, então o controle vem do ambiente |
| **Nível de evidência** | Moderado | Boa validade interna, mas validade externa limitada: um servidor do grupo com dados sintéticos não representa instalações reais |

Esta tabela deve ser revista nas S02 e S03 conforme o que de fato for executado.

## 7. Ameaças à validade (primeira versão, a detalhar na S02)

| Tipo | Ameaça | Mitigação prevista |
|---|---|---|
| Conclusão | Poucas repetições; dados assimétricos | Muitas repetições por tela; testes não paramétricos; tamanho do efeito |
| Interna | Ruído da máquina; efeito de cache; PHP diferente entre as versões | Ordem alternada; cache frio e quente separados; mesmo PHP quando possível |
| Construto | O TTFB não representa a experiência real do usuário | Limitar a conclusão ao tempo de servidor; registrar métricas do navegador se viável |
| Externa | Ambiente único, dados sintéticos, sem plugins nem integrações | Declarar o limite e não extrapolar para instalações reais |

## 8. Pendências

- [ ] O trio valida o caminho e a pergunta de pesquisa (itens **[decisão do grupo]**).
- [ ] Conferir os requisitos de PHP e banco de dados do Moodle 4.5 e do 5.3 para fixar o ambiente.
- [ ] Conferir a coerência com o plano de coleta (#164) e o plano de análise (#165).

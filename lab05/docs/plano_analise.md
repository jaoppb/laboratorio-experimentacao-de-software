# Plano de Análise Estatística e Estimativa de Impacto: Moodle

**Issue:** #165 · **Papel:** C (Análise e Impacto) · **Responsável:** Marcela Campos  
**Versão:** 1.0 (Lab05S01) · **Data:** 19/11/2026  
**Software:** Moodle 4.5 LTS × Moodle 5.3 LTS  
**Documentos de referência:** `planejamento_pesquisa.md` (#163) e `plano_coleta_instrumentacao.md` (#164)

---

## 1. Métricas do GQM, Escalas de Medição e Operações Estatísticas

Com base na teoria de escalas de Stevens (1946) ensinada na disciplina teórica de Medição e Experimentação de Software, cada métrica definida no GQM do estudo possui uma escala associada que determina com rigor matemático quais operações e estatísticas são válidas e proibidas.

| Métrica GQM | Descrição e Unidade | Escala | Estatísticas Permitidas | Estatísticas Proibidas |
|---|---|---|---|---|
| **M1: TTFB** | Tempo até o primeiro byte retornado pelo servidor (ms) | **Razão** (zero absoluto físico) | Mediana, IQR, média, desvio-padrão, variância, percentis (p50, p95), razão entre valores. | Nenhuma limitação de escala (mas média é desaconselhada sob assimetria severa). |
| **M2: Percentis de TTFB** | Percentis p50 e p95 calculados por tela (ms) | **Razão** | Comparação pontual, percentual de mudança relativa ($\Delta\%$), razão. | Somar percentis de páginas heterogêneas sem ponderação. |
| **M3: Taxa de Erro HTTP** | Percentual de requisições com status 5xx ou timeout (%) | **Razão** (proporção com zero absoluto) | Proporções, risco relativo, razão de chances (*odds ratio*), teste de proporções. | Média de proporções com denominadores de tamanhos distintos sem ponderação. |
| **M4a: Quantidade de Violações** | Total de barreiras de acessibilidade (axe-core) por tela | **Razão** (contagem discreta, zero = nenhuma violação) | Contagem, mediana por tela, soma total, razão. | — |
| **M4b: Severidade da Violação** | Impacto da barreira (*minor*, *moderate*, *serious*, *critical*) | **Ordinal** (ordem natural de gravidade, sem distância fixa entre níveis) | Frequências absolutas e relativas, moda, mediana ordinal, postos. | **Média aritmética e desvio-padrão de severidade** (atribuir valores 1, 2, 3, 4 e calcular média é matematicamente inválido). |

---

## 2. Escolha da Estatística Descritiva

Para cada tipo de dado coletado, adota-se a estatística descritiva mais adequada:

1. **Tempo de Resposta do Servidor (M1 e M2):**
   - **Medida de Tendência Central Primária:** **Mediana** (em vez da média). Conforme evidenciado experimentalmente no Lab04, tempos de resposta em sistemas de software apresentam forte assimetria à direita e caudas pesadas decorrentes de requisições atípicas (operações de I/O em disco, compilação de templates, garbage collection).
   - **Medida de Dispersão Primária:** **IQR** (Intervalo Interquartil: $Q_3 - Q_1$), resistente a outliers de cauda.
   - **Medidas Complementares:** Média aritmética, desvio-padrão e percentis $p50$ e $p95$ (para observar o comportamento na cauda de pior caso do usuário).
2. **Taxa de Erros HTTP (M3):**
   - Proporção observada de erros ($p = \frac{k}{N}$) acompanhada de seu **Intervalo de Confiança de 95% pelo método de Wilson** (adequado para proporções binomiais pequenas e amostras finitas).
3. **Barreiras de Acessibilidade (M4):**
   - Contagem total de regras violadas por tela e versão.
   - Distribuição de frequências percentuais em tabela de contingência cruzando versão × nível de severidade ordinal (*critical*, *serious*, *moderate*, *minor*).

---

## 3. Escolha dos Testes de Hipótese Adequados

### 3.1. TTFB por Página (M1): Teste $U$ de Mann-Whitney (Bicaudal, $\alpha = 0,05$)

- **Hipótese:** $H_{0,1}: P(TTFB_{5.3} > TTFB_{4.5}) = 0,5$ versus $H_{1,1}: P(TTFB_{5.3} > TTFB_{4.5}) \neq 0,5$.
- **Embasamento com os achados do Lab04:**
  No Lab04, realizamos 10.000 simulações de Monte Carlo comparando o teste paramétrico $t$ de Welch com o não-paramétrico de Mann-Whitney sob dados de software assimétricos com caudas pesadas (lognormais):
  1. **Controle de Erro Tipo I:** O Mann-Whitney manteve a taxa de rejeição de $H_0$ rigorosamente em torno de 5% (4,3% a 4,8%) em todos os cenários (inclusive com outliers e assimetria extrema). Em contrapartida, o teste $t$ de Welch mostrou-se ultraconservador (taxa de erro tipo I caiu para 0,85% sob assimetria severa), porque valores extremos inflam o erro-padrão da média.
  2. **Poder Estatístico Superior:** O Mann-Whitney superou o teste de Welch em poder em todas as condições avaliadas. Como o TTFB é baseado em postos, valores atípicos não distorcem a estatística de teste.
  3. Portanto, para comparar os tempos de resposta do Moodle entre as versões, o **Mann-Whitney é a recomendação técnica definitiva**.

### 3.2. Taxa de Erro HTTP (M3): Teste de Duas Proporções / Teste Exato de Fisher

- Compara a proporção de falhas $p_{4.5}$ e $p_{5.3}$.
- Se a contagem esperada em qualquer célula for $< 5$ (o que é provável em ambiente local com baixa taxa de erro), utiliza-se o **Teste Exato de Fisher**; caso contrário, o teste assintótico Z de duas proporções.

### 3.3. Barreiras de Acessibilidade (M4): Teste de Postos Sinalizados de Wilcoxon

- Como as mesmas 4 telas (Login, Dashboard, Curso, Questionário) são inspecionadas em ambas as versões, temos uma estrutura de **amostras pareadas** (Login 4.5 pareado com Login 5.3, etc.). O teste de postos sinalizados de Wilcoxon (ou análise descritiva direta se a quantidade de telas for pequena) avalia a redução ou aumento pareado de falhas.

---

## 4. Medidas de Tamanho do Efeito

O p-valor avalia apenas se a diferença observada é estatisticamente distinguível do acaso, mas não indica a sua magnitude prática. Para tanto, definem-se as métricas formais de tamanho do efeito:

### 4.1. Delta de Cliff ($\Delta$ de Cliff)

Para o teste não-paramétrico de Mann-Whitney em dados contínuos/ordinais, a medida padronizada recomendada na literatura de Engenharia de Software é o **Delta de Cliff ($d \in [-1, 1]$)**:

$$d = \frac{\# (x_{5.3} > x_{4.5}) - \# (x_{5.3} < x_{4.5})}{n_{5.3} \cdot n_{4.5}}$$

- **Interpretação (limiares de Romano et al., 2006):**
  - $|d| < 0,147$: Efeito **Desprezível**
  - $0,147 \le |d| < 0,33$: Efeito **Pequeno**
  - $0,33 \le |d| < 0,474$: Efeito **Médio**
  - $|d| \ge 0,474$: Efeito **Grande**

### 4.2. Razão entre as Medianas e Variação Percentual

Como complemento prático compreensível para gestores de TI e engenheiros:
$$\text{Razão} = \frac{\text{Mediana}_{5.3}}{\text{Mediana}_{4.5}}, \quad \Delta\% = \left(\frac{\text{Mediana}_{5.3} - \text{Mediana}_{4.5}}{\text{Mediana}_{4.5}}\right) \times 100$$
- Uma razão de $0,85$ indica que a versão 5.3 respondeu em 85% do tempo da 4.5 (ou seja, 15% mais rápida).

---

## 5. Estimativa de Tamanho de Amostra Necessário

Reaproveitando os resultados das curvas de poder estatístico simuladas no **Lab04 (Gráfico G4)**:

1. **Curvas de Poder de Referência:**
   - No experimento de simulação do Lab04, com uma amostra de $N = 30$ observações por grupo, o Mann-Whitney obteve um poder estatístico de aproximadamente $72\%$ para detectar uma razão de medianas de $2,0$, atingindo $> 98\%$ para razões $\ge 3,0$.
2. **Dimensionamento para o Moodle:**
   - No Moodle em contêineres locais, esperamos diferenças mais sutis entre versões de software maduras (na faixa de $15\%$ a $25\%$ de melhoria ou regressão no TTFB, correspondente a um tamanho de efeito médio, $d \approx 0,35$).
   - Para detectar um efeito médio com **poder estatístico de 80% ($\beta = 0,20$)** ao nível de significância de **$\alpha = 0,05$**, a literatura (Cohen, 1988; Lehmann, 2006) prescreve:
     $$N_{\text{por grupo e por tela}} \ge 60 \text{ a } 80 \text{ requisições válidas}$$
3. **Plano de Execução:**
   - **Piloto (Lab05S01):** $N = 10$ requisições por tela por versão (total de 80 requisições) para validar estabilidade da variância e ausência de travamentos.
   - **Coleta Final (Lab05S02):** $N = 80$ requisições válidas por tela por versão ($80 \times 4 \text{ telas} \times 2 \text{ versões} = 640 \text{ requisições no total}$). Esse volume leva aproximadamente 3 a 5 minutos para rodar localmente e confere alta solidez estatística.
4. **Verificação com o piloto (#167):** a análise do piloto (`analise_piloto.md` §6) usou só as repetições `warm` (n = 9 por grupo) e não contradiz o N = 80, que fica mantido como piso. O n necessário estimado (20 a 40) vem de um efeito observado com IC largo e não substitui a premissa de $d \approx 0,35$ deste plano.

---

## 6. Números Públicos e Modelo de Estimativa de Impacto no Mundo Real

A seção 5 do enunciado do Lab05 exige traduzir o resultado empírico em impacto mensurável para empresas e usuários no mundo real, utilizando dados públicos com fonte.

### 6.1. Dados Públicos Coletados (com Links e Datas de Acesso)

| Indicador Público | Valor Registrado | Fonte Oficial | Data de Acesso |
|---|---|---|---|
| **Usuários Registrados no Moodle** | **513.581.641 usuários** | https://stats.moodle.org | 19/11/2026 |
| **Sites Registrados Ativos** | **147.888 sites** em 237 países | https://stats.moodle.org | 19/11/2026 |
| **Cursos Hospedados** | **59.374.088 cursos** | https://stats.moodle.org | 19/11/2026 |
| **Estudo de Caso de Adoção Nacional** | 100% dos programas acadêmicos da universidade | Nepal Open University Case Study (Moodle HQ) | 19/11/2026 |

### 6.2. Modelo de Projeção de Impacto (Fórmula e Cenários)

A partir da diferença de tempo de resposta ($\Delta \text{TTFB} = \text{Mediana}_{4.5} - \text{Mediana}_{5.3}$, em milissegundos), projeta-se o impacto acumulado em dois níveis:

#### A. Nível de uma Universidade Típica (Ex.: 30.000 alunos ativos)
Adotando parâmetros operacionais conservadores da literatura de sistemas acadêmicos (média de 20 requisições a páginas principais por aluno por dia em período letivo):

$$\text{Tempo economizado/dia (horas)} = \frac{(\Delta \text{TTFB}_{\text{médio}} \text{ ms}) \times 20 \text{ reqs/aluno} \times 30.000 \text{ alunos}}{3.600.000 \text{ ms/hora}}$$

- **Simulação de Cenário:** Se o Moodle 5.3 economizar **50 ms** por requisição:
  $$\text{Tempo economizado} = \frac{50 \times 20 \times 30.000}{3.600.000} = \mathbf{8,33 \text{ horas de espera acumulada dos alunos economizadas por dia}}.$$
  Ao longo de um semestre letivo (100 dias úteis), isso representa **mais de 830 horas** a menos de espera ociosa e redução equivalente de tempo de ocupação de threads de CPU no servidor PHP-FPM.

#### B. Nível Global do Ecossistema Moodle
Considerando apenas $2\%$ dos 513 milhões de usuários ativos em um dado dia (cerca de 10 milhões de usuários diários no mundo):
- A mesma economia de 50 ms resultaria em **mais de 2.700 horas de CPU e espera poupadas diariamente em servidores globais**.

### 6.3. Limitações da Estimativa e Ameaças à Validade Externa

Em respeito ao método científico e à validade externa:
- O estudo em contêiner local isolado não incorpora a latência de trânsito de rede de provedores de internet (ISP) dos alunos.
- Ambientes de produção reais contam com dezenas de plugins de terceiros e temas customizados que podem mascarar ganhos do core do Moodle.
- Portanto, o impacto é declarado expressamente como **potencial de ganho do núcleo da aplicação sob condições controladas**, e não como garantia de aceleração para qualquer infraestrutura arbitrária.

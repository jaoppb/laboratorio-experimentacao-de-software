# Plano de Coleta e Instrumentação: Moodle 4.5 LTS × 5.3 LTS

**Issue:** #164 · **Papel:** B (Instrumentação e Operação) · **Responsável:** Marcela Campos  
**Versão:** 1.1 (Lab05S01, revisada após o piloto #166) · **Data:** 19/11/2026  
**Software:** Moodle (LMS open source em operação em produção)  
**Documentos de referência:** `escolha_software.md` (#162) e `planejamento_pesquisa.md` (#163)

---

## 1. Visão Geral e Objetivos da Coleta

O objetivo deste plano é estabelecer a infraestrutura, o protocolo de medição e a instrumentação necessários para responder à pergunta de pesquisa do estudo: verificar empiricamente se a migração do **Moodle 4.5 LTS** para o **Moodle 5.3 LTS** altera o tempo de resposta do servidor (TTFB), a taxa de erros HTTP e as barreiras de acessibilidade (WCAG) nas telas mais utilizadas por alunos.

As medições cobrem:
1. **Desempenho HTTP (TTFB e tempo total)** via requisições controladas e instrumentadas.
2. **Qualidade e Acessibilidade (ISO/IEC 25010 / WCAG 2.1 AA)** via auditoria estática e dinâmica com o motor `axe-core`.

---

## 2. Ambiente de Execução e Configurações

Para isolar o efeito da versão do software (fator independente de 2 níveis: 4.5 LTS e 5.3 LTS) e garantir controle experimental rigoroso, ambas as versões rodam em contêineres Docker independentes com a **mesma configuração de infraestrutura**:

### 2.1. Matriz de Compatibilidade e Componentes

| Componente | Versão Fixada | Justificativa de Controle |
|---|---|---|
| **Linguagem / Runtime** | PHP 8.3 (Apache `mod_php`, imagem `moodlehq/moodle-php-apache:8.3`) | Menor versão aceita pelo Moodle 5.3 (exige PHP >= 8.3) e também suportada pelo 4.5. Ver §7, problema P2. |
| **Banco de Dados** | MariaDB 11.4 LTS | Menor versão aceita pelo Moodle 5.3 (exige MariaDB >= 11.4) e também suportada pelo 4.5. Ver §7, problema P3. |
| **Servidor Web** | Apache 2.4 da imagem `moodlehq/moodle-php-apache` | Substitui o Nginx previsto na versão 1.0 do plano. Ver §7, problema P4. |
| **Moodle 4.5 LTS** | 4.5.16 (tag `v4.5.16`) | Versão LTS anterior mantida pela Moodle HQ. |
| **Moodle 5.3 LTS** | 5.3.1 (tag `v5.3.1`) | Versão LTS atual mais recente. |

### 2.2. Parâmetros de Recursos e Otimização do PHP

Ambos os contêineres recebem exatamente os mesmos limites operacionais em `docker/docker-compose.yml` (limites e imagens) e `docker/php-moodle.ini` (PHP e OPcache):
- **Limites de Contêiner:** `cpus: "2.0"` e `mem_limit: "2048m"` (2 GB de RAM dedicados por instância), valendo também para os bancos de dados. As imagens são fixadas por digest.
- **PHP OPcache:** Ativado em ambos com os mesmos parâmetros (`opcache.enable=1`, `opcache.memory_consumption=128`, `opcache.max_accelerated_files=10000`, `opcache.revalidate_freq=0`).
- **PHP Configurações:** `memory_limit = 512M`, `max_execution_time = 60`, `post_max_size = 64M`, `upload_max_filesize = 64M`, `max_input_vars = 5000`.

### 2.3. Especificações da Máquina Host (Registro para Reprodutibilidade)

As medições são executadas na máquina local do grupo, com registro dos parâmetros de hardware para documentação de ameaças à validade interna:
- **Processador:** CPU multinúcleo (mínimo 4 núcleos físicos). Piloto: Apple M2 (arm64), 8 núcleos.
- **Memória RAM:** 16 GB. Piloto: 16 GB (VM do OrbStack com 7,8 GiB).
- **Sistema Operacional:** Windows 11 / Linux / macOS com Docker Engine >= 26.0. Piloto: macOS 26.6 com OrbStack e Docker 29.8.
- **Isolamento de Ruído:** Durante as rodadas de medição, nenhum outro processo pesado de usuário (IDE pesada, navegadores concorrentes, indexadores) deve estar ativo.

---

## 3. Roteiro de Coleta e Instrumentação

### 3.1. Telas Avaliadas (Objetos de Medição)

Seguindo o GQM definido na Issue #163, foram selecionadas as 4 telas de maior tráfego e impacto para alunos:
1. **Login (`/login/index.php`):** Requisição pública, representativa de autenticação e carga inicial.
2. **Painel do Aluno (`/my/`):** Tela autenticada, com agregação de cursos, prazos, linha do tempo e múltiplos blocos dinâmicos.
3. **Página de Curso Sintético (`/course/view.php?id=2`):** Tela com módulos de aprendizado, seções de tópicos, links e mídias.
4. **Página do Questionário / Quiz (`/mod/quiz/view.php?id=6`):** Página de entrada do quiz, crítica para o aluno em períodos de prova. A tela de *tentativa* do quiz (com questões) não é medida no piloto (ver §7, problema P6, pendente para a S02).

### 3.2. Cursos e Usuários Sintéticos

- Não são utilizados dados de instituições reais nem contas de alunos reais.
- Os dados do ambiente são povoados por meio da ferramenta padrão do Moodle para testes de benchmark e QA (`admin/tool/generator/cli/maketestcourse.php --size=XS`), criando o curso sintético `lab05`. O estudante `aluno_teste_1` (matriculado no curso) e o quiz são criados por `docker/semear_dados.php` (ver §7, problema P6).
- As duas instâncias são instaladas do zero pelos mesmos scripts (`docker/instalar_moodle.sh`) e ficam com os mesmos identificadores (curso `id=2`, quiz `cmid=6`; `instalar_moodle.sh` imprime `curso_id` e `quiz_cmid` para conferência).

### 3.3. Instrumentação de Desempenho (TTFB e Tempo Total)

A coleta de desempenho é realizada por script automatizado em Python (`scripts/coleta_piloto.py` e posterior runner completo da S02), utilizando a biblioteca `httpx` com conexão TCP/HTTP direta:
- **Métricas extraídas a cada requisição:**
  - `status_http`: código HTTP retornado (esperado: 200).
  - `ttfb_ms`: *Time To First Byte* em milissegundos (tempo transcorrido desde o envio da requisição HTTP até o recebimento dos cabeçalhos de resposta).
  - `tempo_total_ms`: tempo total até o fim do corpo da resposta.
  - `tamanho_bytes`: tamanho do corpo (já descompactado) em bytes.
  - `cache`: `cold` (1ª repetição de cada tela e versão, após `purge_caches.php`) ou `warm` (repetições 2 a 10).
  - Esquema completo do CSV: `id, versao, tela, rota, repeticao, cache, status_http, ttfb_ms, tempo_total_ms, tamanho_bytes`. Os nomes em português substituem os nomes em inglês da versão 1.0 do plano.
- **Sessão:** a tela `login` é medida sem cookie (visitante). As demais usam o estudante `aluno_teste_1` autenticado.
- **Mitigação de Confundimento Térmico / Ordem:** As coletas alternam as versões a cada requisição (4.5, 5.3, 4.5, 5.3, ...), de modo que o aquecimento de CPU ou do cache do SO afete as duas de forma parecida. A ordem é fixa (4.5 sempre primeiro em cada par): ver §7, problema P13.

### 3.4. Instrumentação de Acessibilidade (WCAG 2.1 / axe-core)

A avaliação da característica de usabilidade e acessibilidade (ISO/IEC 25010) é automatizada utilizando o motor padrão de mercado `axe-core`:
- Cada uma das 4 telas nas duas versões é renderizada em navegador headless (Playwright com Chromium headless e `axe-playwright-python`, em `scripts/auditoria_axe.py`).
- O script executa o `axe.run()` com as tags WCAG 2.0/2.1 A e AA e grava um JSON por tela e versão em `dados/piloto/axe/<versao>_<tela>.json`, com:
  - Total de violações por tela.
  - Classificação por severidade: *crítico* (`critical`), *sério* (`serious`), *moderado* (`moderate`) e *leve* (`minor`), mais `indefinido` quando o axe não informa o impacto.
  - IDs das regras WCAG violadas (ex.: contraste de cores, labels de formulários, estrutura semântica de headings).

---

## 4. Frequência e Volume de Amostras

### 4.1. Coleta Piloto (Sprint Lab05S01)
- **Objetivo do Piloto:** Validar conectividade, scripts de instrumentação, extração correta de cookies de autenticação e ausência de falhas técnicas.
- **Volume do Piloto:** 10 repetições por tela em cada versão ($10 \times 4 \text{ telas} \times 2 \text{ versões} = 80 \text{ requisições}$).
- **Avaliação de Acessibilidade Piloto:** 1 auditoria do axe-core nas 4 telas para ambas as versões.

### 4.2. Coleta Definitiva (Sprint Lab05S02)
- **Volume Planejado:** Com base na estimativa de poder estatístico descrita no Plano de Análise (#165), serão coletadas **80 repetições válidas por tela em cada versão** ($80 \times 4 \times 2 = 640 \text{ requisições de desempenho}$), garantindo poder estatístico $> 85\%$ para detectar diferenças de tamanho médio a grande com $\alpha = 0,05$.
- **Intervalo entre requisições:** 200 a 500 ms de pausa aleatória entre requisições para evitar enfileiramento artificial no servidor web local. O piloto já aplica essa pausa.

---

## 5. Regras de Ética e Conformidade

Seguindo estritamente a seção 2b e as regras éticas do enunciado do Lab05:

1. **Sem Teste de Carga ou Estresse em Sistemas de Terceiros:**
   - Todo o tráfego gerado é confinado exclusivamente ao ambiente local (`localhost` / Docker network).
   - Nenhuma requisição de teste é direcionada a servidores públicos da Moodle HQ, da comunidade moodle.org ou de universidades parceiras.
2. **Respeito a Termos de Uso e Taxa Máxima de Acesso Externo:**
   - Eventuais consultas de metadados, documentação ou notas de versão em sites oficiais são pontuais e manuais ou limitadas a no máximo **1 requisição por segundo**, respeitando integralmente o `robots.txt`.
3. **Nenhum Dado Pessoal (LGPD e Privacidade):**
   - O estudo não utiliza, não extrai e não armazena nomes reais, e-mails, senhas reais ou identificadores de usuários de terceiros. Todos os perfis são usuários sintéticos gerados por scripts do grupo (`aluno_teste_1`).
4. **Ausência de Participantes Humanos na S01:**
   - Por ser um experimento controlado de infraestrutura e produto de software (software rodando no ambiente do grupo), não há sujeitos humanos interagindo no estudo nesta fase, dispensando aplicação de Termo de Consentimento Livre e Esclarecido (TCLE).

---

## 6. Estrutura do Repositório e Quadro no GitHub Projects

### 6.1. Organização dos Arquivos no Monorepo

O estudo do Lab05 reside na pasta `lab05/` do repositório principal:

```text
lab05/
├── docs/
│   ├── escolha_software.md              # [Gabriel, #162] Evidências dos 3 critérios
│   ├── planejamento_pesquisa.md         # [Gabriel, #163] GQM, hipóteses, 7 categorias
│   ├── plano_coleta_instrumentacao.md   # [Marcela, #164/#166] Ambiente, roteiro, ética e piloto
│   ├── plano_analise.md                 # [Marcela, #165] Métricas, testes, poder e impacto
│   ├── analise_piloto.md                # [Marcela, #167] Pipeline e suficiência da amostra
│   └── relatorio_s01.md                 # [Marcela, #167] Índice e estado das entregas da S01
├── scripts/
│   ├── coleta_piloto.py                 # [Marcela, #164/#166] Medição HTTP/TTFB (real e --simulado)
│   ├── auditoria_axe.py                 # [#166] Auditoria axe-core
│   ├── validar_piloto.py                # [#166] Validador dos dados do piloto
│   └── analisar_piloto.py               # [#167] Análise do piloto
├── docker/                              # [#166] Compose, instalação e dados sintéticos do Moodle
├── tests/                               # [#166/#167] Testes dos scripts
├── pyproject.toml                       # [#166] Dependências dos scripts
├── dados/
│   ├── piloto/                          # Dados reais do piloto (CSV, JSON e axe/)
│   └── reais/                           # Dados consolidados da coleta (Sprint S02, a criar)
├── enunciado.md                         # Enunciado oficial da disciplina
└── README.md                            # Guia central do Lab05 e instruções de reprodução
```

### 6.2. Acompanhamento no GitHub Projects

- **Quadro:** [Laboratório de Experimentação de Software - Projects View 1](https://github.com/users/jaoppb/projects/3/views/1)
- **Rastreabilidade:** Todos os commits contêm no início da mensagem a referência explícita à Issue correspondente (ex.: `#164`, `#165`).
- **Issues da Sprint 1:**
  - `#162` Escolha do software e evidências dos 3 critérios (Responsável: Gabriel) — Concluído.
  - `#163` Pergunta de pesquisa, GQM, hipóteses e 7 categorias (Responsável: Gabriel) — Concluído.
  - `#164` Plano de coleta e instrumentação e regras de ética (Responsável: Marcela) — Concluído.
  - `#165` Plano de análise, testes, poder e estimativa de impacto (Responsável: Marcela) — Concluído.
  - `#166` Coleta piloto (B) (Responsável: Marcela) — Concluído (§7).
  - `#167` Análise do piloto e consolidação da entrega da S01 (C) — Concluído ([analise_piloto.md](analise_piloto.md) e [relatorio_s01.md](relatorio_s01.md)).

---

## 7. Resultado do Piloto (#166) e Ajustes ao Plano

### 7.1. O que foi executado

- Duas instâncias reais (Moodle 4.5.16 e 5.3.1) em Docker, instaladas por CLI do zero, com o mesmo curso sintético, o mesmo estudante e as mesmas configurações de PHP e de limites (2 CPUs e 2 GB por instância).
- 80 requisições de desempenho (10 repetições × 4 telas × 2 versões), em ordem alternada, com pausa aleatória de 200 a 500 ms e purga de cache antes da coleta. Dados em `dados/piloto/amostra_piloto.csv` e `resumo_piloto.json`. O piloto teve duas execuções completas na mesma máquina (a 1ª serviu de ensaio, e a 2ª é a versionada), além de uma tentativa abortada (P12).
- 8 auditorias axe-core (4 telas × 2 versões) com as tags WCAG 2.0/2.1 A e AA, em `dados/piloto/axe/`.
- Validação com `scripts/validar_piloto.py`: esquema do CSV, 80 linhas, 10 amostras por tela e versão, `status_http = 200`, TTFB positivo e não maior que o tempo total, uma rota por tela, cache frio só na repetição 1, ordem alternada e resumo JSON igual ao recálculo a partir do CSV. Também confere `meta.origem = real`, que o release de cada versão está registrado e os 8 relatórios axe. Resultado: sem problemas. Os testes (`tests/`, `pytest`) rodam o validador sobre os dados versionados.

Os dados que o #164 havia versionado eram sintéticos (distribuições lognormais geradas por `coleta_piloto.py`) e foram substituídos por esta coleta. O gerador continua disponível com `--simulado`, grava em `dados/piloto_simulado/` e não escreve em `dados/piloto/`.

### 7.2. Problemas encontrados e ajustes

| # | Problema | Ajuste |
|---|---|---|
| P1 | O piloto do #164 não media nenhum Moodle: os valores eram gerados por um sorteio lognormal. Plano e README descreviam `httpx`, Docker e axe-core que não existiam no repositório. | Piloto refeito em Moodle real. Runner HTTP, `docker/`, auditoria axe e validador criados. Gerador sintético isolado em `--simulado`. |
| P2 | O Moodle 5.3 exige PHP >= 8.3 (o plano previa PHP 8.2). A instalação do 5.3 abortou com PHP 8.2.35. | As duas versões rodam em PHP 8.3 (o 4.5 suporta 8.3), para manter a mesma infraestrutura nos dois tratamentos. |
| P3 | O Moodle 5.3 exige MariaDB >= 11.4 (o plano previa 10.11). | As duas versões usam MariaDB 11.4. |
| P4 | Não há imagem pronta do Moodle 4.5/5.x utilizável (`bitnami/moodle:4.5` e `5.0` não existem no registry). A imagem `moodlehq/moodle-php-apache` traz só PHP e Apache. | O código vem das tags oficiais (`docker/preparar_codigo.sh`, em `docker/codigo/`, fora do git), com `composer install --no-dev` em contêiner. O servidor web passa a ser o Apache da imagem (o plano previa Nginx). O 5.x serve a partir de `public/` (`APACHE_DOCUMENT_ROOT`) e move os scripts de `admin/tool/.../cli` para `public/`. As imagens ficam fixadas por digest. |
| P5 | O contêiner do Moodle subiu sem rede quando a porta já estava ocupada por outro projeto Compose, e a instalação falhou com "could not connect to the database". | O projeto Compose tem nome fixo (`lab05`). Em caso de conflito de porta, `docker compose down` e `up -d --force-recreate`. |
| P6 | `maketestcourse.php` não cria quiz, e a API de banco de questões difere entre 4.5 e 5.x. Também falhou com MariaDB 11.4 em modo estrito (`password` nulo) ao criar o quiz. | `docker/semear_dados.php` cria o quiz pela API de módulos (`quizpassword = ''`), **sem questões**. A tela medida (`/mod/quiz/view.php`) não depende delas. **Pendência para a S02:** a tela de tentativa de quiz (5 questões) não foi medida (follow-up #172). |
| P7 | Com o cookie do estudante, `/login/index.php` não é a tela pública de login. | A tela `login` é medida por cliente HTTP sem sessão. |
| P8 | A ordem entre login e purga de cache altera o que a 1ª repetição mede: com a purga antes do login, o próprio login (sessão, caches de usuário) aquece caches da 1ª repetição. | Ordem fixada: autenticar, purgar caches, medir. A 1ª repetição de cada tela é `cold`. |
| P9 | O Moodle não expõe a versão na página de login (sem `<meta generator>`). | O `release` é lido de `version.php` dentro do contêiner e gravado em `resumo_piloto.json` (`meta.releases_moodle`). |
| P10 | Os nomes de colunas do plano (`status_code`, `total_time_ms`, ...) divergiam do CSV. | O plano (§3.3) adota os nomes do CSV, que o `validar_piloto.py` e a análise do #167 consomem. |
| P11 | Só a repetição 1 é fria (n = 1 por tela e versão). Nas telas autenticadas a 1ª requisição ficou entre 1,1 e 2,2 vezes a mediana (maior caso: dashboard 4.5, 195 ms contra 90 ms). Na tela pública `login` ela levou 458 ms (4.5) e 505 ms (5.3), contra medianas de 43 e 45 ms. Média e p95 do resumo misturam frio e quente. | **Decidido no #167:** a análise principal usa só `warm` (n = 9 por grupo), e `cold` é só descrito (n = 1, sem teste). Para a S02, coletar `cold` à parte, com várias repetições e purga entre elas, em vez de uma por grupo. |
| P12 | Em uma tentativa intermediária, o login do estudante foi recusado ("Invalid login") três vezes seguidas, com a mesma senha que funcionou antes e depois (o contador `login_failed_count_since_success` ficou em 3). Não foi reproduzido nem explicado. | Os scripts abortam com mensagem clara (`Falha de autenticação`) sem gravar dados parciais (`auditoria_axe.py` só grava os relatórios depois de auditar as 8 combinações), e a execução foi repetida com sucesso. Se voltar na S02, investigar antes de aumentar o volume. |
| P13 | A ordem é fixa: 4.5 sempre precede 5.3 dentro de cada par. A "ordem alternada balanceada" do plano 1.0 não se cumpre (a versão 5.3 sempre é medida logo após a 4.5). | **Decidido no #167:** o piloto não é alterado, e a ordem fixa entra como ameaça à validade interna (o sentido da diferença não é interpretado). Para a S02, contrabalancear a ordem (ABBA ou sorteio por par), e refazer o piloto no follow-up #171. |

### 7.3. Resultados descritivos do piloto (TTFB, ms, n = 10 por célula)

| Tela | 4.5: mediana (IQR) | 5.3: mediana (IQR) |
|---|---|---|
| login | 42,85 (11,18) | 45,30 (5,93) |
| dashboard | 90,09 (11,45) | 92,34 (6,25) |
| curso | 88,97 (14,00) | 95,31 (5,74) |
| questionario | 82,89 (14,63) | 90,81 (7,85) |

Todas as 80 requisições retornaram 200. O axe-core não reportou violações em nenhuma das 8 combinações (22 a 28 regras aprovadas por tela; as regras "incompletas", que exigem revisão manual, são 0 ou 1 por tela e ficam registradas nos relatórios). O motor foi verificado manualmente com uma página que contém violações conhecidas (detectou `image-alt`, `label`, `html-has-lang` e `document-title`). Entre a 1ª e a 2ª execução do piloto, as medianas variaram até cerca de 6 ms na mesma configuração (por exemplo, `curso` 4.5: 83,45 e 88,97 ms), o que indica o nível de ruído esperado. Esse ruído tem o tamanho das diferenças entre versões vistas aqui (2 a 8 ms nas medianas): na tela `dashboard`, a mediana da 4.5 ficou acima da 5.3 na 1ª execução (95,56 contra 89,99 ms) e abaixo na 2ª (90,09 contra 92,34 ms). Com n = 10 e uma única passada, estes números só validam o pipeline. A análise estatística está em [analise_piloto.md](analise_piloto.md) (#167).

### 7.4. Como reproduzir

Ver [README.md, seção 4](../README.md#4-coleta-piloto).

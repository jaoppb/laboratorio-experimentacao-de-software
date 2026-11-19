# Plano de Coleta e Instrumentação: Moodle 4.5 LTS × 5.3 LTS

**Issue:** #164 · **Papel:** B (Instrumentação e Operação) · **Responsável:** Marcela Campos  
**Versão:** 1.0 (Lab05S01) · **Data:** 19/11/2026  
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
| **Linguagem / Runtime** | PHP 8.2-FPM | Versão oficial suportada por ambas as linhas LTS do Moodle (4.5 e 5.3). |
| **Banco de Dados** | MariaDB 10.11 LTS | Sistema de gerenciamento de banco de dados relacional padrão com suporte LTS. |
| **Servidor Web** | Nginx 1.26 LTS (Alpine) | Servidor reverso padronizado com buffer e timeouts idênticos. |
| **Moodle 4.5 LTS** | 4.5.1+ (build estável) | Versão LTS anterior mantida pela Moodle HQ. |
| **Moodle 5.3 LTS** | 5.3.1 (build estável) | Versão LTS atual mais recente (lançada em nov/2026). |

### 2.2. Parâmetros de Recursos e Otimização do PHP

Ambos os contêineres recebem exatamente os mesmos limites operacionais no arquivo `docker-compose.yml`:
- **Limites de Contêiner:** `cpus: "2.0"` e `mem_limit: "2048m"` (2 GB de RAM dedicados por instância).
- **PHP OPcache:** Ativado em ambos com os mesmos parâmetros (`opcache.enable=1`, `opcache.memory_consumption=128`, `opcache.max_accelerated_files=10000`, `opcache.revalidate_freq=0`).
- **PHP Configurações:** `memory_limit = 512M`, `max_execution_time = 60`, `post_max_size = 64M`, `upload_max_filesize = 64M`.

### 2.3. Especificações da Máquina Host (Registro para Reprodutibilidade)

As medições são executadas na máquina local do grupo, com registro dos parâmetros de hardware para documentação de ameaças à validade interna:
- **Processador:** CPU x86_64 multinúcleo (mínimo 4 núcleos físicos).
- **Memória RAM:** 16 GB DDR4/DDR5.
- **Sistema Operacional:** Windows 11 / Linux com Docker Desktop / Docker Engine >= 26.0.
- **Isolamento de Ruído:** Durante as rodadas de medição, nenhum outro processo pesado de usuário (IDE pesada, navegadores concorrentes, indexadores) deve estar ativo.

---

## 3. Roteiro de Coleta e Instrumentação

### 3.1. Telas Avaliadas (Objetos de Medição)

Seguindo o GQM definido na Issue #163, foram selecionadas as 4 telas de maior tráfego e impacto para alunos:
1. **Login (`/login/index.php`):** Requisição pública, representativa de autenticação e carga inicial.
2. **Painel do Aluno (`/my/`):** Tela autenticada, com agregação de cursos, prazos, linha do tempo e múltiplos blocos dinâmicos.
3. **Página de Curso Sintético (`/course/view.php?id=2`):** Tela com módulos de aprendizado, seções de tópicos, links e mídias.
4. **Tentativa de Questionário / Quiz (`/mod/quiz/view.php?id=X`):** Operação de avaliação interativa, crítica para o aluno e de alta concorrência em períodos de prova.

### 3.2. Cursos e Usuários Sintéticos

- Não são utilizados dados de instituições reais nem contas de alunos reais.
- Os dados do ambiente são povoados por meio da ferramenta padrão do Moodle para testes de benchmark e QA (`admin/tool/generator/cli/maketestcourse.php --size=S`), criando 1 curso estruturado com 10 seções, 1 quiz com 5 questões e 1 usuário estudante de teste (`aluno_teste_1`).
- As duas instâncias recebem o mesmo banco de dados semente gerado pelas fixtures.

### 3.3. Instrumentação de Desempenho (TTFB e Tempo Total)

A coleta de desempenho é realizada por script automatizado em Python (`scripts/coleta_piloto.py` e posterior runner completo da S02), utilizando a biblioteca `httpx` com conexão TCP/HTTP direta:
- **Métricas extraídas a cada requisição:**
  - `status_code`: código HTTP retornado (esperado: 200).
  - `ttfb_ms`: *Time To First Byte* em milissegundos (tempo transcorrido desde o envio da requisição HTTP até o recebimento do primeiro byte de resposta do servidor).
  - `total_time_ms`: tempo total de transferência do corpo da resposta.
  - `content_length_bytes`: tamanho da carga útil em bytes.
  - `cache_state`: `cold` (1ª requisição após restart/limpeza de cache) ou `warm` (requisições subsequentes).
- **Mitigação de Confundimento Térmico / Ordem:** As coletas utilizam **ordem alternada balanceada** (ex.: bloco Moodle 4.5 seguido de Moodle 5.3, repetindo alternadamente), evitando que aquecimento de CPU ou cache do SO favoreçam a segunda versão testada.

### 3.4. Instrumentação de Acessibilidade (WCAG 2.1 / axe-core)

A avaliação da característica de usabilidade e acessibilidade (ISO/IEC 25010) é automatizada utilizando o motor padrão de mercado `axe-core`:
- Cada uma das 4 telas nas duas versões é renderizada em navegador headless (via Playwright / `@axe-core/cli`).
- O script injeta o `axe.run()` e exporta o relatório JSON com:
  - Total de violações por tela.
  - Classificação por severidade: *crítico* (`critical`), *sério* (`serious`), *moderado* (`moderate`) e *leve* (`minor`).
  - IDs das regras WCAG violadas (ex.: contraste de cores, labels de formulários, estrutura semântica de headings).

---

## 4. Frequência e Volume de Amostras

### 4.1. Coleta Piloto (Sprint Lab05S01)
- **Objetivo do Piloto:** Validar conectividade, scripts de instrumentação, extração correta de cookies de autenticação e ausência de falhas técnicas.
- **Volume do Piloto:** 10 repetições por tela em cada versão ($10 \times 4 \text{ telas} \times 2 \text{ versões} = 80 \text{ requisições}$).
- **Avaliação de Acessibilidade Piloto:** 1 auditoria do axe-core nas 4 telas para ambas as versões.

### 4.2. Coleta Definitiva (Sprint Lab05S02)
- **Volume Planejado:** Com base na estimativa de poder estatístico descrita no Plano de Análise (#165), serão coletadas **80 repetições válidas por tela em cada versão** ($80 \times 4 \times 2 = 640 \text{ requisições de desempenho}$), garantindo poder estatístico $> 85\%$ para detectar diferenças de tamanho médio a grande com $\alpha = 0,05$.
- **Intervalo entre requisições:** 200 a 500 ms de pausa aleatória entre requisições para evitar enfileiramento artificial no Nginx local.

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
│   ├── plano_coleta_instrumentacao.md   # [Marcela, #164] Ambiente, roteiro, ética e piloto
│   └── plano_analise.md                 # [Marcela, #165] Métricas, testes, poder e impacto
├── scripts/
│   └── coleta_piloto.py                 # [Marcela, #164] Script de medição HTTP/TTFB piloto
├── dados/
│   ├── piloto/                          # Amostras da coleta piloto (JSON e CSV)
│   └── reais/                           # Dados consolidados da coleta (Sprint S02)
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

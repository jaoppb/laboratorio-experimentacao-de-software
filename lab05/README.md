# Lab05 — Experimento em Software Real: Medindo o que Importa em Produção

**Sprint 1:** Proposta do software (Moodle) + Pergunta de pesquisa + GQM e hipóteses + 7 Categorias + Plano de coleta e instrumentação + Plano de análise + Coleta piloto (executada em Moodle real).

- **Repositório:** <https://github.com/jaoppb/laboratorio-experimentacao-de-software>
- **GitHub Projects:** <https://github.com/users/jaoppb/projects/3/views/1>

---

## 1. Visão Geral do Estudo

O **Lab05** tem como objetivo planejar, executar e analisar um experimento em um software real, que esteja em operação hoje em produção e possua alto impacto no mercado e na sociedade.

- **Software Escolhido:** **Moodle** (LMS open source em PHP e banco de dados relacional).
- **Fator Estudado (Tratamentos):** Comparação entre as duas versões estáveis com suporte de longo prazo: **Moodle 4.5 LTS** × **Moodle 5.3 LTS**.
- **Caminho Metodológico Principal:** Rodar o software no ambiente controlado do grupo (contêineres Docker padronizados em PHP 8.3 e MariaDB 11.4 LTS).
- **Caminho Metodológico Secundário:** Avaliação da característica de acessibilidade (ISO/IEC 25010 / WCAG 2.1 via motor `axe-core`).

---

## 2. Pergunta de Pesquisa e GQM

**Pergunta de Pesquisa Principal (PP):**
> *Ao migrar o Moodle da versão 4.5 LTS para a 5.3 LTS, em ambiente controlado e com a mesma configuração, o tempo de resposta das páginas mais usadas por alunos muda? E a quantidade de violações de acessibilidade nessas páginas?*

**Objetivo (Template de Basili):**
> Analisar **o Moodle nas versões 4.5 LTS e 5.3 LTS**  
> com o propósito de **comparar**  
> com respeito a **desempenho (tempo de resposta TTFB e erros) e acessibilidade (WCAG)**  
> do ponto de vista de **quem administra e quem usa o Moodle (instituições e alunos)**  
> no contexto de **um ambiente controlado em contêineres Docker, com dados de curso sintéticos**.

---

## 3. Entregas da Sprint Lab05S01 e Divisão de Tarefas

Cada integrante é responsável por áreas metodológicas e técnicas estruturadas por issues no GitHub Projects:

| Issue | Integrante | Papel | Documento / Artefato |
|---|---|---|---|
| **#162** | Gabriel Assis | Papel A | [docs/escolha_software.md](docs/escolha_software.md) — Evidências dos 3 critérios (Real, Em operação, Alto impacto com +500M de usuários). |
| **#163** | Gabriel Assis | Papel A | [docs/planejamento_pesquisa.md](docs/planejamento_pesquisa.md) — GQM, hipóteses nulas e alternativas, variáveis e classificação nas 7 categorias de pesquisa. |
| **#164** | Marcela Campos | Papel B | [docs/plano_coleta_instrumentacao.md](docs/plano_coleta_instrumentacao.md) — Ambiente Docker, roteiro de coleta, instrumentação HTTP/axe, regras de ética e [scripts/coleta_piloto.py](scripts/coleta_piloto.py). |
| **#165** | Marcela Campos | Papel C | [docs/plano_analise.md](docs/plano_analise.md) — Escalas de métricas, estatística descritiva, teste de Mann-Whitney, tamanho do efeito ($\Delta$ de Cliff), poder estatístico e fórmula de estimativa de impacto. |
| **#166** | Marcela Campos | Papel B | [docs/plano_coleta_instrumentacao.md](docs/plano_coleta_instrumentacao.md) §7 — Coleta piloto em Moodle real (Docker), dados em `dados/piloto/`, validador, auditoria axe-core e registro de problemas e ajustes. |

---

## 4. Coleta Piloto

O piloto roda contra duas instâncias reais do Moodle (4.5.16 e 5.3.1) em Docker, com a mesma infraestrutura, e mede TTFB, tempo total, status HTTP e tamanho do corpo nas 4 telas (`login`, `dashboard`, `curso`, `questionario`), mais a auditoria `axe-core`. Os problemas encontrados e os ajustes feitos no plano estão em [docs/plano_coleta_instrumentacao.md](docs/plano_coleta_instrumentacao.md), seção 7.

Reprodução (requer Docker, `git` e Python >= 3.9):

```bash
cd lab05
python3 -m venv .venv && . .venv/bin/activate
# versões mínimas em pyproject.toml (dependências e extras axe/dev)
pip install httpx numpy pytest playwright axe-playwright-python
playwright install chromium

cp docker/.env.example docker/.env     # defina senhas locais
docker/preparar_codigo.sh              # baixa as tags oficiais para docker/codigo/ (ignorado pelo git)
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d
docker/instalar_moodle.sh              # instala as duas instâncias e povoa os dados sintéticos
                                       # (imprime curso_id=2 e quiz_cmid=6, usados nas rotas padrão)

set -a; . docker/.env; set +a          # exporta MOODLE_ALUNO_SENHA
python scripts/coleta_piloto.py
python scripts/auditoria_axe.py
python scripts/validar_piloto.py       # confere completude, consistência e formato
pytest                                 # testes dos scripts (sem rede e sem Docker)
```

Saídas versionadas em `dados/piloto/`:
- `amostra_piloto.csv`: 80 requisições com versão, tela, repetição, estado de cache, status, TTFB, tempo total e tamanho.
- `resumo_piloto.json`: mediana, IQR, média, p95, mínimo e máximo por tela e versão, mais `meta` (releases exatos, data, purga de cache).
- `axe/<versao>_<tela>.json`: violações WCAG 2.1 A/AA por tela e versão.

Para apagar o ambiente e os volumes: `docker compose -f docker/docker-compose.yml down -v` (apague também `docker/codigo/*/config.php` antes de reinstalar).

`python scripts/coleta_piloto.py --simulado` gera dados sintéticos em `dados/piloto_simulado/` apenas para testar o pipeline sem contêineres; esses dados não são medições.

---

## 5. Regras de Ética e Conformidade

Em estrita consonância com o enunciado do laboratório:
1. **Sem teste de carga em terceiros:** todo o tráfego de medição ocorre estritamente em contêineres locais isolados (`localhost`).
2. **Sem dados pessoais:** todos os cursos e usuários são sintéticos (`aluno_teste_1`), gerados pelo utilitário interno do Moodle (`maketestcourse.php`) e por `docker/semear_dados.php`.
3. **Respeito a robôs e termos de uso:** eventuais acessos externos a documentações respeitam o teto de no máximo 1 requisição por segundo e o `robots.txt`.

---

## 6. Estrutura de Pastas

```text
lab05/
├── docs/
│   ├── escolha_software.md              # [#162] Evidências dos 3 critérios
│   ├── planejamento_pesquisa.md         # [#163] GQM, hipóteses, 7 categorias
│   ├── plano_coleta_instrumentacao.md   # [#164/#166] Ambiente, roteiro, ética e piloto
│   └── plano_analise.md                 # [#165] Métricas, testes, poder e impacto
├── docker/                              # [#166] Ambiente Docker do piloto
│   ├── docker-compose.yml
│   ├── php-moodle.ini
│   ├── preparar_codigo.sh               # baixa as tags oficiais (docker/codigo/ não é versionado)
│   ├── instalar_moodle.sh
│   ├── semear_dados.php
│   └── .env.example
├── scripts/
│   ├── coleta_piloto.py                 # [#164/#166] Medição HTTP/TTFB (real e --simulado)
│   ├── auditoria_axe.py                 # [#166] Auditoria axe-core
│   └── validar_piloto.py                # [#166] Validador dos dados do piloto
├── tests/                               # [#166] Testes dos scripts
├── dados/
│   └── piloto/                          # Dados reais do piloto
│       ├── amostra_piloto.csv
│       ├── resumo_piloto.json
│       └── axe/
├── pyproject.toml                       # Dependências dos scripts
├── enunciado.md                         # Enunciado oficial da disciplina
└── README.md                            # Guia central do Lab05
```

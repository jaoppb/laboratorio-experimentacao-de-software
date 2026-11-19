# Lab05 — Experimento em Software Real: Medindo o que Importa em Produção

**Sprint 1:** Proposta do software (Moodle) + Pergunta de pesquisa + GQM e hipóteses + 7 Categorias + Plano de coleta e instrumentação + Plano de análise + Coleta piloto.

- **Repositório:** <https://github.com/jaoppb/laboratorio-experimentacao-de-software>
- **GitHub Projects:** <https://github.com/users/jaoppb/projects/3/views/1>

---

## 1. Visão Geral do Estudo

O **Lab05** tem como objetivo planejar, executar e analisar um experimento em um software real, que esteja em operação hoje em produção e possua alto impacto no mercado e na sociedade.

- **Software Escolhido:** **Moodle** (LMS open source em PHP e banco de dados relacional).
- **Fator Estudado (Tratamentos):** Comparação entre as duas versões estáveis com suporte de longo prazo: **Moodle 4.5 LTS** × **Moodle 5.3 LTS**.
- **Caminho Metodológico Principal:** Rodar o software no ambiente controlado do grupo (contêineres Docker padronizados em PHP 8.2 e MariaDB 10.11 LTS).
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

---

## 4. Coleta Piloto de Desempenho

A coleta piloto da Sprint 1 valida o pipeline de instrumentação medindo o *Time To First Byte* (TTFB) nas 4 telas principais (`login`, `dashboard`, `curso`, `questionario`):

Para executar o script de coleta piloto:

```bash
cd lab05
python scripts/coleta_piloto.py --repeticoes 10
```

Os dados são gerados em:
- `dados/piloto/amostra_piloto.csv`: 80 requisições balanceadas com registro de versão, tela, repetição, TTFB e estado de cache.
- `dados/piloto/resumo_piloto.json`: estatísticas descritivas (mediana, IQR, p95 e média) calculadas por tela e versão.

---

## 5. Regras de Ética e Conformidade

Em estrita consonância com o enunciado do laboratório:
1. **Sem teste de carga em terceiros:** todo o tráfego de medição ocorre estritamente em contêineres locais isolados (`localhost`).
2. **Sem dados pessoais:** todos os cursos e usuários são sintéticos (`aluno_teste_1`), gerados por utilitários internos do Moodle.
3. **Respeito a robôs e termos de uso:** eventuais acessos externos a documentações respeitam o teto de no máximo 1 requisição por segundo e o `robots.txt`.

---

## 6. Estrutura de Pastas

```text
lab05/
├── docs/
│   ├── escolha_software.md              # [#162] Evidências dos 3 critérios
│   ├── planejamento_pesquisa.md         # [#163] GQM, hipóteses, 7 categorias
│   ├── plano_coleta_instrumentacao.md   # [#164] Ambiente, roteiro, ética e piloto
│   └── plano_analise.md                 # [#165] Métricas, testes, poder e impacto
├── scripts/
│   └── coleta_piloto.py                 # [#164] Script de medição HTTP/TTFB piloto
├── dados/
│   └── piloto/                          # Amostras e resumo da coleta piloto
│       ├── amostra_piloto.csv
│       └── resumo_piloto.json
├── enunciado.md                         # Enunciado oficial da disciplina
└── README.md                            # Guia central do Lab05 (Sprint 1)
```

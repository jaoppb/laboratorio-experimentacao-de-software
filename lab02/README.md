# Lab02

**Status:** Em andamento (Sprint 1 — Desenho do Experimento + Preparação)

> Enunciado completo do professor em [`docs/enunciado.md`](docs/enunciado.md).

## Tema

Comparar, de forma controlada, a resolução de exercícios de programação
(katas) **com assistente de IA** (Copilot/ChatGPT/Claude/Gemini) **vs.
sem** (manual).

## Questões de pesquisa

- **RQ1:** o assistente reduz o tempo para resolver a tarefa?
- **RQ2:** o assistente reduz a quantidade de defeitos (testes que falham)?
- **RQ3:** o assistente muda a complexidade/duplicação do código?

## Desenho geral

Cada integrante do grupo resolve **4 ou 6 katas**, metade com IA habilitada
e metade sem, cronometrando o tempo e rodando ferramentas de análise
estática no código final de cada trial.

## Estrutura de sprints (20 pontos)

| Sprint | Pontos | Entrega |
| --- | --- | --- |
| S01 | 5 | Desenho do experimento + preparação (katas, ambiente, scripts de cronometragem e de métricas) |
| S02 | 5 | Execução — cada um resolve os katas de verdade |
| S03 | 5 | Análise estatística dos resultados + dashboard |
| Relatório Final | 5 | Relatório final |

## Divisão da Sprint 1

- **Marcela** — Script de cronometragem: mede o tempo até o kata passar em
  todos os testes de aceitação ("time-to-green"), com limite de 35 min por
  trial. Se estourar o tempo sem sucesso, registra como **censurado em
  35 min** (o dado não é descartado).
- **João Pedro** — Ambiente + script de métricas estáticas: monta o
  ambiente do experimento (linguagem, IDE, assistente de IA fixado — o
  mesmo para todos os trials) e o script que roda CK/PMD (Java) ou
  Radon/jscpd (outra linguagem) sobre o código de cada trial, medindo
  complexidade ciclomática, duplicação e LOC.
- **Gabriel Assis** — Katas + testes de aceitação — 6 katas da XIII Maratona
  Mineira de Programação (2026), com enunciados, testes de aceitação e runner
  em [`katas/`](katas/README.md). Fonte escolhida por ser pouco indexada
  (caderno de 2026), o que reduz a ameaça de memorização pela IA.
- **Marcela** — Desenho do experimento: depois que as três partes acima
  estiverem encaminhadas, o grupo fecha hipótese nula/alternativa,
  variáveis, tipo de experimento (crossover within-subject), quantidade de
  medições e ameaças à validade (efeito aprendizado, familiaridade com a
  IA, memorização de kata conhecido).

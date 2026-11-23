# Consolidação da entrega da Sprint Lab05S01

**Issue:** #167 · **Papel:** C · **Responsável:** Marcela Campos  
**Estudo:** Moodle 4.5 LTS × Moodle 5.3 LTS, desempenho (TTFB e erros) e acessibilidade (axe-core)  
**Enunciado (seção 7):** Lab05S01 = software com evidências dos três critérios + pergunta de pesquisa + caminho escolhido + primeira versão das 7 categorias + plano de coleta e de análise + coleta piloto.

Este documento é um índice. O conteúdo de cada entrega fica no documento indicado e não é copiado aqui.

## 1. Entregas e estado

| Item do enunciado | Issue | Documento ou artefato | Estado |
|---|---|---|---|
| Software com evidências dos 3 critérios (real, em operação, alto impacto) | #162 | [escolha_software.md](escolha_software.md) | Entregue. Pendências do documento: 3 confirmações (professor e leitura de moodle.org/news). |
| Pergunta de pesquisa, GQM e hipóteses | #163 | [planejamento_pesquisa.md](planejamento_pesquisa.md) §2 a §4 | Entregue. Itens **[decisão do grupo]** aguardam validação do trio. |
| Caminho escolhido (principal: rodar no ambiente do grupo; secundário: qualidade do produto) | #163 | [planejamento_pesquisa.md](planejamento_pesquisa.md) §1 | Entregue. |
| Primeira versão das 7 categorias | #163 | [planejamento_pesquisa.md](planejamento_pesquisa.md) §6 | Entregue (primeira versão, a revisar nas S02 e S03). |
| Plano de coleta e instrumentação (ambiente, roteiro, ética) | #164 | [plano_coleta_instrumentacao.md](plano_coleta_instrumentacao.md) §1 a §6 | Entregue e revisado após o piloto (versão 1.1). |
| Plano de análise (escalas, testes, tamanho do efeito, amostra, impacto) | #165 | [plano_analise.md](plano_analise.md) | Entregue. |
| Coleta piloto em Moodle real, com dados e registro de problemas | #166 | [plano_coleta_instrumentacao.md](plano_coleta_instrumentacao.md) §7, `dados/piloto/`, `docker/`, `scripts/` | Entregue (Moodle 4.5.16 e 5.3.1). |
| Análise do piloto: pipeline e suficiência da amostra | #167 | [analise_piloto.md](analise_piloto.md), `scripts/analisar_piloto.py`, `dados/piloto/analise_piloto.json` | Entregue. |

Responsáveis: Gabriel Assis (#162, #163) e Marcela Campos (#164 a #167). Reprodução completa: [README.md](../README.md#4-coleta-piloto).

## 2. Resultado do piloto em um parágrafo

O piloto rodou 80 requisições HTTP e 8 auditorias axe em duas instâncias reais do Moodle, com o mesmo ambiente, e os dados passam no validador. A análise planejada roda de ponta a ponta sobre eles. Com as 9 repetições `warm` por tela e versão, as medianas de TTFB ficam entre 43 e 95 ms, a 5.3 sai de 2 a 7 ms acima da 4.5, e nenhum p ajustado por Holm fica abaixo de 0,05. Esse resultado não pode ser lido como diferença entre as versões, porque a ordem fixa 4.5 → 5.3 e o ruído entre execuções (cerca de 6 ms) têm o mesmo tamanho. Não houve erro HTTP (0 em 40 requisições por versão) nem violação axe (0 nas 8 combinações), então o piloto só valida o pipeline para essas duas métricas. Pela variância observada, 20 a 40 repetições `warm` por tela já teriam poder de 80%, e o N = 80 previsto para a S02 fica mantido como piso, sem reduzir (detalhes e ressalvas em [analise_piloto.md](analise_piloto.md) §6).

## 3. Pendências e decisões para a S02

| Item | Origem | Destino |
|---|---|---|
| Ordem fixa 4.5 → 5.3: contrabalancear (ABBA ou sorteio) e refazer o piloto | P13 | Issue #171 |
| Tela de tentativa do quiz (com questões) não medida; o piloto mede a entrada do quiz | P6 | Issue #172 |
| Repetições `cold`: só n = 1 por grupo; planejar coleta fria à parte, com purga entre as repetições | P11 | S02 (orientação em [analise_piloto.md](analise_piloto.md) §6) |
| M4 por tela pareada não tem poder (Wilcoxon exato: p mínimo de 0,125 com 4 telas) | [analise_piloto.md](analise_piloto.md) §5 | S02: definir a unidade pareada |
| `planejamento_pesquisa.md` (PP1) fala em "tentativa de questionário", enquanto o piloto mede a entrada do quiz | #163 e #172 | Alinhar o texto quando o #172 for resolvido |
| Login recusado sem explicação em uma tentativa intermediária | P12 | Investigar antes de aumentar o volume, se voltar na S02 |

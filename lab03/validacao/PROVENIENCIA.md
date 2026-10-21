# Proveniência dos arquivos de rótulos e decisões

Este arquivo registra **quem produziu** cada arquivo de rótulos, avaliações ou decisões da
validação manual (amostra-ouro) e **como**. Arquivos que normalmente seriam produzidos por
uma pessoa mas foram produzidos por um agente de IA **devem** constar aqui, com a
independência declarada de forma honesta. A metodologia nunca deve afirmar avaliadores
humanos para rótulos produzidos por IA.

| Arquivo | Produzido por | Data | Método | Observações de independência |
|---|---|---|---|---|
| `rotulos_marcela.csv` | Humana: Marcela Campos (commit `8b20a10`, autor "Marcela") | 2026-10-15 | Rotulação manual sobre a planilha `dados/amostra_ouro/amostra_ouro_marcela.csv` (versão com sorteio incompleto, Issue #64). | Rotulação independente, sem ver a saída da heurística. **Válida apenas para as 150 linhas reais** (30 repositórios com releases sorteadas). Os rótulos das **150 linhas com tag `(pendente de persistência)`** (30 repositórios sem sorteio de releases na época) são **nulos**: foram dados sobre linhas-placeholder, sem release real, e estão listados em `marcela_linhas_invalidas.csv`. Isso inclui `tipo_projeto` e `entrega_real` desses 30 repositórios, que também ficam sem rótulo válido até uma nova rotulação. O arquivo não foi alterado; a invalidação é feita pela lista, não por edição. |
| `marcela_linhas_invalidas.csv` | Agente de IA (Kiro) a pedido do orquestrador do grupo; não é um rótulo | 2026-10-20 | Derivação mecânica: todas as linhas de `rotulos_marcela.csv` com `tag_name = (pendente de persistência)`. Colunas `repo_idx`, `release_idx`, `repo_name`, `chave_placeholder_antiga`. | Não contém julgamento de pessoa nem rótulo; só identifica linhas void. Reproduzível por filtro simples do arquivo de Marcela. |
| `rotulos_gabriel.csv` | Agente de IA (Claude, modelo Opus 5.5, via Claude Code) a pedido de Gabriel Assis, que informou o grupo; **não é rotulação humana** | 2026-10-21 | Rotulação das 300 linhas reais de `dados/amostra_ouro/amostra_ouro_gabriel.csv` a partir de um resumo gerado dos dados públicos do GitHub: descrição e tópicos de cada repositório, notas de cada release (GraphQL) e assunto dos commits incluídos (`dados/releases/`). `tipo_projeto` e `entrega_real` uma vez por repositório; `release_corretiva` pelo objetivo principal descrito nas notas (correção vs. funcionalidade). Casos duvidosos marcados com "incerto:" em `notas_justificativa`. | **Independência parcial.** Não consultou os rótulos de João nem de Marcela, nem rodou a heurística na amostra. Porém o mesmo agente implementou a heurística v1 (Issue #59) e conhecia sua regra (patch SemVer + palavras fix/revert/hotfix), o que pode aproximar os rótulos da heurística. Na concordância (#65) e na avaliação (#62), este arquivo deve ser tratado como **avaliador IA**, e a Metodologia não pode descrevê-lo como avaliador humano. |

Os demais rótulos (`rotulos_joao.csv`) e o consenso (`consenso.csv`)
ainda não existem; ao serem adicionados, registre aqui uma linha para cada um.

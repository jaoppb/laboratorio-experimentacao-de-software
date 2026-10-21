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

Os demais rótulos (`rotulos_joao.csv`, `rotulos_gabriel.csv`) e o consenso (`consenso.csv`)
ainda não existem; ao serem adicionados, registre aqui uma linha para cada um.

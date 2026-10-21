# Tipo do projeto rotulado por agentes (Issue #69)

**Natureza:** documentação de método e de resultados. Os rótulos aqui **não foram feitos por pessoas**; foram feitos por
agentes de IA. A origem fica marcada em cada linha (`tipo_projeto_origem = agente`) e deve ser citada no artigo.

**Arquivos**

| Arquivo | O que é |
|---|---|
| `dados/tipo_projeto_agentes.csv` | **Rótulos congelados** (330 linhas, mesma ordem de `repositorios.csv`), já harmonizados pela rubrica v1. |
| `dados/tipo_projeto_agentes_bruto.csv` | Saída original dos 3 rotuladores, concatenada, antes da harmonização. |
| `dados/tipo_projeto_agentes_harmonizacao.csv` | Log de mudanças da harmonização (repo, tipo antigo, tipo novo, regra). |
| `analises/validar_tipo_projeto.py` | Validador do contrato do CSV (`uv run python -m analises.validar_tipo_projeto`). |
| `analises/comparar_tipo_agentes_humano.py` | Etapa 2: comparação com a referência humana (somente leitura). |

**Não** adicionamos a coluna a `repositorios.csv|parquet`: uma regeneração do pipeline está prevista e a junção
(`full_name`) será feita na hora da análise da RQ 06.

## 1. Decisão do grupo

Os três autores decidiram que o `tipo_projeto` dos 330 repositórios é rotulado por **agentes**; a origem deve ser
marcada no conjunto de dados e no artigo; e os 60 rótulos humanos da amostra-ouro servem de **referência** para medir
a acurácia dos agentes. Pendência humana (ver seção 9): se os 60 rótulos humanos continuam como referência. João e
Gabriel disseram que sim; Marcela disse que foram substituídos.

## 2. Método

Três agentes rotuladores trabalharam em paralelo, cada um em um bloco de 110 repositórios (0–110, 110–220, 220–330),
usando README, metadados, lista de arquivos da raiz e as chamadas de API listadas em `fontes`. Foram instruídos a
**não ver rótulos humanos nem colunas de desfecho** (DORA). Cada linha traz `confianca` (alta/media/baixa),
`justificativa` e `fontes`.

**Etapa 1 (cega aos rótulos humanos)**

1. Concatenação dos blocos e checagem: exatamente os 330 `full_name` de `repositorios.csv`, na mesma ordem, sem
   duplicatas, valores permitidos, nenhum campo vazio.
2. Busca de aplicação inconsistente da rubrica: varredura das `justificativa` por runtime, compilador, interpretador,
   linguagem, toolchain, IDE/editor, skills/prompts, listas, template/boilerplate, documentação, dataset, bot,
   plugin/extensão, SDK, "tie-breaker" e TUI/terminal, comparando como cada bloco rotulou cada grupo.
3. Redação de **uma** rubrica explícita (seção 3), aplicada a todos os blocos. Para os casos de fronteira, a evidência
   guardada (`justificativa`/`fontes`) foi relida e, em alguns repositórios, o README e a lista de arquivos foram
   consultados de novo com `gh api` (somente leitura).
4. Reclassificação apenas dos repositórios cuja classe contrariava a rubrica (seção 4).
5. **Congelamento**: commit `210fb75` ("FREEZE"), feito **antes** de abrir qualquer arquivo de rótulos humanos.

**Etapa 2 (comparação)**: feita só depois do congelamento. Nenhum rótulo congelado foi alterado por causa dela.

Não usamos sub-agentes para rechecar os 40 rótulos de confiança `baixa`; eles continuam como rotulados e podem ser
filtrados pela coluna `confianca` (seção 6).

## 3. Rubrica `rubrica-tipo-v1`

Segue o guia do lab (`guialab03.md`, seção 6: biblioteca/framework, aplicação/serviço, ferramenta CLI ou outro) na
leitura mais estrita: o tipo é **a forma principal como o artefato do repositório é consumido**, e `outro` é classe
residual, não um lugar para casos difíceis.

- **R1 biblioteca/framework.** O consumo principal é importar/depender (pacote em registro, crate, módulo). Inclui
  frameworks web/UI, SDKs, bibliotecas de componentes, motores usados como dependência (ex.: bevy) e toolchains que
  se autodescrevem como bibliotecas reutilizáveis (ex.: LLVM, protobuf).
- **R2 ferramenta CLI.** O consumo principal é digitar um comando no terminal, incluindo TUIs de propósito único
  (lazygit, yazi) e **linguagens, runtimes, compiladores e interpretadores cujo executável é o artefato principal**
  (node, deno, bun, rustc/cargo, tsc, php, julia, pwsh, typst, forc). Ferramentas de desenvolvimento (bundler,
  formatador) entram aqui quando o executável próprio é o modo principal de uso (esbuild, prettier, vite).
- **R3 aplicação/serviço.** O consumo principal é executar um programa final: aplicativo com GUI (inclui
  editores/IDEs, navegadores, terminais gráficos), servidor/daemon, banco de dados, plataforma self-hosted, servidor
  MCP, motor de inferência servido (vllm, llama.cpp).
- **R4 outro.** Repositório sem software executável ou biblioteca consumível como produto principal: coleções de
  skills/prompts, templates/boilerplates/esqueletos de aplicação, documentação e tutoriais, listas.
- **R5 plugins/harness de agentes.** Se o conteúdo é predominantemente Markdown/prompts, é `outro` (R4), mesmo com
  instalador. Se tem código próprio relevante: com binário/instalador próprio e sem servidor, é `ferramenta CLI`
  (oh-my-claudecode, ruflo, OpenSpec); com dashboard ou serviço próprio, é `aplicação/serviço`.
- **Empates entre superfícies** (biblioteca + CLI + serviço): vale a primeira superfície que a descrição curta do
  repositório ou a primeira instrução de instalação do README apresenta; se ainda assim ambíguo, baixa a confiança.

Limitação conhecida da R2: bundlers e frameworks de teste consumidos principalmente por configuração/API
(webpack, babel, jest, playwright, storybook) ficaram como biblioteca/framework, e vite/esbuild/prettier como CLI. A
fronteira é razoável, mas é um julgamento; alguns desses rótulos têm confiança `media`/`baixa`.

## 4. Harmonização: o que mudou

Contagem por classe antes e depois:

| Classe | Antes (bruto) | Depois (congelado) |
|---|---:|---:|
| aplicação/serviço | 151 | 151 |
| biblioteca/framework | 97 | 95 |
| ferramenta CLI | 55 | 63 |
| outro | 27 | 21 |

Os três blocos aplicavam desempates diferentes: o bloco 0–110 mandava runtimes e compiladores ambíguos para `outro`
("tie-breaker: runtimes ambíguos = outro": node, deno, bun, TypeScript, rust); o bloco 110–220 misturava
(`ferramenta CLI` para forc, typst e PowerShell, mas `outro` para julia); o 220–330 usava `ferramenta CLI` para
"compilador com CLI principal" (esbuild), mas `outro` para o php-src. Nove repositórios mudaram:

| Repositório | Antigo | Novo | Regra |
|---|---|---|---|
| nodejs/node | outro | ferramenta CLI | R2 |
| microsoft/TypeScript | outro | ferramenta CLI | R2 |
| denoland/deno | outro | ferramenta CLI | R2 |
| oven-sh/bun | outro | ferramenta CLI | R2 |
| rust-lang/rust | outro | ferramenta CLI | R2 |
| JuliaLang/julia | outro | ferramenta CLI | R2 |
| php/php-src | outro | ferramenta CLI | R2 |
| code-yeongyu/oh-my-openagent | biblioteca/framework | ferramenta CLI | R5 (igual a oh-my-claudecode) |
| laravel/laravel | biblioteca/framework | outro | R4 (esqueleto de aplicação, como full-stack-fastapi-template) |

Mantidos sem mudança, apesar de parecerem próximos: LLVM e protobuf (R1, autodescrição de biblioteca), neovim e
Zed/VS Code (editores são aplicação, R3), llama.cpp e vllm (servem modelos, R3) contra whisper.cpp (núcleo em
`include/`/`src/`, executáveis em `examples/`; R1). Nas linhas alteradas, `justificativa` recebe o sufixo
`[harmonizado rubrica-tipo-v1: era "…" (regra)]` e `rotulador` recebe `+harmonizacao-v1`. A harmonização foi feita
pelo agente que montou este PR; o teste `test_harmonizacao_reproduz_o_arquivo_congelado` garante que bruto + log =
arquivo congelado.

## 5. Distribuição final

| Classe | n | % |
|---|---:|---:|
| aplicação/serviço | 151 | 45,8% |
| biblioteca/framework | 95 | 28,8% |
| ferramenta CLI | 63 | 19,1% |
| outro | 21 | 6,4% |

## 6. Confiança

| Confiança | n | Bloco 0–110 | Bloco 110–220 | Bloco 220–330 |
|---|---:|---:|---:|---:|
| alta | 203 | 65 | 63 | 75 |
| media | 87 | 27 | 30 | 30 |
| baixa | 40 | 18 | 17 | 5 |

Os 40 rótulos `baixa` são: 16 ferramenta CLI, 13 aplicação/serviço, 7 outro, 4 biblioteca/framework. A diferença de
rigor entre os blocos (18/17/5 `baixa`) é outro sinal de que cada rotulador tinha uma régua própria; a harmonização
corrigiu a regra, não a confiança declarada.

## 7. Deslize de cegueira divulgado

O rotulador do bloco 0–110 informou que, por um `head` no CSV de repositórios, imprimiu na tela as linhas de dois
repositórios com as colunas DORA visíveis: `mattpocock/skills` e `affaan-m/ECC`. Ele declara que os rótulos saíram só
de README e metadados. Os dois estão como `outro` (coleção de skills), classe que a rubrica determina por si.

Segunda divulgação, deste PR: o agente que harmonizou leu, antes do congelamento, o memorando
`docs/decisao_rq06_tipo_projeto.md`, que cita contagens dos rótulos da Marcela (zero `outro`; sete bibliotecas) e
quatro repositórios de fronteira (`psf/requests`, `vadimdemedes/ink`, `electron/electron`, `evanw/esbuild`). Nenhum
desses quatro foi alterado, e as nove mudanças da seção 4 decorrem da inconsistência entre blocos (listada no pedido
da tarefa) e das regras R2/R4/R5, mas não é possível provar que a informação não influenciou a escolha de "runtimes
→ CLI" (que reduz o `outro`). Os arquivos `validacao/`, `amostra_ouro/` e `sorteio_info.json` não foram abertos antes
do congelamento, nem colunas de desfecho de `repositorios.*`.

## 8. Etapa 2: comparação com a referência humana

Referência: `validacao/rotulos_marcela.csv`, **uma só avaliadora**. Para 30 dos 60 repositórios os rótulos foram dados
sobre linhas que a PR #82 declarou nulas (`historico/marcela_linhas_invalidas.csv`); por isso (b) é referência mais fraca.
Comandos: `uv run python -m analises.comparar_tipo_agentes_humano --saida-divergencias <arquivo>`.

| Subconjunto | n | Concordância | Kappa de Cohen |
|---|---:|---:|---:|
| (a) linhas válidas | 30 | 70,0% | 0,52 |
| (b) linhas nulas na PR #82 | 30 | 63,3% | 0,35 |
| (c) todos os 60 | 60 | 66,7% | 0,44 |

Kappa 0,44 é "moderado" na escala de Landis & Koch (1977); (a) fica no limite de moderado, (b) em razoável. Intervalos
de confiança não foram calculados, e com n = 30 eles são largos.

Matriz de confusão dos 60 (linhas = humana, colunas = agente):

| humana \ agente | biblioteca/framework | aplicação/serviço | ferramenta CLI | outro |
|---|---:|---:|---:|---:|
| biblioteca/framework | 6 | 0 | 0 | 1 |
| aplicação/serviço | 5 | 25 | 9 | 0 |
| ferramenta CLI | 0 | 4 | 9 | 1 |
| outro | 0 | 0 | 0 | 0 |

Precisão e recall do agente contra a referência humana (60 repositórios):

| Classe | Precisão | Recall | F1 | n humana | n agente |
|---|---:|---:|---:|---:|---:|
| biblioteca/framework | 0,55 | 0,86 | 0,67 | 7 | 11 |
| aplicação/serviço | 0,86 | 0,64 | 0,74 | 39 | 29 |
| ferramenta CLI | 0,50 | 0,64 | 0,56 | 14 | 18 |
| outro | n/d | n/d | n/d | 0 | 2 |

`outro`: a humana não usou a classe, então precisão e recall não são interpretáveis (o script mostra 0,00 por
convenção `zero_division=0`). As tabelas por subconjunto (a) e (b) saem do mesmo comando.

Leituras, sem arbitrar: (i) o desacordo se concentra em aplicação (humana) × CLI/biblioteca (agente): 14 dos 20
desacordos têm a humana em `aplicação/serviço`; os agentes classificam como CLI ferramentas executadas no terminal
(herdr, croc, esbuild, codewhale), e como biblioteca pacotes que a humana tratou como aplicação (psf/requests,
ink, electron); (ii) a acurácia sobe com a confiança declarada (alta 27/33 = 82%, media 10/16 = 63%, baixa 3/11 = 27%),
o que sugere usar `confianca` como filtro de sensibilidade; (iii) a harmonização não mudou a concordância nos 60
(bruto 66,7%, kappa 0,445; final 66,7%, kappa 0,439): `rust-lang/rust` passou a coincidir com a humana (CLI), e
`laravel/laravel` deixou de coincidir (a humana disse biblioteca/framework), `oven-sh/bun` segue discordando.

Divergências (20) para a arbitragem humana; nenhuma foi resolvida aqui:

| Repositório | Agente | Humana | Justificativa do agente (resumo) |
|---|---|---|---|
| electron/electron | biblioteca/framework | aplicação/serviço | Framework para apps desktop; usado como dependência |
| fatedier/frp | aplicação/serviço | ferramenta CLI | Proxy reverso (frps/frpc) executado como servidor/cliente de rede |
| paperclipai/paperclip | aplicação/serviço | ferramenta CLI | "open-source app…"; Docker; aplicação |
| oven-sh/bun | ferramenta CLI | aplicação/serviço | Runtime JS all-in-one com executável `bun` (harmonizado) |
| laravel/laravel | outro | biblioteca/framework | Esqueleto de aplicação do framework Laravel (harmonizado) |
| opendatalab/MinerU | ferramenta CLI | aplicação/serviço | Parsing de documentos com CLI, API e skill; entrada principal sem evidência clara |
| pbakaus/impeccable | outro | ferramenta CLI | Skill/guia de design para agentes, conteúdo majoritariamente prompts |
| openbq-org/OpenBB | biblioteca/framework | aplicação/serviço | Plataforma de dados Python usada como pacote; também cli/ e desktop/ |
| career-ops-hq/career-ops | ferramenta CLI | aplicação/serviço | Agente de vagas executado no terminal; mistura prompts e scripts |
| cline/cline | aplicação/serviço | ferramenta CLI | Agente como SDK, extensão de IDE ou CLI; produto principal é a extensão |
| ChrisTitusTech/winutil | aplicação/serviço | ferramenta CLI | Utilitário PowerShell com interface gráfica XAML |
| heygen-com/hyperframes | biblioteca/framework | aplicação/serviço | Framework HTML→vídeo com CLI associada |
| PowerShell/PowerShell | ferramenta CLI | aplicação/serviço | Shell/linguagem de linha de comando (`pwsh`) |
| psf/requests | biblioteca/framework | aplicação/serviço | Biblioteca HTTP para Python |
| herdrdev/herdr | ferramenta CLI | aplicação/serviço | Multiplexador de terminal (TUI) para agentes |
| codewhale-hq/Codewhale | ferramenta CLI | aplicação/serviço | Agent engine e cliente de terminal em Rust |
| schollz/croc | ferramenta CLI | aplicação/serviço | "CLI file-transfer tool" |
| vadimdemedes/ink | biblioteca/framework | aplicação/serviço | "React for interactive command-line apps"; pacote npm |
| evanw/esbuild | ferramenta CLI | aplicação/serviço | Bundler; binário Go usado via CLI |
| Yeachan-Heo/oh-my-claudecode | ferramenta CLI | aplicação/serviço | Orquestração multiagente; plugin e pacote npm com bins `omc` |

(Texto completo das justificativas: coluna `justificativa` do CSV.)

## 9. Limitações e ameaças à validade

- **Referência humana de uma só avaliadora.** Não existe kappa entre humanos (faltam `rotulos_joao.csv` e
  `rotulos_gabriel.csv`), então não sabemos quão confiável é a própria categoria. Um kappa agente × humana de 0,44 pode
  refletir erro do agente, ambiguidade da rubrica, ou idiossincrasia da avaliadora (por exemplo, tratar ferramentas
  executadas no terminal como "aplicação").
- **Referência parcialmente fraca.** Metade dos 60 rótulos foi dada sobre linhas que a PR #82 declarou nulas; o
  resultado de (b) é menos confiável. Os 60 também são só 18% dos 330, e Rust está sobre-representado neles
  (`decisao_rq06_tipo_projeto.md`).
- **Circularidade.** A rubrica foi escrita por um agente depois de ver os rótulos de outros agentes. Os agentes
  compartilham vieses de modelo e de fontes (README, descrição), e a harmonização reduz a variância entre blocos, não o
  viés comum.
- **Cegueira.** Quebras conhecidas: o deslize do rotulador 0–110 (dois repositórios, seção 7) e a leitura do memorando
  pelo harmonizador (seção 7). Fora isso, ninguém abriu rótulos humanos nem colunas de desfecho antes do congelamento.
- **Rótulos de baixa confiança.** 40 de 330 (12%); a acurácia nos 11 que caem na amostra-ouro é 27%.
- **Sem rechecagem independente** dos rótulos `baixa` (não foram usados sub-agentes) e sem segunda rotulação completa
  por outro agente.
- **Uso na RQ 06.** O tipo rotulado por agentes é um fator observacional medido com erro; resultados por tipo devem
  ser lidos com essa ressalva e, idealmente, com análise de sensibilidade (só `confianca` alta/media; só os 60
  humanos).

## 10. Como citar a origem no artigo

Sugestão para a Metodologia: "O tipo do projeto (biblioteca/framework, aplicação/serviço, ferramenta CLI, outro) dos
330 repositórios foi rotulado por três agentes de IA (um por bloco de 110 repositórios), sem acesso aos desfechos
(exceto por um deslize registrado) e depois harmonizado por uma rubrica única (`rubrica-tipo-v1`, 9 reclassificações).
O rótulo não é humano: a coluna `tipo_projeto_origem` vale `agente` em todas as linhas. Contra 60 rótulos humanos de
uma avaliadora, a concordância foi de 66,7% (κ de Cohen = 0,44)." Na Ameaças à Validade, repetir as limitações da
seção 9. Registrar também na tabela de proveniência (`validacao/PROVENIENCIA.md`) quando os rótulos humanos forem
revistos.

## 11. Pendências humanas

1. Decidir se os 60 rótulos humanos continuam como referência de acurácia (João e Gabriel: sim; Marcela: substituídos).
2. Arbitrar as 20 divergências da seção 8 e, se a referência continuar, rotular novamente os 30 repositórios cujas
   linhas foram anuladas.
3. Se o grupo quiser um kappa entre humanos para o tipo, completar `rotulos_joao.csv` e `rotulos_gabriel.csv`.

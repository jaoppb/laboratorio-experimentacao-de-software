# Confiabilidade entre execuções de IA e aviso de validade (Issues #57, #61, #64, #65)

**Código:** `analises/auditoria_rotulos_ia.py` · **Testes:** `tests/test_rotulos_ia.py`
**Proveniência dos arquivos:** [`validacao/PROVENIENCIA.md`](../validacao/PROVENIENCIA.md)

> Este documento mede concordância **bruta** entre rótulos já versionados. Ele **não** calcula o
> kappa de Fleiss entre os três slots, o consenso nem qualquer resultado da heurística: isso é um
> passo posterior (`docs/protocolo_consenso.md`), que só pode ocorrer com os rótulos já commitados.

## 1. Quem rotulou o quê

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `validacao/rotulos_joao.csv` | 300 linhas | IA (claude-opus-5.5, esforço `high`) |
| `validacao/rotulos_gabriel.csv` | 300 linhas (arquivo preexistente, **não modificado**) | IA (Claude Code, Opus 5.5; esforço desconhecido; independência parcial) |
| `validacao/rotulos_marcela.csv` | 300 linhas: 150 humanas (Marcela, inalteradas) + 150 de IA | humano (150) e IA (claude-opus-5.5, esforço `high`; 150) |
| `validacao/extra/rotulos_gabriel_execucao2_ia.csv` | 300 linhas, **fora dos slots** | IA (claude-opus-5.5, esforço `high`), segunda execução para o slot `gabriel`, repositórios em ordem decrescente |

Os arquivos `*_origem.csv` registram a origem de cada linha. O de Gabriel
(`rotulos_gabriel_origem.csv`) foi **derivado da linha dele em `PROVENIENCIA.md`** (modelo
`claude-opus-5.5 (Claude Code)`, esforço `desconhecido`, data `2026-10-21`, independência parcial).

Todas as execuções de IA usam o **mesmo modelo**: os erros são correlacionados, e as concordâncias
abaixo medem consistência de um modelo consigo mesmo, **não** concordância entre pessoas.

## 2. Confiabilidade entre execuções (slot `gabriel`: execução commitada × execução 2)

Unidade: repositório (60) em `tipo_projeto` e `entrega_real`; release (300) em `release_corretiva`.
A execução commitada é a de Gabriel (Claude Code), que conhecia a regra da heurística v1; a
execução 2 é cega à heurística. Comando (a partir de `lab03/`):

```bash
uv run python -m analises.auditoria_rotulos_ia confiabilidade
```

| Dimensão | Unidade | N | Concordância | Kappa de Cohen |
|---|---|---:|---:|---:|
| `tipo_projeto` | repositório | 60 | 88,3% | 0,823 |
| `entrega_real` | repositório | 60 | 100,0% | 1,000 |
| `release_corretiva` | release | 300 | 92,7% | 0,852 |

Leitura e ressalvas:

* A concordância é alta, mas **vem do mesmo modelo**; ela mostra que o critério produz rótulos
  estáveis para esse modelo, não que pessoas concordariam.
* `entrega_real` é quase constante (59 `sim` e 1 `não` na execução commitada), então o kappa de
  100% / 1,000 sustenta-se em um único repositório `não` e **não é informativo**.
* `release_corretiva`: 22 das 300 releases divergem (13 `não` na execução commitada viraram `sim` na
  execução 2; 9 `sim` viraram `não`). A execução 2 tem 138 `sim` e 162 `não`; a commitada, 134 e 166.
* `tipo_projeto`: as divergências são entre `ferramenta CLI`, `aplicação/serviço` e `outro` (7 de 60).

## 3. Aviso de validade: IA × as 150 linhas humanas de Marcela

Concordância bruta de cada execução de IA com as **150 linhas humanas** de `rotulos_marcela.csv`
(30 repositórios; as 150 linhas que **não** constam em `validacao/historico/marcela_linhas_invalidas.csv`).
Comando (a partir de `lab03/`):

```bash
uv run python -m analises.auditoria_rotulos_ia ia-vs-humano
```

| Execução de IA | `release_corretiva` (150 releases) | `tipo_projeto` (30 repos = 150 linhas) | `entrega_real` (30 repos) |
|---|---:|---:|---:|
| `rotulos_joao.csv` | 58,0% (κ 0,113) | 70,0% (κ 0,526) | 96,7% (κ 0,000) |
| `rotulos_gabriel.csv` (commitado) | 58,7% (κ 0,129) | 70,0% (κ 0,514) | 100,0% (κ indefinido) |
| `extra/…execucao2_ia.csv` | 57,3% (κ 0,111) | 73,3% (κ 0,592) | 100,0% (κ indefinido) |

Como cada repositório tem 5 linhas com o mesmo `tipo_projeto`, a concordância "por linha" e "por
repositório" de `tipo_projeto` são iguais (70,0%).

**Isto é um aviso de validade, não um resultado.** Em `release_corretiva`, as três execuções de IA
concordam com Marcela só em ≈58% das releases, kappa de Cohen ≈ 0,11 a 0,13 (nível "leve" na escala de
Landis & Koch): a leitura de "release corretiva" da IA e a dela diferem de forma sistemática. Em
`tipo_projeto` a concordância é ≈70% (κ ≈ 0,5, "moderada"). Em `entrega_real` quase não há variação
(o kappa é indefinido ou nulo). Portanto:

* a boa concordância entre execuções de IA (seção 2) **não** implica que os rótulos de IA reproduzam o
  julgamento humano;
* o `consenso.csv` automático (maioria de rótulos de IA) herdará esse viés e deve ser apresentado
  com essa ressalva, separando `*_votos_ia` e `*_votos_humano`;
* na amostra de 150 linhas há uma única avaliadora humana, então não é possível separar "a IA erra"
  de "Marcela interpreta de outro jeito" sem uma segunda pessoa.

## 4. Integridade das 150 linhas humanas

```bash
git show origin/main:lab03/validacao/rotulos_marcela.csv > /tmp/rotulos_marcela_main.csv   # antes deste PR
uv run python -m analises.auditoria_rotulos_ia humanas --anterior /tmp/rotulos_marcela_main.csv
```

Resultado: 150 linhas humanas byte a byte idênticas, 150 linhas de IA com chaves iguais às de
`historico/marcela_linhas_invalidas.csv`, e SHA-256 das linhas humanas (em ordem, com CRLF)
`7c59bb376dca7e4d07b396198dcc4be6f724863e1b2401b95a52287f570ee57b`. O mesmo hash é verificado em
`tests/test_rotulos_ia.py`, de modo que uma edição futura nessas linhas faz o teste falhar.

## 5. Validação com a ferramenta de concordância

```bash
uv run python -m analises.concordancia validar --origens
```

Valida os três slots (300 linhas cada, chaves e identificação iguais às da planilha) e imprime a
proveniência: `marcela` = `humano` 150 + `ia` 150; `gabriel` = `ia` 300 (independência parcial);
`joao` = `ia` 300, com o aviso de que o kappa mede concordância entre execuções do mesmo modelo.
A lista `marcela_linhas_invalidas.csv` foi movida para `validacao/historico/` porque a
ferramenta a usa automaticamente quando está ao lado de `rotulos_marcela.csv` e ignoraria as 150 linhas
agora válidas (ver `protocolo_consenso.md`, seção 3.3).

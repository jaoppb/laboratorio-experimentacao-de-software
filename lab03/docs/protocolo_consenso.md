# Protocolo de concordância (kappa de Fleiss) e consenso (Issue #65)

**Código:** `analises/concordancia.py` · **Testes:** `tests/test_concordancia.py`
**Entradas:** `validacao/rotulos_{joao,gabriel,marcela}.csv` (um por avaliador, gerados na
rotulação independente das Issues #57, #61 e #64)
**Saída humana:** `validacao/consenso.csv` (produzido na reunião de consenso)

> Este documento descreve a **ferramenta e o protocolo**. Os valores reais de kappa e o
> `consenso.csv` só existem depois que os três arquivos de rótulos estiverem no repositório
> e a reunião acontecer; nenhum número real é reportado aqui.

## 1. Planilha e unidades de análise

A planilha de rotulação (`dados/amostra_ouro/amostra_ouro_template.csv`) tem **300 linhas**:
60 repositórios sorteados (semente 42) × 5 releases sorteadas por repositório. Cada
dimensão é um julgamento de natureza diferente, e por isso a **unidade de análise muda**:

| Dimensão            | Categorias                                                                   | Natureza do julgamento | Unidade de análise | N     |
|---------------------|------------------------------------------------------------------------------|------------------------|--------------------|-------|
| `tipo_projeto`      | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro`       | por **repositório**    | repositório        | 60    |
| `entrega_real`      | `sim`, `não`, `incerto`                                                      | por **repositório**    | repositório        | 60    |
| `release_corretiva` | `sim`, `não`                                                                 | por **release**        | release            | 300   |

`tipo_projeto` e `entrega_real` aparecem **repetidos nas 5 linhas** do mesmo repositório.
Se o kappa fosse calculado sobre as 300 linhas, cada repositório contaria 5 vezes e o
resultado ficaria artificialmente inflado e com amostra efetiva superestimada. Por isso a
ferramenta:

* **valida** que, em cada arquivo, `tipo_projeto` e `entrega_real` são iguais nas linhas do
  mesmo `repo_idx` (se não forem, o arquivo é rejeitado);
* **conta cada repositório uma única vez** nessas duas dimensões (N = 60);
* usa as 300 releases (chave `repo_idx` + `release_idx`) em `release_corretiva`.

## 2. Como o kappa de Fleiss é calculado

Para cada dimensão, monta-se uma matriz *unidades × avaliadores* com a categoria escolhida
por cada um dos 3 avaliadores. As categorias em português são convertidas para códigos
numéricos de forma **explícita e fixa** (a posição na lista de categorias da tabela acima,
começando em 0; ex.: `sim` = 0, `não` = 1, `incerto` = 2 em `entrega_real`). Em seguida:

1. `statsmodels.stats.inter_rater.aggregate_raters(matriz, n_cat=<nº de categorias>)` gera a
   tabela *unidades × categorias* (quantos avaliadores escolheram cada categoria). O `n_cat`
   é fixo para que categorias que ninguém usou entrem com contagem zero.
2. `statsmodels.stats.inter_rater.fleiss_kappa(tabela, method="fleiss")` calcula

   ```
   P_i = (Σ_j n_ij² − n) / (n·(n−1))      concordância na unidade i (n = 3 avaliadores)
   P̄   = média de P_i                     concordância observada
   P_e = Σ_j p_j²                          concordância esperada por acaso (p_j = proporção da categoria j)
   κ   = (P̄ − P_e) / (1 − P_e)
   ```

Além do kappa, a saída traz a **concordância unânime (%)**: fração de unidades em que os 3
avaliadores escolheram a mesma categoria. Ela é reportada só como apoio; o kappa é a medida
principal por corrigir a concordância ao acaso.

**Kappa indefinido.** Se todos os avaliadores escolherem sempre a mesma categoria em todas
as unidades (ex.: todos `sim` em `entrega_real`), `P_e = 1` e o kappa é `0/0`. A ferramenta
imprime `n/d` e a interpretação "indefinido (sem variabilidade nas categorias)", em vez de
falhar. Isso deve ser discutido no artigo (o kappa não mede concordância sem variação).

### 2.1 Interpretação (Landis & Koch, 1977)

| Kappa        | Interpretação  |
|--------------|----------------|
| < 0          | pobre          |
| 0,00 – 0,20  | leve           |
| 0,21 – 0,40  | razoável       |
| 0,41 – 0,60  | moderada       |
| 0,61 – 0,80  | substancial    |
| 0,81 – 1,00  | quase perfeita |

Os limites superiores são inclusivos (ex.: 0,40 → razoável). Um kappa baixo indica que o
próprio critério é ambíguo; isso é um achado e deve ser discutido na seção de ameaças à
validade do artigo.

### 2.2 Verificação da implementação

Os testes (`tests/test_concordancia.py`) usam fixtures sintéticas com valores calculados à
mão: concordância perfeita (κ = 1), um caso binário com 4 unidades (κ = 1/3) e um caso com
3 categorias (κ = 17/47 ≈ 0,362), além de verificar que repositórios contam uma vez em
`tipo_projeto`/`entrega_real`.

## 3. Formato dos arquivos

### 3.1 `validacao/rotulos_<avaliador>.csv`

`<avaliador>` ∈ {`joao`, `gabriel`, `marcela`}. CSV UTF-8 (com ou sem BOM), mesmas 11
colunas e **mesmas 300 linhas** da planilha em branco:

```
repo_idx,repo_name,repo_url,tipo_projeto,entrega_real,release_idx,tag_name,published_at,release_url,release_corretiva,notas_justificativa
```

A ferramenta rejeita o arquivo (com mensagem indicando linhas/chaves) se:

* faltar alguma coluna, ou o número de linhas for diferente da planilha;
* as chaves (`repo_idx`, `release_idx`) estiverem duplicadas, ausentes ou sobrando, ou
  `repo_name`/`tag_name` não baterem com a planilha sorteada;
* `tipo_projeto`, `entrega_real` ou `release_corretiva` estiverem em branco ou fora das
  categorias permitidas (`incerto` **não** é permitido em `release_corretiva`);
* `tipo_projeto`/`entrega_real` variarem entre as releases do mesmo repositório.

### 3.2 `validacao/consenso.csv`

Mesmas colunas de identificação da planilha, com os rótulos de consenso e, ao lado de cada
um, a **origem** da decisão. `notas_justificativa` é substituída por `notas_consenso`:

```
repo_idx,repo_name,repo_url,tipo_projeto,tipo_projeto_origem,entrega_real,entrega_real_origem,release_idx,tag_name,published_at,release_url,release_corretiva,release_corretiva_origem,notas_consenso
```

`*_origem` ∈ {`unanimidade`, `maioria`, `reuniao`}. O valor `pendente` só existe no modelo
gerado pela ferramenta e **não pode restar** no arquivo final (`verificar-consenso` falha).
O consenso de `tipo_projeto` e `entrega_real` é por repositório, portanto repetido nas 5
linhas dele; o consenso de `release_corretiva` é por linha.

## 4. Protocolo de desempate e consenso

1. **Pré-requisito.** Os três `rotulos_*.csv` estão commitados em `validacao/` e passam em
   `validar`. A rotulação foi independente (sem consulta entre os integrantes e sem ver a
   saída da heurística). **Os arquivos de rótulos não são editados depois do cálculo do
   kappa**: o kappa mede a rotulação independente; correções vão apenas para o consenso.
2. **Kappa antes do consenso.** Calcula-se e registra-se o kappa (comando abaixo) *antes* da
   reunião, para que a discussão não contamine a medida.
3. **Regra de maioria simples.** Em cada unidade, o rótulo vencedor é o escolhido por pelo
   menos 2 dos 3 avaliadores (placares 3-0 ou 2-1). A ferramenta já preenche essas unidades
   (`unanimidade` ou `maioria`). Como `release_corretiva` tem só 2 categorias, ela **sempre**
   tem maioria; nenhuma release fica pendente.
4. **Reunião para os empates.** Os casos **1-1-1** (só possíveis em `tipo_projeto` e
   `entrega_real`, que têm 3 ou mais categorias) ficam em branco com origem `pendente` e são
   decididos **em reunião** com os três presentes, abrindo o repositório/release no GitHub
   (a lista de divergências traz o link). A decisão deve nascer da
   argumentação sobre o critério do guia; o objetivo é que dois ou mais cheguem ao mesmo
   rótulo. Se, depois da discussão, os três mantiverem rótulos distintos, aplica-se o
   **desempate final**: `tipo_projeto` = `outro` e `entrega_real` = `incerto` (as categorias
   de "não classificável"), com a justificativa em `notas_consenso`.
5. **Tratamento de `incerto`** (só em `entrega_real`):
   * `incerto` é uma categoria como as demais: entra no kappa e conta como voto na maioria.
     Se a maioria for `incerto` (ex.: `incerto`, `incerto`, `sim`), o consenso é `incerto`;
   * um empate 1-1-1 `sim`/`não`/`incerto` vai para a reunião; o grupo pode decidir
     `sim` ou `não` com base em novas evidências, ou manter `incerto` quando a dúvida persistir;
   * o consenso `incerto` **não é forçado** para `sim`/`não`. Ele é mantido no arquivo e
     tratado nas análises como "entrega não confirmada" (decisão de uso no artigo é do grupo
     e deve ser declarada junto aos resultados).
6. **Revisão opcional dos 2-1.** A reunião também pode rever casos 2-1 se o dissidente
   apontar um erro de leitura do critério. Nesse caso, altera-se o rótulo no
   `consenso.csv`, troca-se a origem para `reuniao` e justifica-se em `notas_consenso`.
7. **Quem registra.** Um integrante (relator, definido no início da reunião) edita o
   `consenso.csv` durante a reunião: preenche o rótulo, muda `*_origem` de `pendente` para
   `reuniao` e escreve a justificativa curta em `notas_consenso`. Os outros dois conferem
   a tela compartilhada. O relator e a data da reunião são registrados no corpo do commit.
8. **Fechamento.** Roda-se `verificar-consenso`; só com ele passando o `consenso.csv` é
   commitado (mensagem `#65 add gold standard consensus labels`). O `consenso.csv` é a
   referência para a avaliação da heurística (precisão/recall/F1, Issue #62) e para o
   `tipo_projeto` usado na RQ 06.

## 5. Comandos (a partir de `lab03/`)

A ferramenta **nunca cria** `rotulos_*.csv` e **nunca grava** `consenso.csv` sem um caminho
de saída explícito (`--saida` é obrigatório no comando `consenso`, sem valor padrão), e não
sobrescreve arquivo existente sem `--forcar`. Se faltar qualquer um dos três arquivos de
rótulos, os comandos terminam com código de saída 2 e uma mensagem listando os que faltam.

```bash
cd lab03 && uv sync

# 1. Validar o formato (todos os 3; ou só os que já existem, ex.: --avaliadores marcela)
uv run python -m analises.concordancia validar
uv run python -m analises.concordancia validar --avaliadores marcela

# 2. Kappa de Fleiss nas três dimensões (e, opcionalmente, JSON para o relatório)
uv run python -m analises.concordancia kappa
uv run python -m analises.concordancia kappa --json dados/analises/kappa_fleiss.json

# 3. Divergências: pauta da reunião (CSV opcional)
uv run python -m analises.concordancia divergencias --saida dados/analises/divergencias.csv

# 4. Modelo de consenso (maioria preenchida, empates em branco) em um caminho EXPLÍCITO.
#    Para trabalhar direto no arquivo final, o caminho é validacao/consenso.csv:
uv run python -m analises.concordancia consenso --saida validacao/consenso.csv

# 5. Depois da reunião, verificar o arquivo final (sem pendências, valores válidos)
uv run python -m analises.concordancia verificar-consenso
```

Parâmetros comuns: `--validacao-dir` (default `validacao`) e `--planilha`
(default `dados/amostra_ouro/amostra_ouro_template.csv`). Códigos de saída: `0` ok;
`1` arquivo inválido ou erro de uso; `2` arquivos de avaliadores ausentes.

Saída do comando `kappa` (formato; os números abaixo são apenas ilustrativos, não reais):

```
dimensão          unidade          N    kappa  unânime %  interpretação (Landis & Koch)
tipo_projeto      repositorio     60    x.xxx      xx.x%  ...
entrega_real      repositorio     60    x.xxx      xx.x%  ...
release_corretiva release       300    x.xxx      xx.x%  ...
```

## 6. Estado atual e pendências humanas

* Existe apenas `validacao/rotulos_marcela.csv` (formato validado pela ferramenta). Faltam
  `rotulos_joao.csv` e `rotulos_gabriel.csv`, que dependem da rotulação manual (#57/#61).
* Faltam: o cálculo do kappa real, a reunião de consenso e o commit de `validacao/consenso.csv`.

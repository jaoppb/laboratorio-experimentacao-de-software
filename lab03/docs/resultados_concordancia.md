# Resultados de concordância (kappa de Fleiss) e consenso automático (Issue #65)

**Código:** `analises/concordancia.py`, `analises/auditoria_rotulos_ia.py` (sem alterações neste PR)
**Entradas:** `validacao/rotulos_{joao,gabriel,marcela}.csv` + `rotulos_*_origem.csv`, `validacao/extra/rotulos_gabriel_execucao2_ia.csv`
**Saída:** `validacao/consenso.csv` (consenso **automático**, sem reunião)
**Protocolo e formato:** [`protocolo_consenso.md`](./protocolo_consenso.md) (seção 7: modo com avaliadores IA) ·
**Proveniência:** [`../validacao/PROVENIENCIA.md`](../validacao/PROVENIENCIA.md) ·
**Confiabilidade e aviso de validade:** [`confiabilidade_execucoes_ia.md`](./confiabilidade_execucoes_ia.md)

> **Leia isto primeiro.** Os três "avaliadores" **não são três pessoas**. `joao` e `gabriel` são
> execuções de IA (o mesmo modelo, `claude-opus-5.5`; a de `gabriel` é do Claude Code, com
> independência parcial) e `marcela` mistura **150 linhas humanas** (a única evidência humana) e
> **150 linhas de IA**. O kappa abaixo mede **consistência entre execuções do mesmo modelo**, não
> ambiguidade do critério entre pessoas. Todo comando de kappa imprime o aviso:
> `!!! AVISO: rótulos de IA: o kappa mede concordância entre execuções do mesmo modelo, não entre pessoas !!!`.
> Nenhum número daqui envolve a heurística (`cfr_b`): ela não foi executada nem avaliada neste PR.

## 1. Método

* **Unidades de análise** (como em `protocolo_consenso.md`, seção 1): 60 **repositórios** em
  `tipo_projeto` e `entrega_real` (cada repositório conta uma vez, não cinco) e 300 **releases** em
  `release_corretiva`.
* **Kappa de Fleiss** (statsmodels, `method="fleiss"`) entre os três slots; **kappa de Cohen**
  (scikit-learn) para pares. Ao lado de cada kappa vai a **concordância bruta** (no Fleiss, a
  *unânime*: fração de unidades em que os 3 escolheram a mesma categoria; nos pares, % de
  unidades iguais). Interpretação: Landis & Koch (1977), faixas em `protocolo_consenso.md`, seção 2.1.
* **Consenso automático** (`consenso --modo-automatico --origens`): maioria simples por unidade;
  empate 1-1-1 vira `tipo_projeto = outro` / `entrega_real = incerto` (origem `desempate_automatico`);
  `release_corretiva` é binária e não empata. Não houve reunião.
* **A reunião de consenso foi dispensada por falta de tempo** (decisão de 2026-10-21); portanto os
  empates e as divergências 2-1 não foram deliberados por pessoas e o `consenso.csv` deve ser
  descrito como automático.
* Dados lidos como estão em `main`; nenhum arquivo de rótulos foi alterado. Execução em 2026-10-21.

## 2. Kappa de Fleiss: três slots (`joao`, `gabriel`, `marcela`)

Comando: `uv run python -m analises.concordancia kappa --origens`.

| Dimensão | Unidade | N | Kappa de Fleiss | Concordância unânime | Landis & Koch |
|---|---|---:|---:|---:|---|
| `tipo_projeto` | repositório | 60 | 0,787 | 80,0% | substancial |
| `entrega_real` | repositório | 60 | 0,492 | 96,7% | moderada (**instável**, ver 2.1) |
| `release_corretiva` | release | 300 | 0,625 | 72,3% | substancial |

Resumo de proveniência impresso pela ferramenta: `marcela`: humano 150 + IA (`claude-opus-5.5`,
esforço `high`) 150; `gabriel`: IA 300 (`claude-opus-5.5 (Claude Code)`, esforço `desconhecido`;
"independência (gabriel): parcial: o mesmo assistente implementou a heurística v1 (#59)"); `joao`:
IA (`claude-opus-5.5`, `high`) 300.

### 2.1 `entrega_real`: paradoxo da prevalência

`entrega_real` é quase constante: dos 180 votos (60 repositórios × 3), **176 são `sim` (97,8%)**,
2 `não` e 2 `incerto`. Só 2 repositórios não são unânimes (96,7% de unanimidade), e o consenso
tem 59 `sim` e 1 `não`. Com a categoria dominante tão frequente, a concordância esperada ao
acaso é altíssima (`P_e ≈ 0,96`) e **poucas discordâncias derrubam o kappa** (0,492) apesar de
96,7% de concordância bruta; nos pares varia de 0,326 a 1,000 conforme caiam ou não nas mesmas
2 divergências. O kappa de `entrega_real` **não é informativo**: reporte sempre a concordância
bruta e a prevalência junto, e não interprete 0,492 como "moderada" isoladamente.

### 2.2 Dentro do slot `marcela`: linhas humanas × linhas de IA

Como o slot `marcela` mistura origens, o kappa agregado da seção 2 é uma média de duas situações bem
diferentes. Separando pelas linhas em que `marcela` é **humana** (30 repositórios, 150 releases) ou **IA**
(os outros 30 repositórios, 150 releases), com os mesmos `joao` e `gabriel` (IA) nos dois casos:

| Dimensão | Subconjunto | N | Kappa de Fleiss | Unânime | Landis & Koch |
|---|---|---:|---:|---:|---|
| `tipo_projeto` | marcela **humana** | 30 | 0,665 | 70,0% | substancial |
| `tipo_projeto` | marcela IA | 30 | 0,900 | 90,0% | quase perfeita |
| `entrega_real` | marcela **humana** | 30 | −0,011 | 96,7% | pobre (sem variação: não informativo) |
| `entrega_real` | marcela IA | 30 | 0,658 | 96,7% | substancial (idem) |
| `release_corretiva` | marcela **humana** | 150 | 0,368 | 55,3% | razoável |
| `release_corretiva` | marcela IA | 150 | 0,858 | 89,3% | quase perfeita |

Quando o terceiro "avaliador" é humano, a concordância cai de "quase perfeita" para "razoável" em
`release_corretiva`. Isso é o aviso de validade da seção 4 visto pelo Fleiss. (A comparação
não é um experimento controlado: os 30 repositórios humanos e os 30 de IA foram separados pelo
histórico do sorteio, não por sorteio aleatório.)

## 3. Pares (kappa de Cohen) e robustez

Unidades como na seção 2. Os pares com `marcela` usam as 300 linhas e, portanto, **misturam**
150 linhas humanas e 150 de IA; o par IA × humano puro está na seção 4.

| Par | `tipo_projeto` (N=60) | `entrega_real` (N=60) | `release_corretiva` (N=300) |
|---|---|---|---|
| `joao` × `gabriel` | 95,0% · κ 0,924 | 96,7% · κ 0,326 | 93,7% · κ 0,871 |
| `joao` × `marcela` | 81,7% · κ 0,721 | 96,7% · κ 0,326 | 76,7% · κ 0,525 |
| `gabriel` × `marcela` | 81,7% · κ 0,713 | 100,0% · κ 1,000 | 74,3% · κ 0,480 |
| `joao` × `gabriel` (execução 2) | 90,0% · κ 0,851 | 96,7% · κ 0,326 | 93,0% · κ 0,858 |
| `gabriel` (execução 2) × `marcela` | 83,3% · κ 0,746 | 100,0% · κ 1,000 | 76,3% · κ 0,522 |
| `gabriel` × `gabriel` (execução 2) | 88,3% · κ 0,823 | 100,0% · κ 1,000 | 92,7% · κ 0,852 |

(As linhas "execução 2" são o arquivo `extra/rotulos_gabriel_execucao2_ia.csv`, que não ocupa slot.)

**Robustez: a execução 2 no lugar do slot `gabriel`** (mesmos `joao` e `marcela`):

| Dimensão | Fleiss (commitado) | Fleiss (execução 2) | Unânime (execução 2) | Landis & Koch (execução 2) |
|---|---:|---:|---:|---|
| `tipo_projeto` | 0,787 | 0,773 | 78,3% | substancial |
| `entrega_real` | 0,492 | 0,492 | 96,7% | moderada (instável) |
| `release_corretiva` | 0,625 | 0,635 | 73,0% | substancial |

O resultado quase não muda (diferença máxima de 0,014 no kappa; mesmas faixas de Landis & Koch).
Isso mostra estabilidade **entre execuções do mesmo modelo**, inclusive quando se troca a execução com
independência parcial (que conhecia a regra da heurística v1) por uma cega.

## 4. IA × as 150 linhas humanas de Marcela (única evidência humana)

Kappa de Cohen entre cada execução de IA e as 150 linhas humanas (30 repositórios em `tipo_projeto` e
`entrega_real`; 150 releases em `release_corretiva`). Comando:
`uv run python -m analises.auditoria_rotulos_ia ia-vs-humano`.

| Execução de IA | `release_corretiva` (N=150) | `tipo_projeto` (N=30) | `entrega_real` (N=30) |
|---|---|---|---|
| `joao` | 58,0% · κ 0,113 (leve) | 70,0% · κ 0,526 (moderada) | 96,7% · κ 0,000 |
| `gabriel` (commitado) | 58,7% · κ 0,129 (leve) | 70,0% · κ 0,514 (moderada) | 100,0% · κ indefinido |
| `gabriel` (execução 2) | 57,3% · κ 0,111 (leve) | 73,3% · κ 0,592 (moderada) | 100,0% · κ indefinido |

Detalhes que ajudam a ler a tabela:

* `entrega_real`: as 30 linhas humanas são todas `sim` (prevalência de 100%), então o kappa é 0 ou
  indefinido por construção; o que importa é a concordância bruta (96,7% a 100%), que nada diz sobre
  a capacidade de detectar `não`/`incerto`.
* `release_corretiva`: a humana marcou 60 `sim` e 90 `não`. Na `joao`, 29 dos 90 `não` viraram `sim`
  e 34 dos 60 `sim` viraram `não`. Os erros vão **nas duas direções** e a proporção de `sim` é parecida
  (55 da IA contra 60 humanos), então não é só um viés de prevalência: o julgamento por release difere
  release a release. (`gabriel`: 29 e 33.)
* `tipo_projeto`: 30 repositórios humanos (14 `aplicação/serviço`, 12 `ferramenta CLI`, 4
  `biblioteca/framework`; nenhum `outro`).
* Há uma única avaliadora humana: não dá para separar "a IA erra" de "Marcela interpreta de outro
  jeito" sem uma segunda pessoa.

## 5. Consenso automático (`validacao/consenso.csv`)

Comando: `uv run python -m analises.concordancia consenso --modo-automatico --origens --saida validacao/consenso.csv`.
O arquivo tem 300 linhas, as colunas de sempre, `*_origem`, `notas_consenso`, `consenso_modo =
automatico_maioria` e, por dimensão, `*_votos_ia` e `*_votos_humano` (3 votos por unidade; o voto humano
existe só nos 30 repositórios/150 releases de Marcela humana). `verificar-consenso` passa e lembra que o
arquivo foi gerado sem reunião. Unidades por caso (a ferramenta imprime linhas; aqui estão convertidas
em **unidades de análise**: repositório em `tipo_projeto`/`entrega_real`, release em `release_corretiva`):

| Dimensão | Unidades | Unânime (3-0) | Maioria (2-1) | Empate 1-1-1 (desempate automático) | Distribuição do consenso |
|---|---:|---:|---:|---:|---|
| `tipo_projeto` | 60 repos | 48 | 11 | 1 (→ `outro`) | 26 `aplicação/serviço`, 20 `ferramenta CLI`, 11 `biblioteca/framework`, 3 `outro` |
| `entrega_real` | 60 repos | 58 | 2 | 0 | 59 `sim`, 1 `não`, 0 `incerto` |
| `release_corretiva` | 300 releases | 217 | 83 | 0 (binária, não empata) | 127 `sim`, 173 `não` |

(Em linhas, como a ferramenta imprime: `tipo_projeto` 240/55/5, `entrega_real` 290/10/0,
`release_corretiva` 217/83/0.) O único empate é um repositório de `tipo_projeto` (5 linhas), resolvido
automaticamente como `outro` e anotado em `notas_consenso`.

Contra o voto humano: nas 150 releases humanas, o consenso (maioria com 2 IA) coincide com Marcela em
92 e a **supera** em 58; em `tipo_projeto` coincide em 21 dos 30 repositórios; em `entrega_real` em
30 de 30. Ou seja, o consenso automático **herda o viés da IA** onde a humana discorda (seção 4).

## 6. Interpretação honesta: o que se pode e o que não se pode afirmar

**Pode-se afirmar (com a ressalva de proveniência):**

* As execuções de IA do mesmo modelo são **consistentes entre si** (κ 0,79 em `tipo_projeto`, 0,63
  em `release_corretiva`; pares só de IA: κ 0,82 a 0,92 em `tipo_projeto` e 0,85 a 0,87 em
  `release_corretiva`), e trocar a execução do slot `gabriel` por outra quase não muda isso.
* O procedimento é reprodutível e os números das seções 2 a 5 saem das ferramentas versionadas e do script da seção 7.
* `entrega_real` é praticamente `sim` em tudo (59 de 60 no consenso): a dimensão quase não
  discrimina, e seu kappa não deve ser usado como evidência de qualidade.

**Não se pode afirmar:**

* Que "três avaliadores concordam" ou que o critério é confiável **entre pessoas**. O kappa mede
  consistência de um modelo consigo mesmo (erros correlacionados, tendendo a superestimar a
  confiabilidade) e, em um dos slots, com independência parcial.
* Que o consenso é uma "referência humana" ou um consenso deliberado: é maioria automática de rótulos
  majoritariamente de IA, sem reunião; só 1 dos 3 votos em 30 repositórios/150 releases é humano.
* Que a IA reproduz o julgamento humano. A única evidência humana (seção 4) aponta o contrário em
  `release_corretiva`: concordância de ≈58% e κ ≈ 0,11 a 0,13 (leve), contra ≈93% entre execuções de IA.
  Com N=30/150 e uma só pessoa, isso é um **sinal de alerta** e não uma estimativa precisa da validade.
* Qualquer coisa sobre a heurística: o F1 e demais métricas são do PR seguinte, com este consenso
  já mesclado.

**Para o artigo:** descrever os rótulos como "execuções de um modelo de linguagem, com 150 linhas de
uma avaliadora humana", nunca como "três avaliadores"; apresentar o kappa de Fleiss como
**consistência entre execuções do modelo**, ao lado do κ IA × humano e da concordância bruta;
declarar o desvio do protocolo (modo automático, sem reunião) e a independência parcial de
`rotulos_gabriel.csv`; tratar `entrega_real` pela concordância bruta e pela prevalência, não pelo kappa;
e, nas ameaças à validade, registrar o baixo acordo IA × humano em `release_corretiva`. Uma segunda
pessoa rotulando as mesmas 150 releases (e/ou substituir um slot, `protocolo_consenso.md` seção 7.3)
é o que permitiria afirmar algo sobre a ambiguidade humana do critério.

## 7. Reprodução

A partir de `lab03/` (com `UV_DEFAULT_INDEX` apontando para o PyPI público, se preciso):

```bash
uv sync
uv run python -m analises.concordancia validar --origens
uv run python -m analises.concordancia kappa --origens                     # seção 2
uv run python -m analises.auditoria_rotulos_ia confiabilidade              # gabriel x execução 2
uv run python -m analises.auditoria_rotulos_ia ia-vs-humano                # seção 4
uv run python -m analises.concordancia divergencias --origens             # pauta (12 / 2 / 83)
uv run python -m analises.concordancia consenso --modo-automatico --origens \
    --saida validacao/consenso.csv --forcar                                # seção 5 (regera o arquivo)
uv run python -m analises.concordancia verificar-consenso
```

Os kappas de pares, a robustez (execução 2) e a separação por origem em `marcela` (seções 2.2 e 3)
não têm subcomando próprio; saem deste script, que só usa funções já existentes (executar com
`uv run python script.py` ou colar em `uv run python -`):

```python
import itertools
import pandas as pd
from analises.auditoria_rotulos_ia import DEFAULT_INVALIDAS, comparar_rotulos
from analises.concordancia import DIMENSOES, calcular_kappa_matriz, carregar_csv, rotulos_por_unidade

V = "validacao"
planilha = carregar_csv("dados/amostra_ouro/amostra_ouro_template.csv")
rot = {s: carregar_csv(f"{V}/rotulos_{s}.csv") for s in ("joao", "gabriel", "marcela")}
rot["gabriel2"] = carregar_csv(f"{V}/extra/rotulos_gabriel_execucao2_ia.csv")
chave = lambda d: list(zip(d.repo_idx, d.release_idx))
invalidas = set(chave(carregar_csv(DEFAULT_INVALIDAS)))  # linhas de IA de marcela
eh_ia = pd.Series([k in invalidas for k in chave(rot["marcela"])], index=rot["marcela"].index)

def fleiss(slots, mascara=None):
    """Fleiss entre `slots`; `mascara` restringe às linhas de marcela humanas (False) ou de IA (True)."""
    sel = None if mascara is None else set(chave(rot["marcela"][eh_ia == mascara]))
    cortar = lambda d: d if sel is None else d[[k in sel for k in chave(d)]]
    for dim in DIMENSOES:
        m = rotulos_por_unidade({s: cortar(rot[s]) for s in slots}, dim, cortar(planilha))
        r = calcular_kappa_matriz(m, dim)
        print(f"  {dim.nome:<18}N={r.n_unidades:<4}kappa={r.kappa:.3f}  unânime={r.concordancia_unanime_pct:.1f}%  {r.interpretacao}")

print("Fleiss (joao, gabriel, marcela):"); fleiss(["joao", "gabriel", "marcela"])
print("Fleiss com a execução 2 no lugar de gabriel:"); fleiss(["joao", "gabriel2", "marcela"])
print("Fleiss só nas linhas em que marcela é HUMANA:"); fleiss(["joao", "gabriel", "marcela"], False)
print("Fleiss só nas linhas em que marcela é IA:"); fleiss(["joao", "gabriel", "marcela"], True)
for a, b in itertools.combinations(["joao", "gabriel", "marcela", "gabriel2"], 2):
    for c in comparar_rotulos(rot[a], rot[b]):
        k = "n/d" if c.kappa_cohen is None else f"{c.kappa_cohen:.3f}"
        print(f"{a} x {b}: {c.dimensao:<18}N={c.n:<4}{c.concordancia_pct:5.1f}%  kappa={k}")
```

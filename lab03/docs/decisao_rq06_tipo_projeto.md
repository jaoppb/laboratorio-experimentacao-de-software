# Decisão da RQ 06: usar o "tipo do projeto" como fator? (Issue #69)

**Natureza:** memorando de apoio à decisão. Ele reúne evidência e opções; **não decide pelo grupo**.
**Quem decide:** Marcela e Gabriel (conforme `docs/relatorio_sprint2_gabriel_assis.md`, pendência #69), com o João.
**Dados usados:** `validacao/rotulos_marcela.csv` (60 repositórios, **uma só avaliadora**, não é consenso),
`dados/repositorios.csv` (330 repositórios) e os Parquet de `releases/` e `runs/` persistidos na #56 (somente leitura).
**Reprodução:** seção 8 e Anexo A (todos os números abaixo saem dos scripts do anexo, sem rede).

> **Como ler os números.** Os rótulos de tipo são de uma avaliadora. O kappa de Fleiss ainda não existe
> (faltam `rotulos_joao.csv` e `rotulos_gabriel.csv`), então não sabemos quão confiável é a própria categoria.
> Toda "projeção para 330" supõe que os 60 sorteados (semente 42) representam os 330. A seção 2.2 testa isso.
> Deliberadamente **não olhamos o desempenho DORA por tipo**: escolher o fator depois de ver o resultado
> seria p-hacking e contaminaria a RQ 06.

## 1. A decisão

O guia pede, na RQ 06, **no mínimo três fatores** entre cinco: linguagem principal, popularidade (quartis de estrelas),
nº de contribuidores (quartis), idade (quartis) e **tipo do projeto**. O tipo só foi rotulado nos 60 repositórios da
amostra-ouro (planilha de 300 linhas = 60 × 5 releases; `tipo_projeto` é por repositório e se repete nas 5 linhas).
Os outros fatores existem nos 330. A Issue #69 propõe:

- **(a)** não usar o tipo;
- **(b)** rotular o tipo nos 330 (ou nos 270 restantes);
- **(c)** usar o tipo apenas com n = 60 e registrar a limitação como ameaça à validade.

Ponto de partida: **(a) já cumpre o mínimo do guia**, porque restam quatro fatores com n = 330 (linguagem, estrelas,
contribuidores, idade). A decisão, portanto, não é "se dá para fechar a RQ 06", e sim "se o grupo quer testar a
hipótese informal nº 4 do artigo" (aplicações/CLI entregam mais que bibliotecas; `artigo_contexto_e_hipoteses.md`).

## 2. Evidência comum às três opções

### 2.1 Tamanho dos grupos (rótulos da Marcela, n = 60)

| Categoria | n (de 60) | % | IC 95% (Wilson) | Projeção em 330 | IC da projeção |
|---|---:|---:|---|---:|---|
| aplicação/serviço | 39 | 65% | 52–76% | ~214 | 173–250 |
| ferramenta CLI | 14 | 23% | 14–35% | ~77 | 48–117 |
| biblioteca/framework | **7** | 12% | 6–22% | ~38 | 19–73 |
| outro | 0 | 0% | n/d | n/d | n/d |

A categoria `outro` não foi usada. Ela existe na planilha; em 330 repositórios provavelmente aparecerá, e será preciso
decidir se entra como grupo, se é fundida a uma vizinha ou se é excluída.

Casos de fronteira entre categorias nos 60 rótulos atuais (observação do memorando, não correção): `psf/requests` e
`vadimdemedes/ink` constam como aplicação/serviço, embora sejam bibliotecas; `electron/electron` e `evanw/esbuild`
também são discutíveis (framework/ferramenta). Se o desacordo for frequente no consenso (#65), o fator fica pouco
confiável em qualquer das opções, e é um risco por si só.

### 2.2 Os 60 representam os 330?

Comparação por Mann-Whitney entre os 60 e os 270 restantes (p ≥ 0,05 em todas; não rejeita "mesma distribuição",
mas com n = 60 o teste também tem pouco poder):

| Variável | Mediana (60) | Mediana (270) | p |
|---|---:|---:|---:|
| estrelas | 61.280 | 58.670 | 0,86 |
| contribuidores | 379,5 | 466 | 0,24 |
| releases na janela | 24,5 | 26,5 | 0,94 |
| deployment frequency | 0,470 | 0,509 | 0,94 |
| CFR (a) | 0,038 | 0,049 | 0,22 |

Linguagens dos 60: TypeScript 18, Rust 10, Python 8, Go 8, C++ 5, JavaScript 4. Nos 330: TypeScript 93, Python 76,
Go 37, Rust 34, JavaScript 28, C++ 16. Rust está sobre-representado nos 60 (17% contra 10%). Sem evidência forte de viés
nas variáveis numéricas.

### 2.3 Poder estatístico: o que cada tamanho consegue detectar

Simulação de Monte Carlo (semente 42; dados normais com deslocamento de média; 80% de poder), no `scipy.stats`.
O ε² do Kruskal-Wallis é aproximado por f²/(1+f²). Os dois níveis de α são: 0,05 sem correção e 0,05/12 (primeiro passo
de Holm com 12 testes = 3 fatores × 4 métricas; com 4 fatores seriam 16 testes e o corte ficaria ainda mais rigoroso).

| Cenário (grupos) | Menor efeito detectável, α = 0,05 | Menor efeito detectável, α = 0,05/12 |
|---|---|---|
| **n = 60**, 3 categorias (39/14/7) | f = 0,43 (ε² ≈ 0,16) | f = 0,58 (ε² ≈ 0,25) |
| **n = 330**, 3 categorias (214/77/38) | f = 0,18 (ε² ≈ 0,03) | f = 0,23 (ε² ≈ 0,05) |
| referência: quartis, n = 330 (4 × ~82) | f = 0,19 (ε² ≈ 0,03) | f = 0,24 (ε² ≈ 0,06) |

Comparações de pares (Mann-Whitney), menor |Cliff's δ| detectável com 80% de poder (limiar de "grande" em Romano et al.
é |δ| ≥ 0,474):

| Par | n = 60: α 0,05 / 0,05/12 | n = 330: α 0,05 / 0,05/12 |
|---|---|---|
| aplicação × CLI | 0,48 / 0,63 | 0,22 / 0,28 |
| aplicação × biblioteca | 0,61 / 0,77 | 0,28 / 0,37 |
| CLI × biblioteca | **0,68 / 0,86** | 0,31 / 0,41 |
| aplicação × (CLI + biblioteca), binário | 0,42 / 0,56 | 0,18 / 0,24 |

Leitura: com n = 60 só efeitos **grandes** (ε² ≳ 0,16; δ ≳ 0,5–0,9 conforme o par) seriam detectáveis, e qualquer
comparação que envolva as 7 bibliotecas é praticamente cega a efeitos pequenos e médios. Com n = 330 o fator tipo teria
poder equivalente ao dos fatores em quartis.

### 2.4 Um proxy automático ajuda a pré-preencher o tipo? (evidência, não rótulo)

Testamos, **só com dados já presentes no dataset** (linguagem, tokens do nome do repositório, nomes dos workflows e
prefixos das tags), contra os 60 rótulos da Marcela, com validação leave-one-out:

| Método | Acerto | κ vs rótulo | F1 macro |
|---|---:|---:|---:|
| sempre "aplicação/serviço" (linha de base) | 0,65 | 0,00 | 0,26 |
| regras fixas por palavra-chave | 0,58 | 0,04 | 0,37 |
| TF-IDF + regressão logística (LOO) | 0,57 | 0,15 | 0,47 |

Nenhum supera a linha de base em acerto, e os κ são desprezíveis. **Conclusão da evidência:** os dados do dataset atual
não bastam para inferir o tipo. Não avaliamos tópicos do GitHub, descrição e README (não estão no dataset e exigiriam
rede e token); eles seriam o próximo candidato, mas com 7 bibliotecas não há exemplos suficientes para calibrar de forma
confiável. Há ainda um risco metodológico: o guia pede rotulação independente e sem ver a saída automática; mostrar um
palpite pré-preenchido pode ancorar os avaliadores. Por isso o proxy aparece aqui apenas como evidência.

## 3. Opção (a): não usar o tipo

- **Esforço:** ~0 h de rotulação extra (os 60 rótulos continuam úteis para a validação da heurística e para descrever a
  amostra). ~0,5–1 h para ajustar texto (hipótese 4 do artigo, metodologia, lista de fatores).
- **Estatística:** RQ 06 com linguagem, estrelas, contribuidores e idade, todos com n = 330. Até 16 testes
  (4 fatores × 4 métricas) ou 12 se o grupo escolher só três fatores. Linguagem tem 23 categorias (12 delas têm ≤ 2
  repositórios), então precisa ser agrupada (por exemplo, as 6 maiores + "outras"), o que é uma decisão adicional.
  Poder equivalente ao da tabela 2.3 (n = 330).
- **Riscos:** perde-se a única hipótese baseada em natureza do artefato (biblioteca × aplicação). Nenhum risco de
  qualidade de rótulo.
- **O que muda no texto:** remover o tipo da lista de fatores (Metodologia, análise estatística), da hipótese nº 4 em
  `artigo_contexto_e_hipoteses.md` (ou marcá-la como "não testada") e da tabela de rótulos que ainda mencionar o uso do
  tipo na RQ 06. Em ameaças à validade, citar apenas que a natureza do projeto não foi controlada.

## 4. Opção (b): rotular o tipo nos 330

O tipo é uma única dimensão por repositório (sem ler *release notes*). **As estimativas de tempo abaixo são
premissas, não medições**; não há medida de tempo da rotulação no repositório. Premissa: 2–3 min por repositório
(abrir o README e a página inicial), ou seja, 270 repositórios novos.

| Variante | Quem rotula | Esforço estimado | Observação |
|---|---|---|---|
| b1 | 1 pessoa nos 270 restantes + 2ª pessoa em ~10% (27 repos) para estimar concordância | 9–14 h + 1–1,5 h | ~3–5 h por pessoa se dividido em 3 |
| b2 | 2 pessoas independentes nos 270 + consenso nos desacordos | 18–27 h + reunião | Dá kappa de Cohen nos 270 |
| b3 | as 3 pessoas independentes nos 270 + consenso | 27–41 h + reunião | Dá Fleiss nos 330, mesmo padrão da amostra-ouro |

- **Estatística:** n = 330; grupos projetados 214/77/38 (IC das projeções na tabela 2.1). Mesmo poder que um fator em
  quartis (tabela 2.3). Com 38 bibliotecas, comparações de pares com essa categoria ainda detectam só δ ≳ 0,3–0,4.
- **Riscos:** (i) carga da sprint, como a própria Issue #69 avisa; (ii) qualidade do rótulo: com uma só pessoa (b1)
  não há como medir confiabilidade nos 270; (iii) categoria `outro` e casos de fronteira (seção 2.1); (iv) rotulador
  único introduz viés sistemático que não aparece no kappa dos 60; (v) a análise passa a depender de um trabalho manual
  que o grupo replicador precisará refazer ou herdar.
- **O que muda no texto:** descrever o protocolo de rotulação do tipo em 330 repositórios (quem, critérios, concordância),
  manter a hipótese 4 e acrescentar a medida de confiabilidade (kappa) ao texto da validação manual.

## 5. Opção (c): usar o tipo com n = 60 e registrar como ameaça

- **Esforço:** ~0 h de rotulação extra. ~1–2 h para a análise (Kruskal-Wallis e Mann-Whitney sobre os 60) e para o texto
  da ameaça.
- **Estatística:** 39/14/7. Só detecta efeitos grandes (tabela 2.3). Comparações com as 7 bibliotecas são frágeis
  (δ mínimo 0,68–0,86 contra a CLI). Resultado "não significativo" **não** é evidência de ausência de efeito.
  Há duas formas de tratar a correção de Holm: incluir os 4 testes do tipo na mesma família (aumenta o rigor sobre os
  demais fatores) ou reportá-los como família exploratória separada, declarada como tal. A segunda é mais honesta quanto
  ao poder, mas precisa ser fixada **antes** de ver os resultados.
- **Riscos:** conclusões instáveis por n pequeno; risco de falso negativo (poder baixo) ou de efeito inflado quando algo
  sai significativo; os 60 foram sorteados para a validação da heurística, não para a RQ 06 (seção 2.2: sem sinal forte
  de viés nas variáveis numéricas, mas pouco poder para detectá-lo); tamanho desigual entre fatores (60 × 330) dificulta
  comparar efeitos.
- **O que muda no texto:** descrever o tipo como fator **restrito à subamostra**, com n por categoria, a escolha do tratamento
  de Holm, e uma ameaça de validade estatística ("baixo poder e cobertura de 18% da amostra"). Rotular a análise como
  exploratória.

## 6. Comparação neutra

| Critério | (a) não usar | (b) rotular nos 330 | (c) n = 60 + ameaça |
|---|---|---|---|
| Rotulação extra | 0 h | 9–41 h (b1–b3, premissa) | 0 h |
| Esforço total estimado | ~1 h | 10–42 h | ~2 h |
| n da análise do tipo | n/a | 330 (214/77/38 projetado) | 60 (39/14/7) |
| Menor efeito detectável (3 grupos, α 0,05) | n/a | ε² ≈ 0,03 | ε² ≈ 0,16 |
| Comparações com bibliotecas | n/a | δ ≳ 0,3–0,4 | δ ≳ 0,6–0,9 |
| Testa a hipótese nº 4 | não | sim | só efeitos grandes |
| Cumpre o mínimo de 3 fatores do guia | sim (4 fatores) | sim (5) | sim (5), com ressalva de poder |
| Risco de rótulo ruidoso | nenhum | médio-alto (depende da variante) | médio (1 avaliadora hoje) |
| Carga na sprint | nenhuma | alta | baixa |
| Texto a alterar | hipótese 4 e lista de fatores | protocolo de rotulação | ameaça + fator restrito |

## 7. Recomendação

**Sugestão (não é decisão do memorando):** adotar **(a) como análise confirmatória** da RQ 06 (linguagem, estrelas,
contribuidores e idade, todos com n = 330), e **reportar o tipo apenas de forma descritiva e exploratória nos 60**, fora
da correção de Holm e sem inferência (por exemplo, medianas e n por categoria), declarando a limitação. Isso preserva o
mínimo do guia, não gasta horas de rotulação e evita um teste com poder insuficiente que o artigo teria de interpretar.
Se o grupo considerar a hipótese nº 4 importante e tiver ~10–14 h livres, **(b1)** é o melhor custo-benefício: um
rotulador nos 270 restantes mais conferência cruzada em ~10%, com kappa reportado. O proxy automático (seção 2.4) não
justifica pré-preencher o tipo.

**Decisões que sobram para o grupo:** (1) A e/ou C ou B; (2) se (b), a variante e quem rotula; (3) como agrupar a
linguagem (23 categorias); (4) tratamento do `outro`; (5) tratamento de Holm para os testes do tipo, se existirem.

## 8. Como reproduzir

Pré-requisitos: ambiente `uv` do `lab03/`; os Parquet de `releases/` e `runs/` da #56 (não versionados) em uma pasta
local. O diretório `lab03/cache/` é ignorado pelo Git.

```bash
cd lab03 && uv sync
DADOS_56=<caminho>/lab03/dados          # onde estão releases/ e runs/ da #56 (somente leitura)
mkdir -p cache/issue69 && cp -R "$DADOS_56"/{releases,runs,repositorios.csv,repositorios.parquet,funil.csv} cache/issue69/

# extrai os scripts dos anexos deste memorando e do memorando de limitações para cache/issue69/scripts/
python3 - <<'PY'
import pathlib, re
saida = pathlib.Path("cache/issue69/scripts"); saida.mkdir(parents=True, exist_ok=True)
for doc in ("docs/decisao_rq06_tipo_projeto.md", "docs/impacto_limitacoes_conhecidas.md"):
    for nome, corpo in re.findall(r"```python\n# arquivo: (\S+)\n(.*?)```", pathlib.Path(doc).read_text(encoding="utf-8"), re.S):
        (saida / nome).write_text(corpo, encoding="utf-8")
PY

PYTHONPATH=. uv run python cache/issue69/scripts/rq06_grupos_poder.py   # seções 2.1-2.3 (~25 s)
PYTHONPATH=. uv run python cache/issue69/scripts/rq06_proxy.py          # seção 2.4
```

Os scripts só leem arquivos locais, não usam rede nem alteram dados versionados. As simulações usam semente 42; valores
de poder podem variar na 2ª casa decimal com outra versão do numpy/scipy.

---

## Anexo A: scripts

### A.1 Grupos, representatividade e poder

```python
# arquivo: rq06_grupos_poder.py
"""RQ 06: tamanhos de grupo por tipo de projeto, poder dos testes e proxy automático (evidência, não rótulos).

Uso (de dentro de lab03/):  PYTHONPATH=. uv run python cache/issue69/scripts/rq06_grupos_poder.py
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

RNG = np.random.default_rng(42)
m = pd.read_csv("validacao/rotulos_marcela.csv", encoding="utf-8-sig")
tipo = m.groupby("repo_name").tipo_projeto.first()          # 1 linha por repositório (n = 60)
cat = tipo.value_counts()
N = 330

print("== 1. Grupos nos 60 repositórios rotulados (rótulos de UMA avaliadora; não é consenso) ==")
for k, v in cat.items():
    lo, hi = proportion_confint(v, len(tipo), alpha=0.05, method="wilson")
    print(f"{k}: n={v} ({100*v/len(tipo):.0f}%) IC95% Wilson {100*lo:.0f}-{100*hi:.0f}% "
          f"-> projeção em {N}: ~{round(N*v/len(tipo))} (IC {round(N*lo)}-{round(N*hi)})")
print("categoria 'outro' usada:", int((tipo == "outro").sum()))

print("\n== 2. Os 60 representam os 330? (fatores numéricos e linguagem) ==")
r = pd.read_csv("cache/issue69/repositorios.csv")
amostra = r[r.full_name.isin(tipo.index)]
for col in ("stars", "contributors_count", "releases_count_window", "deployment_frequency", "cfr_a"):
    u = stats.mannwhitneyu(amostra[col], r[~r.full_name.isin(tipo.index)][col])
    print(f"{col}: mediana 60={amostra[col].median():.4g} x 270={r[~r.full_name.isin(tipo.index)][col].median():.4g} "
          f"(Mann-Whitney p={u.pvalue:.2f})")
print("linguagens (60):", amostra.language.value_counts().head(6).to_dict())
print("linguagens (330):", r.language.value_counts().head(6).to_dict())


def poder_kw(tamanhos, f, alpha, sims=4000):
    """Poder do Kruskal-Wallis com dados normais e médias espaçadas (-1, 0, +1 escalonadas) para um f de Cohen."""
    k = len(tamanhos)
    n = np.array(tamanhos)
    mu = np.linspace(-1, 1, k)
    mu = mu - np.average(mu, weights=n)
    f0 = np.sqrt(np.average(mu ** 2, weights=n))
    mu = mu * (f / f0)
    ok = 0
    for _ in range(sims):
        amostras = [RNG.normal(mu[i], 1, n[i]) for i in range(k)]
        ok += stats.kruskal(*amostras).pvalue < alpha
    return ok / sims


def f_para_poder(tamanhos, alpha, alvo=0.80):
    lo, hi = 0.02, 1.5
    for _ in range(10):
        mid = (lo + hi) / 2
        if poder_kw(tamanhos, mid, alpha, sims=800) < alvo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


print("\n== 3. Menor efeito detectável (poder 80%) — Kruskal-Wallis, normal com deslocamento de média ==")
cenarios = {
    "(c) n=60 reais (39/14/7)": [int(cat.get("aplicação/serviço", 0)), int(cat.get("ferramenta CLI", 0)), int(cat.get("biblioteca/framework", 0))],
    "(b) n=330 projetado (214/77/38)": [round(N * v / len(tipo)) for v in (39, 14, 7)],
    "referência: fator em quartis, n=330 (4x~82)": [83, 83, 82, 82],
}
for nome, tam in cenarios.items():
    linha = [nome, str(tam)]
    for alpha, rot in ((0.05, "α=0,05 sem correção"), (0.05 / 12, "α=0,05/12 (Holm, pior caso de 12 testes)")):
        f = f_para_poder(tam, alpha)
        eps2 = f ** 2 / (1 + f ** 2)
        linha.append(f"{rot}: f={f:.2f} ε²≈{eps2:.3f}")
    print(" | ".join(linha))

print("\n== 4. Menor Cliff's δ detectável por Mann-Whitney (poder 80%, α=0,05 e 0,05/12) ==")


def delta_min(n1, n2, alpha, alvo=0.8, sims=1500):
    lo, hi = 0.0, 3.0
    for _ in range(10):
        d = (lo + hi) / 2
        ok = sum(stats.mannwhitneyu(RNG.normal(d, 1, n1), RNG.normal(0, 1, n2)).pvalue < alpha for _ in range(sims // 3))
        (lo, hi) = (d, hi) if ok / (sims // 3) < alvo else (lo, d)
    d = (lo + hi) / 2
    return 2 * stats.norm.cdf(d / np.sqrt(2)) - 1


for nome, (a, b) in {"n=60: CLI(14) x biblioteca(7)": (14, 7), "n=60: aplicação(39) x biblioteca(7)": (39, 7),
                     "n=60: aplicação(39) x CLI(14)": (39, 14), "n=330: aplicação(214) x CLI(77)": (214, 77),
                     "n=330: CLI(77) x biblioteca(38)": (77, 38),
                     "n=330: aplicação(214) x biblioteca(38)": (214, 38)}.items():
    print(f"{nome}: δ mínimo ≈ {delta_min(a, b, 0.05):.2f} (α=0,05) | {delta_min(a, b, 0.05/12):.2f} (α=0,05/12)  "
          f"[|δ|>=0,474 é 'grande' em Romano et al.]")

print("\n== 5. Variante binária (aplicação x não-aplicação), n=60 e n=330 ==")
print(f"n=60: aplicação(39) x CLI+biblioteca(21): δ mínimo ≈ {delta_min(39, 21, 0.05):.2f} (α=0,05) | {delta_min(39, 21, 0.05/12):.2f} (α=0,05/12)")
print(f"n=330: aplicação(214) x CLI+biblioteca(116): δ mínimo ≈ {delta_min(214, 116, 0.05):.2f} (α=0,05) | {delta_min(214, 116, 0.05/12):.2f} (α=0,05/12)")
```

### A.2 Proxy automático do tipo

```python
# arquivo: rq06_proxy.py
"""RQ 06: proxy automático barato para pré-preencher o tipo do projeto (apenas evidência, NÃO são rótulos).

Só usa o que já está no dataset persistido (sem rede): nome do repositório, linguagem principal, nomes dos
workflows (dos runs) e prefixo das tags de release. Tópicos, descrição e README do GitHub NÃO estão no dataset.
Compara com os 60 rótulos de uma avaliadora (Marcela), com validação leave-one-out.

Uso (de dentro de lab03/):  PYTHONPATH=. uv run python cache/issue69/scripts/rq06_proxy.py
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline

D = Path("cache/issue69")
tipo = pd.read_csv("validacao/rotulos_marcela.csv", encoding="utf-8-sig").groupby("repo_name").tipo_projeto.first()
r = pd.read_csv(D / "repositorios.csv").set_index("full_name")


def tokens(s: str) -> list[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t and not t.isdigit()]


def texto(full_name: str) -> str:
    owner, nome = full_name.split("/")
    wf = pq.read_table(D / "runs" / f"{full_name.replace('/', '__')}.parquet", columns=["name"]).to_pandas().name.dropna()
    wf = " ".join(wf.drop_duplicates().tolist()[:40])
    tags = pq.read_table(D / "releases" / f"{full_name.replace('/', '__')}.parquet", columns=["tag_name"]).to_pandas().tag_name
    prefixos = " ".join(sorted({"tagprefix_" + re.sub(r"[\d.]+.*$", "", t).strip("-_@v") for t in tags[:200]}))
    return " ".join(["lang_" + str(r.loc[full_name, "language"]).replace("+", "p").replace("#", "s")]
                    + ["nome_" + t for t in tokens(nome)] + tokens(wf) + tokens(prefixos))


def regras(txt: str) -> str:
    """Regras escritas ANTES de ver os rótulos: palavras-chave por classe; empate -> classe majoritária."""
    t = set(txt.split())
    cli = len(t & {"nome_cli", "nome_cmd", "nome_tool", "nome_codex", "goreleaser", "cargo", "dist", "homebrew", "brew"})
    lib = len(t & {"nome_lib", "nome_core", "nome_js", "nome_ui", "pypi", "npm", "crates", "docs", "storybook", "typecheck", "type"})
    app = len(t & {"docker", "image", "deploy", "helm", "kubernetes", "container", "ghcr", "compose", "e2e", "frontend", "backend"})
    best = max((app, "aplicação/serviço"), (cli, "ferramenta CLI"), (lib, "biblioteca/framework"), key=lambda x: x[0])
    return best[1] if best[0] > 0 else "aplicação/serviço"


X = [texto(n) for n in tipo.index]
y = tipo.to_numpy()
classes = ["aplicação/serviço", "ferramenta CLI", "biblioteca/framework"]
print("n =", len(y), "| distribuição:", pd.Series(y).value_counts().to_dict())
maj = pd.Series(y).value_counts().idxmax()


def relata(nome, pred):
    print(f"{nome}: acerto={accuracy_score(y, pred):.2f} | κ vs rótulo={cohen_kappa_score(y, pred):.2f} | "
          f"F1 macro={f1_score(y, pred, average='macro', labels=classes, zero_division=0):.2f}")
    print(pd.DataFrame(confusion_matrix(y, pred, labels=classes), index=[f"rótulo:{c}" for c in classes],
                       columns=[f"prev:{c}" for c in classes]).to_string())


relata("Linha de base (sempre a classe majoritária)", np.array([maj] * len(y)))
relata("Regras fixas por palavra-chave", np.array([regras(t) for t in X]))
modelo = make_pipeline(TfidfVectorizer(token_pattern=r"\S+", min_df=2, sublinear_tf=True),
                       LogisticRegression(C=3.0, max_iter=2000, class_weight="balanced"))
relata("TF-IDF + regressão logística (leave-one-out)", cross_val_predict(modelo, X, y, cv=LeaveOneOut()))
print("\nObs.: n=60 e 7 bibliotecas -> as estimativas são ruidosas; os rótulos de referência são de uma única avaliadora.")
```

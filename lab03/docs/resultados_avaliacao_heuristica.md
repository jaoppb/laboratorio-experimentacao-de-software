# Resultados da avaliação da heurística de release corretiva (Issue #62)

**Código:** `analises/avaliar_heuristica.py` (sem alterações neste PR) · **Heurísticas:** `metricas/cfr_b.py` (`v1`, `v1_full_message`; `DEFAULT_HEURISTIC = "v1"`, inalterado)
**Protocolo e ferramenta:** [`avaliacao_heuristica.md`](./avaliacao_heuristica.md) · **Referência:** `validacao/consenso.csv` (Issue #65, commit `76ff38b`)
**Proveniência dos rótulos:** [`../validacao/PROVENIENCIA.md`](../validacao/PROVENIENCIA.md) · **Concordância:** [`resultados_concordancia.md`](./resultados_concordancia.md)
**Saídas versionadas:** [`../dados/analises/avaliacao_heuristica/`](../dados/analises/avaliacao_heuristica/) (`aval_*.md` e `erros_*.csv`)
**Execução:** 21/10/2026, a partir do commit `11a80a5` (rótulos e consenso já versionados, como o protocolo exige).

> **Leia isto primeiro.** A "referência" desta avaliação **não é um consenso de pessoas**. O `consenso.csv` é a
> **maioria automática de três rótulos majoritariamente de IA** (`joao` e `gabriel` são execuções do mesmo modelo,
> `claude-opus-5.5`; `marcela` mistura 150 linhas humanas e 150 de IA), **sem reunião de consenso**. A **única evidência
> humana** são as 150 linhas (30 repositórios) rotuladas por Marcela. Ver `PROVENIENCIA.md` e
> `resultados_concordancia.md`. Os números abaixo medem a concordância da heurística com **esse** consenso, e com o rótulo
> humano quando indicado; não é a concordância "com o julgamento humano" em geral.

## 1. Resultado em uma frase

**Nenhuma versão atinge F1 ≥ 0,70 em nenhuma das cinco referências testadas.** Pela regra de decisão
(`avaliacao_heuristica.md`, seção 4), a versão final **não está definida** e o passo seguinte é a `heuristic_v2`
(escrita por Gabriel, **não** por este PR), com a ressalva de sobreajuste da seção 6. `DEFAULT_HEURISTIC` continua `v1`.

## 2. Dados e método

* **Releases e commits:** `uv run python -m analises.persistir_amostra_ouro` persistiu as releases dos 60 repositórios
  sorteados em `dados/releases/` (não versionado), **com a mensagem completa dos commits**
  (528.126 de 528.127 commits têm `full_message`). `v1_full_message` só difere de `v1` com esse dado.
* **Classe positiva:** `sim` (release corretiva). Métricas de `precision_recall_fscore_support`; matriz de confusão
  VP/FP/FN/VN em relação ao rótulo da referência (a heurística diz "corretiva" = positivo).
* **Exclusões** (iguais para as duas versões): 2 de 300 releases, ambas `status != ok (first_release)`:
  `paperclipai/paperclip v0.3.0` e `career-ops-hq/career-ops v1.2.0`. Não há exclusão por arquivo ausente, tag ausente ou
  `previous_release` nulo. Em cada recorte, "N excl." é a parte dessas 2 que cai no recorte.
* **Referências avaliadas** (a ferramenta lê qualquer CSV no formato do consenso em `--consenso`; os recortes são gerados
  pelo script da seção 8):

| Sigla | Referência | Releases | O que representa |
|---|---|---:|---|
| (a) | `consenso.csv` inteiro | 300 | Janela padrão do protocolo. Consenso automático, maioria IA. |
| (b1) | **Rótulo humano de Marcela** nas suas 150 linhas | 150 (30 repositórios) | **Referência só-humana**: uma pessoa, sem consenso. Evidência mais forte de validade, amostra pequena. |
| (b2) | Consenso nas mesmas 150 linhas | 150 | Mesmas releases de (b1), mas com o rótulo do consenso (que supera Marcela em 58 delas). |
| (c) | Linhas em que os três votos coincidiram | 217 | Menos ambiguidade de rótulo; o recorte é escolhido pela concordância dos avaliadores. |
| (d) | Linhas sem voto humano (3 votos de IA) | 150 | Complemento de (b): onde a referência é só IA. Não foi pedido; entra para isolar o efeito do avaliador. |

## 3. Resultados

F1 "tudo corretiva" é o F1 de um classificador trivial que marca **todas** as releases como corretivas
(precisão = prevalência, recall = 1); serve de piso. IC95% é bootstrap por repositório (2.000 reamostragens, semente 0;
seção 8): as releases de um repositório não são independentes.

| Ref. | Versão | Precisão | Recall | F1 | IC95% do F1 | F1 "tudo corretiva" | N aval. | N excl. | VP | FP | FN | VN | F1 ≥ 0,70 |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| (a) 300 | `v1` | 0,614 | 0,638 | **0,625** | 0,519 a 0,717 | 0,598 | 298 | 2 | 81 | 51 | 46 | 120 | **não** |
| (a) 300 | `v1_full_message` | 0,599 | 0,646 | **0,621** | 0,519 a 0,706 | 0,598 | 298 | 2 | 82 | 55 | 45 | 116 | **não** |
| (b1) humano | `v1` | 0,441 | 0,433 | **0,437** | 0,336 a 0,526 | 0,574 | 149 | 1 | 26 | 33 | 34 | 56 | **não** |
| (b1) humano | `v1_full_message` | 0,435 | 0,450 | **0,443** | 0,345 a 0,538 | 0,574 | 149 | 1 | 27 | 35 | 33 | 54 | **não** |
| (b2) consenso nas linhas humanas | `v1` | 0,627 | 0,712 | **0,667** | 0,532 a 0,769 | 0,517 | 149 | 1 | 37 | 22 | 15 | 75 | **não** |
| (b2) consenso nas linhas humanas | `v1_full_message` | 0,613 | 0,731 | **0,667** | 0,527 a 0,774 | 0,517 | 149 | 1 | 38 | 24 | 14 | 73 | **não** |
| (c) unânimes | `v1` | 0,624 | 0,685 | **0,653** | 0,541 a 0,754 | 0,599 | 215 | 2 | 63 | 38 | 29 | 85 | **não** |
| (c) unânimes | `v1_full_message` | 0,610 | 0,696 | **0,650** | 0,540 a 0,752 | 0,599 | 215 | 2 | 64 | 41 | 28 | 82 | **não** |
| (d) só IA | `v1` | 0,603 | 0,587 | **0,595** | 0,433 a 0,731 | 0,670 | 149 | 1 | 44 | 29 | 31 | 45 | **não** |
| (d) só IA | `v1_full_message` | 0,587 | 0,587 | **0,587** | 0,434 a 0,716 | 0,670 | 149 | 1 | 44 | 31 | 31 | 43 | **não** |

Leitura:

* **Todas as células ficam abaixo de 0,70** (máximo: 0,667). O consenso inteiro (a) dá 0,625 / 0,621, bem perto do piso
  "tudo corretiva" (0,598): na amostra completa a regra pouco melhora sobre marcar tudo. O limite superior do IC95% de
  (a) (0,717 e 0,706) toca 0,70, então a amostra sozinha não exclui estatisticamente uma versão em 0,70; mas o ponto
  estimado está abaixo e a referência humana (b1) está claramente abaixo.
* **A referência decide o resultado.** O mesmo `v1` vai de 0,437 (rótulo humano de Marcela) a 0,667 (consenso nas mesmas
  150 releases). A diferença entre (b1) e (b2) é **só o rótulo**: as releases, os commits e a heurística são idênticos.
  Isso é a discordância IA × humana (`resultados_concordancia.md`, seções 4 e 5: o consenso coincide com Marcela em 92 das
  150; κ entre IA e humana ≈ 0,11 a 0,13) aparecendo no F1.
* Em (b1) o F1 (0,437) fica **abaixo** de marcar tudo como corretiva (0,574). Contra o rótulo humano a heurística não
  agrega nada sobre o acaso informado pela prevalência (40% corretivas).
* **`v1` e `v1_full_message` são praticamente equivalentes**: a mensagem completa muda a decisão em 5 de 298 releases
  (`winutil 25.12.18`, `cline v3.56.1`, `headscale v0.29.1`, `cc-switch v3.5.1`, `svelte@5.41.3`; uma vira VP e quatro
  viram FP em (a)). F1 em (a): 0,625 contra 0,621. A diferença é menor que qualquer incerteza amostral; **não há base
  para preferir uma à outra por F1**, e a `v1` é a mais simples.
* Efeito de independência: o slot `gabriel` conhecia a regra da `v1` (`PROVENIENCIA.md`), o que **só pode inflar** o F1
  nas referências com esse voto; mesmo assim nenhuma chega a 0,70.

## 4. Análise de erros

Listas completas em `dados/analises/avaliacao_heuristica/erros_todas.csv` (197 erros: FP e FN das duas versões, com
`mensagens_fix` e `release_url`) e `erros_humano_marcela.csv`. Os exemplos abaixo **ilustram** padrões; as regras gerais são
as colunas "padrão", não os casos.

A `v1` combina dois critérios: (i) só o patch da tag sobe em relação à `previous_release` e (ii) algum commit cita
`revert/hotfix/fix`. Para ver qual falha, a tabela cruza a relação entre as duas tags com o resultado
(`v1`, referência (a), 298 releases; script da seção 8):

| Relação entre `previous_release` e a tag | N | Corretivas no consenso | VP | FP | FN | VN |
|---|---:|---:|---:|---:|---:|---:|
| patch sobe (`1.2.3 → 1.2.4`) | 143 | 78 (55%) | 72 | **50** | 6 | 15 |
| minor sobe (`1.2.x → 1.3.0`) | 95 | 14 (15%) | 0 | 0 | **14** | 81 |
| major sobe | 14 | 5 (36%) | 0 | 0 | 5 | 9 |
| **retrocesso** (a tag tem versão menor que a anterior) | 15 | **13 (87%)** | 0 | 0 | **13** | 2 |
| outro pacote (prefixo da tag diferente) | 17 | 7 (41%) | 1 | 0 | 6 | 10 |
| fora de SemVer | 9 | 8 (89%) | 8 | 1 | 0 | 0 |
| mesma versão (sufixo, pré-release) | 5 | 2 (40%) | 0 | 0 | 2 | 3 |

### 4.1 Falsos negativos (46 em (a), `v1`)

Padrões gerais, em ordem de peso. 36 dos 46 FN **têm** commit com palavra-chave de correção: a falha é do critério de
versão, não de vocabulário.

1. **Releases de manutenção/backport em linhas paralelas (13 FN).** Quando o projeto publica correções para uma linha
   antiga (`v8.0.5` seguido de `v7.3.2`; `v42.9.2` seguido de `v41.10.6`; `n8n@2.26.7` seguido de `n8n@1.123.59`), a
   `previous_release` é a anterior **no tempo**, não na mesma linha. A versão "diminui" e o critério "só o patch sobe" é
   falso, embora esse seja justamente o padrão de release corretiva (87% das 15 releases assim são corretivas no consenso).
2. **Várias linhas ou pacotes no mesmo repositório (6 FN em "outro pacote" + 5 em "major sobe").** Em monorepos ou
   repositórios com mais de uma linha de produto, a tag anterior pode ser de **outro componente** (`skill-v3.7.1` seguido
   de `cli-v3.0.3`; `v8.2.1` seguido de `plugin-legacy@8.2.3`). Comparar números de versão entre componentes diferentes não
   tem significado.
3. **Releases *minor* com muitas correções (14 FN).** Há projetos que entregam correção junto de uma versão minor
   (`v6.18.2 → v6.19.0`, `v7.4.14 → v7.5.5`). O critério de versão descarta todas, mas a taxa corretiva de "minor sobe" é
   só 15%, então a regra acerta 81 de 95; é um custo de precisão inevitável de qualquer critério só por número de versão.
4. **Patch sem palavra-chave (6 FN em "patch sobe").** `v0.29.0 → v0.29.1` com um único commit sem "fix" no assunto, ou
   poucas mensagens genéricas. O vocabulário `revert/hotfix/fix` não cobre todas as correções (a mensagem completa
   resgata só 1 desses casos, `headscale v0.29.1`).
5. **Versionamento por data (2 FN, ambos de `yt-dlp`: `2025.10.14 → 2025.10.22` e `2026.02.21 → 2026.03.03`).** O número que
   a leitura SemVer chama de "patch" ou "minor" é dia ou mês; o critério de versão não se aplica (um cai em "patch sobe" e
   o outro em "minor sobe" na tabela acima, por isso não somam à parte).

### 4.2 Falsos positivos (51 em (a), `v1`; 28 dos 60 repositórios)

Todos os FP, menos 1, estão em "patch sobe": **a regra "patch + alguma palavra de correção" é permissiva demais**. Padrões:

1. **Releases de patch de cadência alta que reúnem funcionalidade e correção (a maior fonte).** Em projetos que publicam
   um patch por semana ou por dia (`bun`, `openpilot`, `3x-ui`, `hyperframes`, `AutoGPT-platform`) o patch carrega dezenas
   de commits, vários `fix:`, e os avaliadores consideram o objetivo principal da release funcionalidade ou manutenção
   rotineira. Medianas (v1, referência (a)): **FP têm 30 commits e 10 `fix`**, contra 11 commits e 3 `fix` nos VP; ou seja,
   mais commits não é sinal de correção. Só 12 dos 51 FP têm ≤ 2 commits `fix` (34 de 81 VP), então o critério "algum
   commit" não separa.
2. **Falta de proporção.** A parte de commits `fix` é igual em FP e FN (mediana 0,33) e maior nos VP (0,44) e menor nos VN
   (0,19). A regra olha presença, e não quanto da release é correção.
3. **"fix" em commit que não é correção de produto: efeito pequeno.** Das 921 mensagens que casam `fix` nos FP, só 46
   (5%) são de tipo docs/ci/test/chore (35 de 494 nos VP, 7%). Texto como `fixed a lie`, `fix dependabot config` ou
   `docs: ... fix minor formatting` ocorre, mas não explica os FP. Restringir o vocabulário não resolve; o problema é o
   critério "algum commit".
4. **Concentração por repositório.** Os 51 FP estão em 28 repositórios; 5 repositórios dão 22 FP (`AutoGPT`,
   `3x-ui`, `bun`, `openpilot`, `hyperframes`). Como as releases de um repositório se parecem, os erros são
   correlacionados (daí o IC95% por repositório).
5. **Tag fora de SemVer com 4 componentes (1 FP).** `v1.3.17.2 → v1.3.18` cai no ramo de "versão desconhecida" e a decisão
   fica só nas mensagens.

### 4.3 Contra o rótulo humano de Marcela (b1)

O F1 cai de 0,625 para 0,437 sem mudar nenhuma release nem a heurística, só o rótulo. O que muda (script da seção 8,
`dados/analises/avaliacao_heuristica/consenso_humano_marcela.csv`):

| Relação | N | Corretivas pela humana | VP | FP | FN | VN |
|---|---:|---:|---:|---:|---:|---:|
| patch sobe | 65 | 30 (46%) | 24 | **30** | 6 | 5 |
| minor sobe | 53 | 18 (34%) | 0 | 0 | **18** | 35 |
| retrocesso | 6 | 2 (33%) | 0 | 0 | 2 | 4 |
| outro pacote | 13 | 6 (46%) | 0 | 1 | 6 | 6 |
| major sobe / mesma versão / fora de SemVer | 12 | 4 | 2 | 2 | 2 | 6 |

* Nas 150 releases de Marcela a taxa corretiva em "patch sobe" é 46% (contra 55% no consenso) e em "minor sobe" é 34%
  (contra 15%): **o rótulo humano depende bem menos do número de versão** do que o consenso. A `v1` codifica justamente
  essa dependência, então erra nos dois lados: 30 FP em releases de patch que Marcela não considerou corretivas e 18 FN em
  releases minor que ela considerou.
* Para "retrocesso", que no consenso é 87% corretivo, Marcela marcou 2 de 6; a amostra é minúscula, e a divergência com a IA
  nesse padrão não é um achado, é um alerta.
* Com uma só avaliadora humana não dá para separar "a heurística erra" de "Marcela interpreta de outro jeito" (mesma
  ressalva de `resultados_concordancia.md`, seção 4). O que a evidência humana mostra com segurança é que **o resultado
  com a IA (≈ 0,60 a 0,67) não se transfere** para o rótulo humano (0,44).

## 5. Regra de decisão aplicada

`avaliacao_heuristica.md`, seção 4:

1. Alguma versão com F1 ≥ 0,70? **Não**, em nenhuma referência. Não há versão a escolher.
2. Portanto vale o passo 2: `heuristic_v2`, **escrita por Gabriel**, registrada em `HEURISTICS` sem apagar a `v1` e a
   `v1_full_message`, e reavaliada. Este PR **não** escreve a v2, não altera `metricas/cfr_b.py`, `DEFAULT_HEURISTIC`,
   rótulos nem consenso.
3. Cada versão testada, mesmo a que falhou, entra na tabela do artigo: as duas linhas da seção 3.

**Versão final para o pipeline:** não definida. Mantém-se `v1` (padrão atual) até a v2 ser avaliada.

Hipóteses gerais para a v2 (extraídas da seção 4; **a testar**, não validadas, e sem prejulgar o desenho que Gabriel escolher): (i) tratar a relação entre tags dentro da
**mesma linha/pacote** (prefixo) em vez de comparar com a tag anterior no tempo; (ii) retrocesso de versão como possível indício
de manutenção (87% corretivos no consenso, mas só 2 de 6 no rótulo humano); (iii) trocar "algum commit com fix" por um critério que considere **quanto** da release é
correção; (iv) lembrar que a "referência certa" é incerta: um critério ajustado ao consenso de IA pode piorar contra o
rótulo humano.

## 6. Aviso de validade (para o artigo)

* **A referência é IA, não pessoas.** O consenso é maioria automática, sem reunião; nas 150 linhas de (d) os três votos
  são de IA do mesmo modelo (erros correlacionados) e, nas outras 150, só um dos três é humano. Descrever como "consenso
  automático de avaliadores de IA, com uma avaliadora humana em metade da amostra", nunca como "consenso humano" nem
  "três avaliadores".
* **Os números da referência só-humana são a evidência mais forte, e a mais frágil.** (b1) tem 150 releases de **30
  repositórios** e **uma** pessoa. O IC95% (0,34 a 0,53) é largo, e as releases de um mesmo repositório estão
  correlacionadas. Mesmo assim, o limite superior (0,54) está bem abaixo de 0,70.
* **Direção do viés.** O slot `gabriel` conhecia a regra da `v1` (pode inflar o F1) e o consenso herda o viés da IA onde
  discorda da humana (58 de 150). Os valores de (a), (b2), (c) e (d) são medidos contra rótulos de IA e **não devem ser lidos
  como validade contra julgamento humano**; para isso só (b1) serve.
* **Sobreajuste na v2.** A v2 será desenhada a partir da análise de erros destas **mesmas 300 releases**. Para estimar o
  desempenho real, reserve repositórios (não releases) só para a avaliação final, como permite `avaliacao_heuristica.md`
  (seção 4, item 3). Ao medir a v2 nas mesmas releases, o F1 será otimista.
* **Releases excluídas (2 de 300)** são as primeiras releases de dois repositórios; a exclusão não depende da versão da
  heurística e é pequena demais para mudar as conclusões.
* **Releases `not_found` se desfazem com a coleta completa de tags.** Em uma primeira passada, 5 releases de `rust-lang/rust`
  saíram como `not_found` porque a clonagem `--single-branch` não trouxe as tags de ramos de manutenção; com
  `fetch_all_tags` (que o pipeline executa após o clone) elas passam a ser avaliáveis, e os resultados acima já usam
  esse dado (as 5 são VN). Se `dados/releases/` for reconstruído, confira que `status != ok (not_found)` seja 0.
* **F1 e prevalência.** O F1 é da classe `sim`, cuja taxa vai de 35% (b2) a 50% (d); a coluna "tudo corretiva" mostra o
  F1 de um classificador trivial e deve acompanhar o F1 em qualquer tabela do artigo.

## 7. Estado e pendências

* Feito: persistência da amostra com mensagens completas; avaliação das duas versões em cinco referências; erros e padrões.
* Pendente (humano): a `heuristic_v2` por Gabriel e sua reavaliação (idealmente com repositórios de teste separados);
  decisão da versão final e do `DEFAULT_HEURISTIC` em commit próprio; reunião de consenso e/ou segunda pessoa rotulando
  as 150 releases humanas, para reduzir a incerteza da referência; texto do artigo (Metodologia e Ameaças à validade).

## 8. Reprodução

A partir de `lab03/` (Python via `uv`; `GITHUB_TOKEN` com acesso de leitura; rede). Se a rede passar por proxy com
inspeção de TLS, a CA do proxy precisa estar no `SSL_CERT_FILE` (no ambiente desta execução foi preciso também relaxar
`VERIFY_X509_STRICT` do Python 3.13+ fora do repositório; isso não faz parte do código).

```bash
uv sync

# 1. Releases + commits (com full_message) dos 60 repositórios; retomável. Sem argumentos:
uv run python -m analises.persistir_amostra_ouro
#    O clone tem timeout de 120 s: se um repositório grande falhar (aqui, rust-lang/rust), clone-o à mão com os mesmos
#    argumentos e busque todas as tags, depois rode o comando acima de novo (ele reaproveita o clone):
#      git clone --bare --filter=tree:0 --single-branch https://github.com/rust-lang/rust.git cache/git_repos/rust-lang__rust.git
#      git --git-dir=cache/git_repos/rust-lang__rust.git fetch --filter=tree:0 origin '+refs/tags/*:refs/tags/*'

# 2. Recortes do consenso (script abaixo) → dados/analises/avaliacao_heuristica/consenso_*.csv (não versionados)
uv run python recortes.py

# 3. Avaliar as duas versões em cada referência (5 execuções)
D=dados/analises/avaliacao_heuristica
avaliar() { uv run python -m analises.avaliar_heuristica --consenso "$2" --saida "$D/aval_$1.md" --saida-erros "$D/erros_$1.csv" --forcar; }
avaliar todas                  validacao/consenso.csv               # (a)
avaliar humano_marcela         $D/consenso_humano_marcela.csv       # (b1)
avaliar consenso_linhas_humanas $D/consenso_nas_linhas_humanas.csv  # (b2)
avaliar unanime                $D/consenso_unanime.csv              # (c)
avaliar so_ia                  $D/consenso_so_ia.csv                # (d)

# 4. Tabela de relações entre tags (seção 4) e IC95% (seção 3): scripts abaixo
PYTHONPATH=. uv run python padroes.py [caminho_do_consenso]
PYTHONPATH=. uv run python bootstrap.py
```

`recortes.py` (só lê `validacao/`; nunca altera rótulos nem consenso):

```python
from pathlib import Path

import pandas as pd

V = Path("validacao")
D = Path("dados/analises/avaliacao_heuristica")
D.mkdir(parents=True, exist_ok=True)
ler = lambda p: pd.read_csv(p, encoding="utf-8-sig", dtype=str, keep_default_na=False)
cons, marcela, origem = ler(V / "consenso.csv"), ler(V / "rotulos_marcela.csv"), ler(V / "rotulos_marcela_origem.csv")
chave = ["repo_idx", "release_idx"]
humanas = cons.merge(origem[origem["origem"] == "humano"][chave], on=chave)  # as 150 linhas humanas

# (b1) referência = o próprio rótulo humano de Marcela nas suas 150 linhas.
rot = marcela.set_index(chave)["release_corretiva"]
b1 = humanas.copy()
b1["release_corretiva"] = [rot[(r, i)] for r, i in zip(b1["repo_idx"], b1["release_idx"])]
b1.to_csv(D / "consenso_humano_marcela.csv", index=False)
humanas.to_csv(D / "consenso_nas_linhas_humanas.csv", index=False)  # (b2) consenso nas mesmas 150 linhas
cons[cons["release_corretiva_origem"] == "unanimidade"].to_csv(D / "consenso_unanime.csv", index=False)  # (c)
cons[cons["release_corretiva_votos_humano"] == "0"].to_csv(D / "consenso_so_ia.csv", index=False)  # (d) 150 linhas sem voto humano
for f in sorted(D.glob("consenso_*.csv")):
    print(f.name, len(pd.read_csv(f)))
```

`padroes.py` (relação entre as tags × resultado da `v1`; mediana de commits e de commits `fix`):

```python
import re
import sys

import pandas as pd

from analises.avaliar_heuristica import carregar_consenso, montar_amostra, prever
from metricas.cfr_b import is_fix_message, parse_semver

caminho = sys.argv[1] if len(sys.argv) > 1 else "validacao/consenso.csv"
prefixo = lambda tag: re.sub(r"v?\d+\.\d+(\.\d+)?.*$", "", tag)  # "svelte@", "bun-v", "ctx7@"...


_NAO_PRODUTO = re.compile(
    r"^\W*((docs?|ci|test|tests|chore|build|style|refactor|perf|deps)(\([^)]*\))?!?:|fix\((ci|docs?|test|tests|deps|lint)\):)",
    re.IGNORECASE,
)


def relacao(anterior: str, atual: str) -> str:
    """Como a tag muda em relação à `previous_release` (critério de versão da v1)."""
    p, c = parse_semver(anterior), parse_semver(atual)
    if p is None or c is None:
        return "fora de SemVer"
    if prefixo(anterior) != prefixo(atual):
        return "outro pacote (prefixo diferente)"
    if c < p:
        return "retrocesso (backport)"
    if c[0] > p[0]:
        return "major sobe"
    if c[1] > p[1]:
        return "minor sobe"
    return "patch sobe" if c[2] > p[2] else "mesma versão"


am = montar_amostra(carregar_consenso(caminho), "dados/releases")
linhas = []
for e in am.exemplos:
    pred = prever(e, "v1")
    tipo = ("VP" if e.consenso else "FP") if pred else ("FN" if e.consenso else "VN")
    fixes = [c.message for c in e.commits if is_fix_message(c.message)]
    # mensagem "fix" de tipo não-produto: Conventional Commits docs/ci/test/chore/... ou escopo ci/docs/test/...
    nao_produto = sum(bool(_NAO_PRODUTO.match(m)) for m in fixes)
    linhas.append({"repo": e.repo_name, "relacao": relacao(e.previous_release, e.tag_name), "tipo": tipo,
                   "n": len(e.commits), "n_fix": len(fixes), "fix_nao_produto": nao_produto})
d = pd.DataFrame(linhas)
t = pd.crosstab(d["relacao"], d["tipo"]).reindex(columns=["VP", "FP", "FN", "VN"], fill_value=0)
t["N"] = t.sum(axis=1)
t["corretivas (VP+FN)"] = t["VP"] + t["FN"]
t["taxa corretiva"] = (t["corretivas (VP+FN)"] / t["N"]).round(2)
print(t.to_string())
fp = d[d["tipo"] == "FP"]
print(f"FP: {len(fp)} em {fp['repo'].nunique()} repositórios; maiores: {fp['repo'].value_counts().head(5).to_dict()}")

d["parte_fix"] = d["n_fix"] / d["n"]
print("\nmediana por tipo de resultado (v1):")
print(d.groupby("tipo")[["n", "n_fix", "parte_fix"]].median().round(2).to_string())
for tipo in ("VP", "FP"):
    x = d[d["tipo"] == tipo]
    print(f"{tipo}: mensagens 'fix' de tipo não-produto = {x['fix_nao_produto'].sum()} de {x['n_fix'].sum()}; "
          f"releases com <=2 commits 'fix' = {(x['n_fix'] <= 2).sum()} de {len(x)}")
```

`bootstrap.py` (IC95% do F1 por reamostragem de repositórios):

```python
"""IC95% (bootstrap por repositório, 2000 reamostragens, semente 0) do F1 de cada versão em cada referência."""
import numpy as np
import pandas as pd
from analises.avaliar_heuristica import carregar_consenso, montar_amostra, prever
from metricas.cfr_b import HEURISTICS

REFS = {
    "todas (300)": "validacao/consenso.csv",
    "humano Marcela (150)": "dados/analises/avaliacao_heuristica/consenso_humano_marcela.csv",
    "consenso nas linhas humanas (150)": "dados/analises/avaliacao_heuristica/consenso_nas_linhas_humanas.csv",
    "unânimes (217)": "dados/analises/avaliacao_heuristica/consenso_unanime.csv",
    "só IA (150)": "dados/analises/avaliacao_heuristica/consenso_so_ia.csv",
}
rng = np.random.default_rng(0)
for nome, caminho in REFS.items():
    am = montar_amostra(carregar_consenso(caminho), "dados/releases")
    for v in HEURISTICS:
        df = pd.DataFrame({"repo": [e.repo_name for e in am.exemplos], "y": [e.consenso for e in am.exemplos],
                           "p": [prever(e, v) for e in am.exemplos]})
        g = {r: x[["y", "p"]].to_numpy() for r, x in df.groupby("repo")}
        repos = list(g)
        def f1(a):
            tp = (a[:, 0] & a[:, 1]).sum(); fp = (~a[:, 0] & a[:, 1]).sum(); fn = (a[:, 0] & ~a[:, 1]).sum()
            return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        vals = [f1(np.vstack([g[r] for r in rng.choice(repos, len(repos))])) for _ in range(2000)]
        lo, hi = np.percentile(vals, [2.5, 97.5])
        print(f"{nome:<36}{v:<18}F1={f1(df[['y','p']].to_numpy()):.3f}  IC95%=[{lo:.3f}; {hi:.3f}]  repos={len(repos)}")
```

# Resultados da Questão de Pesquisa 07 — Análise de Sensibilidade DORA (Sprint 03)

**Autor:** João Pedro Peres (@jaoppb)  
**Papel no Guia:** Integrante C (RQ 07 — Análise de Sensibilidade)  
**Módulo Implementado:** [`../analises/analise_rq07.py`](../analises/analise_rq07.py)  
**Suíte de Testes:** [`../tests/test_analise_rq07.py`](../tests/test_analise_rq07.py)  
**Artefatos Gerados:** [`../dados/analises/rq07_sensibilidade.json`](../dados/analises/rq07_sensibilidade.json), tabelas `.tex`/`.md` e figuras em [`../dados/analises/figuras/`](../dados/analises/figuras/)

---

## 1. Contexto e Definições Operacionais Avaliadas

A Questão de Pesquisa 07 investiga a **robustez metodológica** da medição DORA em software livre:
> *O quanto a classificação DORA de um repositório depende da definição operacional escolhida?*

Para responder a essa pergunta, o pipeline comparou **três combinações metodológicas** disjuntas de *proxies*, aplicadas sobre todos os 330 repositórios da amostra final:

| Parâmetro Operacional | C1 (Referência Oficial) | C2 (Variante Pré-releases) | C3 (Variante Git Tags) |
|---|---|---|---|
| **Unidade de Deploy** | Release publicada oficial | Release publicada + Pré-release | Marcador Git Tag |
| **Lead Time for Changes** | Variante (a) [commit mais antigo] | Variante (b) [mediana por commit] | Variante (b) [commits entre tags] |
| **Change Failure Rate** | Variante (a) [proxy de CI] | Variante (b) [releases corretivas $\le$ 7d] | Variante (a) [proxy de CI] |
| **Tempo de Recuperação** | Mediana por workflow no CI | Mediana por workflow no CI | Mediana por workflow no CI |

Em cada combinação, o repositório recebe notas de 1 a 4 (Low=1, Medium=2, High=3, Elite=4) para as quatro métricas e a classificação consolidada é dada pela **mediana arredondada para baixo**, conforme regra padrão da disciplina.

---

## 2. Distribuição das Categorias DORA por Combinação

A tabela abaixo compara a distribuição dos 330 repositórios nas quatro faixas de maturidade:

| Faixa DORA | C1 (Referência) | C2 (Pré-releases) | C3 (Git Tags) |
|:---|---:|---:|---:|
| **Elite** | 23 (7,0%) | 9 (2,7%) | 26 (7,9%) |
| **High** | 147 (44,5%) | 139 (42,1%) | 177 (53,6%) |
| **Medium** | 146 (44,2%) | 164 (49,7%) | 116 (35,2%) |
| **Low** | 14 (4,2%) | 18 (5,5%) | 11 (3,3%) |
| **Total** | **330 (100%)** | **330 (100%)** | **330 (100%)** |

Figura gerada: `dados/analises/figuras/rq07_distribuicao_c1_c2_c3.png` (e `.pdf`).

---

## 3. Análise de Concordância Pareada e Transições

Calculamos o percentual de migração de categoria e o coeficiente **Kappa de Cohen ponderado linear** ($\kappa_{\text{linear}}$), que atribui penalidade proporcional à distância ordinal entre categorias (uma discrepância Elite $\leftrightarrow$ Low pesa mais que Elite $\leftrightarrow$ High):

| Par Comparado | $n$ | Repositórios que Mudaram | \% Mudança | Subiram de Tier | Desceram de Tier | Kappa Linear ($\kappa_{\text{linear}}$) | Interpretação (Landis & Koch) |
|---|---:|---:|---:|---:|---:|---:|---|
| **C1 $\times$ C2** | 330 | 84 | **25,5\%** | 25 (7,6%) | 59 (17,9%) | **0,6031** | **Substancial** |
| **C1 $\times$ C3** | 330 | 71 | **21,5\%** | 54 (16,4%) | 17 (5,2%) | **0,6871** | **Substancial** |
| **C2 $\times$ C3** | 330 | 85 | **25,8\%** | 81 (24,5%) | 4 (1,2%) | **0,6222** | **Substancial** |

Figura gerada: `dados/analises/figuras/rq07_painel_transicoes.png` (matrizes de transição lado a lado).

---

## 4. Matriz de Transição C1 (Referência) $\rightarrow$ C2

A matriz detalha os fluxos de migração dos 330 repositórios ao adotar a combinação C2:

| C1 (Linhas) $\backslash$ C2 (Colunas) | Elite (C2) | High (C2) | Medium (C2) | Low (C2) | Total C1 |
|---|---:|---:|---:|---:|---:|
| **Elite (C1)** | **8** | 12 | 3 | 0 | 23 |
| **High (C1)** | 1 | **104** | 41 | 1 | 147 |
| **Medium (C1)** | 0 | 23 | **118** | 5 | 146 |
| **Low (C1)** | 0 | 0 | 2 | **12** | 14 |
| **Total C2** | **9** | **139** | **164** | **18** | **330** |

*Diagonal principal (em negrito):* **246 repositórios (74,5%)** mantêm exatamente a mesma categoria DORA entre C1 e C2.

---

## 5. Confronto com a Hipótese Informal e Discussão Teórica

Na Sprint 01 (`docs/hipoteses_rq04_rq07.md`), João formulou a seguinte hipótese informal:
> *Esperamos que entre 35% e 60% dos repositórios alterem sua categoria DORA geral ao confrontar C1 com C2 e C3, com Kappa ponderado linear entre C1 e C2 na faixa de $[0{,}30; 0{,}55]$ (concordância apenas fraca a moderada).*

### Análise Crítica dos Resultados:
1. **Maior Robustez do que o Previsto:**
   - A taxa de migração observada foi de **25,5%** (C1 $\times$ C2) e **21,5%** (C1 $\times$ C3), ambas abaixo do teto pessimista estimado de 35% a 60%.
   - O $\kappa_{\text{linear}}$ alcançou **0,6031** (C1 $\times$ C2) e **0,6871** (C1 $\times$ C3), enquadrando-se no limiar de concordância **Substancial** de Landis & Koch.
   - Isso demonstra que o arcabouço DORA agregado por mediana possui uma **inércia protetora**: a classificação geral absorve oscilações parciais em métricas isoladas.
2. **Sensibilidade Real em 1 a cada 4 Repositórios:**
   - Embora 75% dos repositórios permaneçam estáveis, **1 em cada 4 projetos (25,5%) muda de nível DORA** exclusivamente devido à escolha dos proxies técnicos. Isso refuta a premissa de que proxies operacionais em repositórios abertos sejam neutros ou intercambiáveis.
3. **Efeito das Tags (C3) vs. Pré-releases (C2):**
   - Na combinação C3 (Git Tags), 54 repositórios (16,4%) subiram de tier em relação a C1, refletindo o resgate de projetos que utilizam versionamento rigoroso por tags sem publicar Releases formais na interface do GitHub.
   - Na combinação C2, 59 repositórios (17,9%) desceram de tier, demonstrando que a exigência de ausência de releases corretivas em até 7 dias (CFR b) penaliza mais severamente os projetos do que as falhas brutas de CI (CFR a).

---

## 6. Comandos de Reprodução e Execução

Para reexecutar a análise de sensibilidade e regerar todas as tabelas e gráficos:
```bash
uv run python -m analises.analise_rq07
```

Para rodar os testes automatizados da RQ 07:
```bash
uv run pytest tests/test_analise_rq07.py -v
```

# Referências da Metodologia: mapeamento dos marcadores `[REF: ...]`

Issue #68. Este arquivo acompanha `referencias_metodologia.bib` e **não altera** o
`rascunho_metodologia.md`. A troca dos marcadores pelas citações é uma etapa posterior.

* **Números de linha** referem-se ao `rascunho_metodologia.md` no commit `92dccbc`
  (base desta branch). Se o rascunho mudar, procure pelo texto exato do marcador.
* **Verificação feita em 20/10/2026.** Cada referência foi conferida (autores, ano, título, periódico,
  volume, número, páginas e DOI) contra o Crossref (`https://api.crossref.org/works/<doi>`), contra a
  primeira página do artigo no JSTOR ou contra outra fonte indicada. Nenhuma referência foi escrita só
  de memória.
* **Status:** `VERIFICADO` (conferido em registro oficial ou na página da fonte), `PARCIAL` (conferido
  só em fontes secundárias; o que falta está dito) e `NÃO VERIFICADO` (campo pontual que não consegui
  conferir; todos estão listados na seção 4).

## 1. Marcadores `[REF: ...]` do rascunho

| Linha | Marcador (texto exato) | Chave | Referência completa | Evidência de verificação | Status |
|---|---|---|---|---|---|
| 378 | `[REF: Fleiss, 1971]` | `fleiss1971` | FLEISS, J. L. Measuring nominal scale agreement among many raters. *Psychological Bulletin*, v. 76, n. 5, p. 378-382, 1971. DOI: 10.1037/h0031619. | Crossref `10.1037/h0031619`: autor, título, volume 76, número 5, páginas 378-382, ano 1971. | VERIFICADO |
| 446 | `[REF: Spearman]` | `spearman1904` | SPEARMAN, C. The proof and measurement of association between two things. *The American Journal of Psychology*, v. 15, n. 1, p. 72-101, 1904. DOI: 10.2307/1412159. | Crossref `10.2307/1412159`: título, volume 15, número 1, ano 1904, página inicial 72. Página final 101 conferida em citações indexadas no PubMed (Am J Psychol. 1904;15:72-101) e na Persée. O marcador não traz ano; propomos 1904, o artigo original. | VERIFICADO |
| 451 | `[REF: Kruskal e Wallis, 1952; Mann e Whitney, 1947]` | `kruskal1952`; `mann1947` | KRUSKAL, W. H.; WALLIS, W. A. Use of ranks in one-criterion variance analysis. *Journal of the American Statistical Association*, v. 47, n. 260, p. 583-621, 1952. DOI: 10.1080/01621459.1952.10483441.<br>MANN, H. B.; WHITNEY, D. R. On a test of whether one of two random variables is stochastically larger than the other. *The Annals of Mathematical Statistics*, v. 18, n. 1, p. 50-60, 1947. DOI: 10.1214/aoms/1177730491. | Crossref `10.1080/01621459.1952.10483441` (v. 47, n. 260, p. 583-621, dez. 1952) e Crossref `10.1214/aoms/1177730491` (v. 18, n. 1, p. 50-60, mar. 1947). | VERIFICADO |
| 453 | `[REF: Holm, 1979]` | `holm1979` | HOLM, S. A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, v. 6, n. 2, p. 65-70, 1979. JSTOR: <https://www.jstor.org/stable/4615733>. | Primeira página do PDF no JSTOR (cópia hospedada em ime.usp.br): "Scandinavian Journal of Statistics, Vol. 6, No. 2 (1979), pp. 65-70", Stable URL jstor 4615733, autor Sture Holm. **Não há DOI** no Crossref (a busca só devolveu Holland & Copenhaver, 1987, que é outro artigo), por isso a referência usa o URL do JSTOR. | VERIFICADO |
| 461 | `[REF: Cohen, 1968]` | `cohen1968` | COHEN, J. Weighted kappa: nominal scale agreement provision for scaled disagreement or partial credit. *Psychological Bulletin*, v. 70, n. 4, p. 213-220, 1968. DOI: 10.1037/h0026256. | Crossref `10.1037/h0026256`: autor, título, volume 70, número 4, páginas 213-220, ano 1968. | VERIFICADO |

## 2. Citações sem marcador no rascunho (já aparecem como texto)

Estas citações existem no texto ou no Apêndice C, mas sem a referência completa. Verificamos para que
possam entrar na lista final.

| Linha | Trecho no rascunho | Chave | Referência completa | Evidência de verificação | Status |
|---|---|---|---|---|---|
| 39, 638 | `Forsgren, Humble & Kim, 2018` | `forsgren2018` | FORSGREN, N.; HUMBLE, J.; KIM, G. *Accelerate: the science of lean software and DevOps: building and scaling high performing technology organizations*. IT Revolution Press, 2018. ISBN 978-1-942788-33-1. | Open Library (API, ISBN 9781942788331): três autores, editora "IT Revolution Press", 27 mar. 2018, 288 p. Páginas da editora (itrevolution.com) e da Simon & Schuster confirmam título, autores e ISBN. O Crossref só tem a tradução alemã (2019), que **não** é a obra citada. | VERIFICADO (fonte secundária confiável; sem registro Crossref da edição original) |
| 39, 639 | `DORA, [guia das métricas](https://dora.dev/guides/dora-metrics-four-keys/)` | `dora_metricas` | HARVEY, N. DORA's software delivery performance metrics. DORA, Google Cloud. Disponível em: <https://dora.dev/guides/dora-metrics-four-keys/>. Acesso em: 20 out. 2026. | Página acessada em 20/10/2026: título "DORA's software delivery performance metrics", assinada por Nathen Harvey. A página **não traz data**. Hoje descreve **cinco** métricas (inclui *deployment rework rate*), enquanto o rascunho usa as quatro clássicas; ver o item 3 da seção 4. | VERIFICADO (página); data não aplicável |
| 39, 639 | `Relatórios Accelerate State of DevOps` (<https://dora.dev/research/>) | `dora2024` | DORA. *Accelerate State of DevOps Report 2024*. Google Cloud, 2024. Disponível em: <https://dora.dev/research/2024/>. Acesso em: 20 out. 2026. | `dora.dev/research/` lista os arquivos de 2014 a 2025; a página `/research/2024/` tem o título "Accelerate State of DevOps Report 2024". Escolhemos 2024 por ser a edição citada em `guialab03.md` (mudanças de 2024 nas métricas). **Decisão dos autores:** citar outra edição se o texto depender dela. | VERIFICADO (página) |
| 337, 643 | `Versionamento Semântico ([semver.org](https://semver.org/lang/pt-BR/))` | `semver` | PRESTON-WERNER, T. *Semantic Versioning 2.0.0*. Disponível em: <https://semver.org/lang/pt-BR/>. Acesso em: 20 out. 2026. | Página `semver.org` (título "Semantic Versioning 2.0.0") e a página em pt-BR ("A Especificação da Semântica de Versionamento é autoria de Tom Preston-Werner"). **Ano não verificado**; usar `[s.d.]` até confirmar. | VERIFICADO (autoria e título); ano NÃO VERIFICADO |
| 387, 642 | `Landis & Koch (1977)` | `landis1977` | LANDIS, J. R.; KOCH, G. G. The measurement of observer agreement for categorical data. *Biometrics*, v. 33, n. 1, p. 159-174, 1977. DOI: 10.2307/2529310. | Crossref `10.2307/2529310`: autores, título, volume 33, número 1, mar. 1977, página inicial 159. Página final 174 conferida na primeira página do PDF no JSTOR ("Vol. 33, No. 1 (Mar., 1977), pp. 159-174") e em citações no PubMed Central. | VERIFICADO |
| 456, 641 | `Romano et al., 2006` | `romano2006` | ROMANO, J.; KROMREY, J. D.; CORAGGIO, J.; SKOWRONEK, J. Appropriate statistics for ordinal level data: should we really be using t-test and Cohen's d for evaluating group differences on the NSSE and other surveys? In: ANNUAL MEETING OF THE FLORIDA ASSOCIATION OF INSTITUTIONAL RESEARCH, 2006. | Não foi possível abrir o PDF (ResearchGate, ACM e CiteSeerX bloqueados ou indisponíveis). Título, ano e autores batem em duas fontes secundárias independentes: a documentação do pacote CRAN `effsize` (que cita este trabalho como fonte dos limiares 0,147 / 0,33 / 0,474) e a página do ResearchGate. Um comentário no GitHub do `effsize` cita uma segunda versão do trabalho com título diferente e um quinto autor (L. Devine). | PARCIAL (ver seção 4) |
| 474, 640 | `Wohlin et al. (2012)` | `wohlin2012` | WOHLIN, C.; RUNESON, P.; HÖST, M.; OHLSSON, M. C.; REGNELL, B.; WESSLÉN, A. *Experimentation in software engineering*. Berlin, Heidelberg: Springer, 2012. DOI: 10.1007/978-3-642-29044-2. | Crossref `10.1007/978-3-642-29044-2` (tipo livro): seis autores, ano 2012, editora Springer Berlin Heidelberg, ISBN 9783642290442 (eletrônico) e 9783642290435. | VERIFICADO |

## 3. Referências sugeridas (a pedido da tarefa; o rascunho não tem marcador)

O rascunho usa estes métodos sem citar a fonte. Os autores decidem se entram.

| Onde aparece | Chave | Referência completa | Evidência de verificação | Status |
|---|---|---|---|---|
| Linha 454-455 (`Cliff's delta`, fórmula $\delta = 2U_1/(n_1 n_2) - 1$) | `cliff1993` | CLIFF, N. Dominance statistics: ordinal analyses to answer ordinal questions. *Psychological Bulletin*, v. 114, n. 3, p. 494-509, 1993. DOI: 10.1037/0033-2909.114.3.494. | Crossref `10.1037/0033-2909.114.3.494`: autor, título, volume 114, número 3, páginas 494-509, nov. 1993. Não conferi que a forma $2U_1/(n_1 n_2) - 1$ esteja escrita no artigo; é identidade algébrica conhecida com o U de Mann-Whitney. Citar Cliff (1993) para a estatística, não para essa fórmula. | VERIFICADO (metadados) |
| Linha 453-454 ($\varepsilon^2 = H/(n-1)$) | `tomczak2014` | TOMCZAK, M.; TOMCZAK, E. The need to report effect size estimates revisited: an overview of some recommended measures of effect size. *Trends in Sport Sciences*, v. 21, n. 1, p. 19-25, 2014. | PDF da revista (tss.awf.poznan.pl): cabeçalho "Trends in Sport Sciences 2014; 1(21): 19-25", título e autores. Na extração de texto do PDF, a seção sobre Kruskal-Wallis dá o $\varepsilon^2$ como $H$ dividido por $(n^2-1)/(n+1)$, que é algebricamente $H/(n-1)$ e coincide com o rascunho; confira a fórmula impressa no PDF, pois a extração embaralhou a ordem dos termos. Não procurei DOI para este artigo. | VERIFICADO |
| Linhas 459-462 (kappa de Cohen ponderado; o kappa simples é a base) | `cohen1960` | COHEN, J. A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, v. 20, n. 1, p. 37-46, 1960. DOI: 10.1177/001316446002000104. | Crossref `10.1177/001316446002000104`: autor, título, volume 20, número 1, páginas 37-46, abr. 1960. | VERIFICADO |

## 4. Itens não verificados e ressalvas

1. **`romano2006` (PARCIAL).** Falta o PDF original. Não verificados: prenomes completos dos autores, local
   do evento e páginas; por isso o `.bib` usa só as iniciais e não tem `address` nem `pages`. O título
   pode variar entre a versão em ResearchGate e a citada pelo `effsize`, e há indício de uma segunda
   versão com quinto autor (Devine). Os autores devem abrir o PDF e confirmar antes de submeter. Os limiares
   de Cliff (0,147 / 0,33 / 0,474) são atribuídos a Romano et al. (2006) pelo `effsize`, e não os conferi
   no texto original.
2. **`semver`: ano NÃO VERIFICADO.** Autoria e título conferidos; a data de publicação da versão 2.0.0
   não foi checada. Citar como `[s.d.]` ou confirmar no repositório `semver/semver`.
3. **Guia DORA (`dora_metricas`) × quatro métricas.** O guia atual descreve cinco métricas e já trocou
   MTTR por *failed deployment recovery time*. O rascunho cita o guia para as quatro métricas clássicas.
   Vale o texto dizer que a definição seguida é a clássica (`guialab03.md`), e não a atual.
4. **Cohen (1968) e pesos lineares.** O artigo define o kappa ponderado em geral. Não verifiquei se o
   artigo nomeia os pesos "lineares"; essa escolha é da implementação (`sklearn`, `weights='linear'`) e
   do grupo. Cite Cohen (1968) para o kappa ponderado, não para a escolha dos pesos.
5. **Spearman sem ano no marcador.** O marcador `[REF: Spearman]` não traz ano. A proposta é o artigo de 1904.
   Se o grupo quiser uma referência de livro-texto, é outra decisão.
6. **Holm (1979) sem DOI.** A referência usa o URL do JSTOR. Se a revista exigir DOI, não há um registrado
   que eu tenha encontrado.
7. **Não buscadas.** `statsmodels`, `scikit-learn` e `scipy` são citados por nome no rascunho, mas não
   têm marcador `[REF:]`. Não procurei as referências desses pacotes.

## 5. Como usar o `.bib`

```latex
\bibliographystyle{sbc}            % ou abntex2-alf, conforme o template do evento
\bibliography{referencias_metodologia}
```

Exemplo de troca (etapa futura): o marcador de Fleiss vira `\cite{fleiss1971}`. Todas as chaves usadas nas
tabelas acima existem no `.bib` (16 entradas).

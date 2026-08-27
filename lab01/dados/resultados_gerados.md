# Resultados (gerado automaticamente a partir dos dados coletados)

Base analisada: **99984** repositórios (arquivo `lab01/dados/unified_sample.csv`).

### RQ01 - Idade do repositório
- Mediana: **8.1 anos** | Média: 7.9 anos | Máximo: 18.8 anos
- Base: 99984 de 99984 repositórios com dado válido.

### RQ02 - Pull requests aceitas (mescladas)
- Mediana: **27** | Média: 389.1 | P90: 638 | P99: 6047
- Outliers (IQR): 14896 de 99984 (14.9%), limites normais [-209, 359]

### RQ03 - Total de releases
- 45.3% dos repositórios não têm nenhuma release cadastrada.
- Mediana geral: 2 | Média geral: 28.6

### RQ04 - Tempo até a última atualização
- Mediana: **2 dias** | Média: 9.2 dias | Máximo: 773 dias

### RQ05 - Linguagem primária
- Linguagem líder: **Python** (18089 repositórios, 18.1%)
- Valores ausentes: 8180 de 99984 (8.18%)
- Top 10 linguagens:
  - Python: 18089
  - JavaScript: 11858
  - TypeScript: 9083
  - Java: 6021
  - Go: 5750
  - C++: 5306
  - C: 3927
  - Rust: 3307
  - C#: 2975
  - Shell: 2495

### RQ06 - Razão de issues fechadas/total
- Mediana: **0.750** | Média: 0.689 | Desvio padrão: 0.265
- Valores ausentes: 4831 de 99984 (4.83%)
- Outliers (IQR): 0, limites [-0.080, 1.509]

### RQ07 - Cruzamento RQ02/03/04 por linguagem (mediana)
  - Rust: PRs=143, Releases=16, Dias s/ update=1
  - TypeScript: PRs=93, Releases=17, Dias s/ update=1
  - Go: PRs=80, Releases=16, Dias s/ update=1
  - PHP: PRs=69, Releases=21, Dias s/ update=2
  - C#: PRs=42, Releases=12, Dias s/ update=1
  - C++: PRs=36, Releases=5, Dias s/ update=1
  - C: PRs=26, Releases=2, Dias s/ update=1
  - JavaScript: PRs=25, Releases=1, Dias s/ update=4
  - Shell: PRs=19, Releases=0, Dias s/ update=1
  - Python: PRs=17, Releases=0, Dias s/ update=1
  - HTML: PRs=14, Releases=0, Dias s/ update=2
  - Java: PRs=13, Releases=2, Dias s/ update=4

### Matriz de correlação (Spearman)

```
                        age_days  merged_pull_requests  total_releases  time_since_update_days  total_issues  closed_issues_ratio
age_days                    1.00                  0.16           -0.02                    0.32          0.20                 0.09
merged_pull_requests        0.16                  1.00            0.54                   -0.22          0.68                 0.39
total_releases             -0.02                  0.54            1.00                   -0.22          0.54                 0.32
time_since_update_days      0.32                 -0.22           -0.22                    1.00         -0.23                -0.10
total_issues                0.20                  0.68            0.54                   -0.23          1.00                 0.29
closed_issues_ratio         0.09                  0.39            0.32                   -0.10          0.29                 1.00
```


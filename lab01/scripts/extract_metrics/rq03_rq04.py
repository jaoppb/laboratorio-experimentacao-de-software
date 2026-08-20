from pathlib import Path

import pandas as pd

# Automatically locate the CSV file relative to the script location or current directory
script_dir = Path(__file__).resolve().parent

possible_paths = [
    script_dir / "../../dados/unified_sample.csv",
    script_dir / "../dados/unified_sample.csv",
    Path.cwd() / "dados/unified_sample.csv",
    Path.cwd() / "lab01/dados/unified_sample.csv",
]

csv_path = next((p.resolve() for p in possible_paths if p.exists()), None)

if not csv_path:
    raise FileNotFoundError(
        "Could not locate 'dados/unified_sample.csv'. Ensure the file exists."
    )

# Load CSV data
df = pd.read_csv(csv_path)

# Extract metrics for RQ03 (total_releases)
rq03_mean = df["total_releases"].mean()
rq03_median = df["total_releases"].median()
rq03_std = df["total_releases"].std()
rq03_min = df["total_releases"].min()
rq03_max = df["total_releases"].max()

# Extract metrics for RQ04 (time_since_update_days)
rq04_mean = df["time_since_update_days"].mean()
rq04_median = df["time_since_update_days"].median()
rq04_std = df["time_since_update_days"].std()
rq04_min = df["time_since_update_days"].min()
rq04_max = df["time_since_update_days"].max()

# Generate the Markdown output
markdown_output = f"""## RQ03 + RQ04 (João)

**Metodologia:** A validação foi realizada a partir do arquivo `dados/unified_sample.csv`, contendo uma amostra consolidada de {len(df)} repositórios. Por meio da biblioteca `pandas`, foram calculadas métricas de tendência central (média e mediana), dispersão (desvio padrão) e extremos (mínimo e máximo) para os atributos `total_releases` (RQ03) e `time_since_update_days` (RQ04).

**RQ03 - Total de releases**
- **Estatísticas encontradas:**
  - Média: {rq03_mean:.2f} releases (Desvio Padrão: {rq03_std:.2f})
  - Mediana: {rq03_median:.2f} releases
  - Variação: de {rq03_min} a {rq03_max} releases
- **Hipótese informal:** Repositórios populares e com ciclo de desenvolvimento maduro tendem a adotar entregas frequentes, resultando em um volume expressivo de releases acumuladas.

**RQ04 - Tempo desde a última atualização**
- **Estatísticas encontradas:**
  - Média: {rq04_mean:.2f} dias (Desvio Padrão: {rq04_std:.2f})
  - Mediana: {rq04_median:.2f} dias
  - Variação: de {rq04_min} a {rq04_max} dias
- **Hipótese informal:** Repositórios com grande base de usuários e colaboradores recebem manutenção ativa constante, portanto a maioria expressiva possui atualizações muito recentes.
"""

print(markdown_output)

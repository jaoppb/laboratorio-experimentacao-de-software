"""Estima os parâmetros da simulação lognormal a partir dos dados reais.

Lê dados/reais/pr_merge_time.csv e grava dados/parametros.json:
    {"com_bot": {"n", "mediana", "sigma_log"}, "sem_bot": {...}}

Numa lognormal, mediana = exp(mu) e sigma_log = desvio-padrão de ln(tempo).
Também imprime n, mediana, assimetria e outliers (regra de Tukey) por grupo.
Usa só a biblioteca padrão.
"""
import csv
import json
import math
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "reais" / "pr_merge_time.csv"
SAIDA = RAIZ / "dados" / "parametros.json"


def assimetria(x):
    """Coeficiente de assimetria amostral (Fisher-Pearson ajustado, G1)."""
    n = len(x)
    m = statistics.fmean(x)
    s = statistics.stdev(x)
    return n / ((n - 1) * (n - 2)) * sum(((v - m) / s) ** 3 for v in x)


def outliers_tukey(x):
    q1, _, q3 = statistics.quantiles(x, n=4, method="inclusive")
    iqr = q3 - q1
    return sum(v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr for v in x)


def main():
    grupos = {}
    with ENTRADA.open() as f:
        for linha in csv.DictReader(f):
            grupos.setdefault(linha["grupo"], []).append(float(linha["tempo_merge_horas"]))

    parametros = {}
    for g in ("com_bot", "sem_bot"):
        t = grupos[g]
        logs = [math.log(v) for v in t]
        parametros[g] = {
            "n": len(t),
            "mediana": round(statistics.median(t), 4),
            "sigma_log": round(statistics.stdev(logs), 4),
        }
        print(
            f"{g}: n={len(t)}  mediana={statistics.median(t):.3f} h  média={statistics.fmean(t):.1f} h  "
            f"máx={max(t):.0f} h\n"
            f"        assimetria={assimetria(t):.2f} (bruto)  {assimetria(logs):.2f} (log)  "
            f"outliers Tukey={outliers_tukey(t)}  sigma_log={parametros[g]['sigma_log']}"
        )

    SAIDA.write_text(json.dumps(parametros, indent=2, ensure_ascii=False) + "\n")
    print(f"gravado: {SAIDA}")


if __name__ == "__main__":
    main()

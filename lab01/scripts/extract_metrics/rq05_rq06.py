#!/usr/bin/env python3
"""Extrai métricas para RQ05 (linguagem primária) e RQ06 (closed_issues_ratio).

Uso:
    python rq05_rq06.py --csv ../../dados/unified_sample.csv --out ../../dados/metrics_rq05_rq06.json

O script depende apenas da biblioteca padrão.
"""
from pathlib import Path
import csv
import json
import statistics
import argparse
from typing import List, Dict, Any


def load_rows(csv_path: Path) -> List[List[str]]:
    with csv_path.open(newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def extract_metrics(header: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    h_index = {name: i for i, name in enumerate(header)}
    pl_idx = h_index.get('primary_language')
    cir_idx = h_index.get('closed_issues_ratio')

    lang_counts: Dict[str, int] = {}
    closed_vals: List[float] = []
    miss_lang = 0
    miss_closed = 0

    for r in rows:
        # primary language
        pl = r[pl_idx].strip() if pl_idx is not None else ''
        if pl == '' or pl.lower() == 'nan':
            miss_lang += 1
        else:
            lang_counts[pl] = lang_counts.get(pl, 0) + 1

        # closed_issues_ratio
        cir = r[cir_idx].strip() if cir_idx is not None else ''
        try:
            if cir == '' or cir.lower() == 'nan':
                miss_closed += 1
            else:
                v = float(cir)
                closed_vals.append(v)
        except Exception:
            miss_closed += 1

    total_rows = len(rows)
    top_langs = sorted(lang_counts.items(), key=lambda x: -x[1])

    metrics: Dict[str, Any] = {
        'total_rows': total_rows,
        'primary_language': {
            'counts': top_langs,
            'missing': miss_lang,
        },
        'closed_issues_ratio': {
            'missing': miss_closed,
        },
    }

    if closed_vals:
        n = len(closed_vals)
        mean = sum(closed_vals) / n
        med = statistics.median(closed_vals)
        mn = min(closed_vals)
        mx = max(closed_vals)
        pstdev = statistics.pstdev(closed_vals)
        # quartiles (inclusive method)
        try:
            qs = statistics.quantiles(closed_vals, n=4, method='inclusive')
            q1, q2, q3 = qs[0], qs[1], qs[2]
        except Exception:
            # fallback simple quartiles
            q1 = statistics.median(sorted(v for v in closed_vals if v <= med))
            q3 = statistics.median(sorted(v for v in closed_vals if v >= med))
        iqr = q3 - q1
        li = q1 - 1.5 * iqr
        ls = q3 + 1.5 * iqr
        outliers = [v for v in closed_vals if v < li or v > ls]

        metrics['closed_issues_ratio'].update({
            'n_non_null': n,
            'mean': mean,
            'median': med,
            'min': mn,
            'max': mx,
            'pstdev': pstdev,
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'iqr_limits': [li, ls],
            'outliers_count': len(outliers),
        })

    return metrics


def save_metrics(out_path: Path, metrics: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # convert counts tuples to list for JSON
    m = metrics.copy()
    m['primary_language'] = m['primary_language'].copy()
    m['primary_language']['counts'] = [[k, v] for k, v in m['primary_language']['counts']]
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(m, f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, default=Path(__file__).parents[2] / 'dados' / 'unified_sample.csv')
    parser.add_argument('--out', type=Path, default=Path(__file__).parents[2] / 'dados' / 'metrics_rq05_rq06.json')
    parser.add_argument('--top', type=int, default=20, help='Número de linguagens top a incluir na saída impressa')
    args = parser.parse_args()

    header, rows = load_rows(args.csv)
    metrics = extract_metrics(header, rows)

    # print resumo
    print(f"TOTAL_ROWS {metrics['total_rows']}")
    print('\nTop languages (top {args.top}):')
    for k, v in metrics['primary_language']['counts'][: args.top]:
        print(f'{k}: {v}')
    print('\nmissing_primary_language', metrics['primary_language']['missing'])
    print('missing_closed_issues_ratio', metrics['closed_issues_ratio']['missing'])
    if 'n_non_null' in metrics['closed_issues_ratio']:
        c = metrics['closed_issues_ratio']
        print('\nclosed_issues_ratio stats:')
        print(f"n={c['n_non_null']} mean={c['mean']:.6f} median={c['median']:.6f} min={c['min']:.6f} max={c['max']:.6f} pstdev={c['pstdev']:.6f}")
        print('q1=', c['q1'], 'q3=', c['q3'], 'iqr=', c['iqr'])
        print('outliers_count', c['outliers_count'])

    save_metrics(args.out, metrics)
    print(f'Escrito: {args.out}')


if __name__ == '__main__':
    main()

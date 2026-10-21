"""Comparison report of the final regeneration of the dataset (Issue #56).

Compares the dataset before (baseline) and after the regeneration column by
column and checks the invariants of a regeneration of a FROZEN sample: same
repositories in the same order, unchanged selection-time metadata and the full
schema. `render_report` produces the pt-BR Markdown written to
`docs/regeneracao_final.md`.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.orchestrator import SCHEMA_REPOSITORIOS

# Selection-time columns: copied from the committed dataset, never recomputed.
METADATA_COLUMNS: tuple[str, ...] = (
    "owner",
    "name",
    "full_name",
    "stars",
    "language",
    "default_branch",
    "created_at",
    "contributors_count",
)
SCHEMA_COLUMNS: tuple[str, ...] = tuple(f.name for f in SCHEMA_REPOSITORIOS)
METRIC_COLUMNS: tuple[str, ...] = tuple(
    c for c in SCHEMA_COLUMNS if c not in METADATA_COLUMNS
)
TIER_COLUMNS: tuple[str, ...] = tuple(c for c in SCHEMA_COLUMNS if c.endswith("_tier"))

# Columns that every regenerated repository must have filled (the others are
# legitimately null for some repositories: lead time without commits, CFR (b)
# with every release censored, recovery time without episodes, ...).
NEVER_NULL_COLUMNS: tuple[str, ...] = (
    "releases_count_window",
    "total_releases",
    "workflow_runs_count_window",
    "total_workflow_runs",
    "deployment_frequency",
    "deployment_tier",
    "cfr_a",
    "cfr_tier",
    "recovery_tier",
    "overall_dora_score",
    "overall_dora_tier",
    "prereleases_count_window",
    "total_prereleases",
    "tags_count_window",
    "total_tags",
    "c2_deployment_frequency",
    "c3_deployment_frequency",
    "cfr_b_failed_releases",
    "cfr_b_evaluated_releases",
    "cfr_b_censored_releases",
    "cfr_b_skipped_releases",
    "c2_cfr_b_failed_releases",
    "c2_cfr_b_evaluated_releases",
    "c2_cfr_b_censored_releases",
    "c2_cfr_b_skipped_releases",
)

NULL_LABEL = "(nulo)"


def same_value(a: Any, b: Any) -> bool:
    """Equality that treats NaN as null and compares floats with a tiny tolerance."""
    a = None if isinstance(a, float) and math.isnan(a) else a
    b = None if isinstance(b, float) and math.isnan(b) else b
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=0.0)
        except (TypeError, ValueError):
            return False
    return a == b


def check_invariants(
    old: Sequence[dict[str, Any]],
    new: Sequence[dict[str, Any]],
    expected_rows: int | None = None,
) -> list[str]:
    """Invariants of the regeneration of a frozen sample; empty list when all hold."""
    problems: list[str] = []
    if expected_rows is not None:
        if len(old) != expected_rows:
            problems.append(
                f"conjunto anterior tem {len(old)} linhas (esperado {expected_rows})"
            )
        if len(new) != expected_rows:
            problems.append(f"conjunto novo tem {len(new)} linhas (esperado {expected_rows})")
    if len(old) != len(new):
        problems.append(f"número de linhas mudou: {len(old)} → {len(new)}")

    old_names = [r["full_name"] for r in old]
    new_names = [r.get("full_name") for r in new]
    if len(set(new_names)) != len(new_names):
        problems.append("há repositórios duplicados no conjunto novo")
    if old_names != new_names:
        missing = sorted(set(old_names) - set(new_names))
        extra = sorted(set(new_names) - set(old_names))
        if missing or extra:
            problems.append(
                f"conjunto de repositórios mudou (faltam {len(missing)}, a mais {len(extra)})"
            )
        else:
            problems.append("a ordem dos repositórios mudou")

    schema = set(SCHEMA_COLUMNS)
    old_by_name = {r["full_name"]: r for r in old}
    for rec in new:
        name = rec.get("full_name")
        keys = set(rec)
        if keys != schema:
            problems.append(
                f"{name}: esquema incompleto "
                f"(faltam {sorted(schema - keys)}, a mais {sorted(keys - schema)})"
            )
            continue
        before = old_by_name.get(name)
        if before is not None:
            for col in METADATA_COLUMNS:
                if not same_value(before.get(col), rec.get(col)):
                    problems.append(f"{name}: coluna de metadados {col} mudou")
        for col in NEVER_NULL_COLUMNS:
            if rec.get(col) is None:
                problems.append(f"{name}: {col} nulo")
    return problems


def check_written_files(
    baseline_csv: Path | None,
    csv_path: Path,
    parquet_path: Path,
) -> list[str]:
    """Invariants of the written files: identical columns/rows and metadata text."""
    import pyarrow.parquet as pq

    problems: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        header = list(rows[0].keys()) if rows else []
    if not rows:
        with open(csv_path, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
    parquet_columns = pq.read_schema(parquet_path).names
    parquet_rows = pq.read_metadata(parquet_path).num_rows

    if header != list(SCHEMA_COLUMNS):
        problems.append("colunas do CSV diferem do esquema")
    if parquet_columns != list(SCHEMA_COLUMNS):
        problems.append("colunas do Parquet diferem do esquema")
    if parquet_rows != len(rows):
        problems.append(f"CSV tem {len(rows)} linhas e Parquet {parquet_rows}")

    if baseline_csv is not None and baseline_csv.is_file():
        with open(baseline_csv, newline="", encoding="utf-8") as f:
            old_rows = list(csv.DictReader(f))
        if len(old_rows) != len(rows):
            problems.append(f"CSV anterior tem {len(old_rows)} linhas, o novo {len(rows)}")
        else:
            for before, after in zip(old_rows, rows):
                for col in METADATA_COLUMNS:
                    if before.get(col) != after.get(col):
                        problems.append(
                            f"{after.get('full_name')}: {col} difere no texto do CSV"
                        )
    return problems


@dataclass
class ColumnComparison:
    """Before/after of one column."""

    column: str
    is_new: bool
    changed_rows: int
    nulls_before: int
    nulls_after: int
    became_null: int
    became_filled: int


@dataclass
class Comparison:
    """Everything the report needs."""

    rows: int
    columns: list[ColumnComparison] = field(default_factory=list)
    # tier column -> Counter of (before, after) for the rows where it changed
    tier_transitions: dict[str, Counter] = field(default_factory=dict)
    # (full_name, tier before, tier after, score before, score after)
    overall_changes: list[tuple[str, str, str, Any, Any]] = field(default_factory=list)
    new_columns: list[str] = field(default_factory=list)
    below_selection_criteria: list[tuple[str, int, int]] = field(default_factory=list)
    unsplittable: dict[str, int] = field(default_factory=dict)

    @property
    def changed_columns(self) -> list[ColumnComparison]:
        return [c for c in self.columns if c.changed_rows]


def compare_datasets(
    old: Sequence[dict[str, Any]],
    new: Sequence[dict[str, Any]],
    baseline_columns: Sequence[str] | None = None,
    min_releases: int = 5,
    min_workflow_runs: int = 50,
    unsplittable: dict[str, int] | None = None,
) -> Comparison:
    """Compare the dataset before and after the regeneration, row by row (by `full_name`)."""
    old_by_name = {r["full_name"]: r for r in old}
    comparison = Comparison(rows=len(new), unsplittable=dict(unsplittable or {}))
    pairs = [(old_by_name.get(r["full_name"], {}), r) for r in new]

    if baseline_columns is not None:
        comparison.new_columns = [c for c in SCHEMA_COLUMNS if c not in baseline_columns]

    for col in SCHEMA_COLUMNS:
        changed = nulls_before = nulls_after = became_null = became_filled = 0
        transitions: Counter = Counter()
        for before, after in pairs:
            a, b = before.get(col), after.get(col)
            if a is None:
                nulls_before += 1
            if b is None:
                nulls_after += 1
            if not same_value(a, b):
                changed += 1
                if b is None:
                    became_null += 1
                if a is None:
                    became_filled += 1
                if col in TIER_COLUMNS:
                    transitions[(a or NULL_LABEL, b or NULL_LABEL)] += 1
        comparison.columns.append(
            ColumnComparison(
                column=col,
                is_new=col in comparison.new_columns,
                changed_rows=changed,
                nulls_before=nulls_before,
                nulls_after=nulls_after,
                became_null=became_null,
                became_filled=became_filled,
            )
        )
        if col in TIER_COLUMNS and transitions:
            comparison.tier_transitions[col] = transitions

    for before, after in pairs:
        if not same_value(before.get("overall_dora_tier"), after.get("overall_dora_tier")):
            comparison.overall_changes.append(
                (
                    after["full_name"],
                    before.get("overall_dora_tier") or NULL_LABEL,
                    after.get("overall_dora_tier") or NULL_LABEL,
                    before.get("overall_dora_score"),
                    after.get("overall_dora_score"),
                )
            )
        releases = after.get("releases_count_window")
        runs = after.get("workflow_runs_count_window")
        if (releases is not None and releases < min_releases) or (
            runs is not None and runs < min_workflow_runs
        ):
            comparison.below_selection_criteria.append(
                (after["full_name"], releases or 0, runs or 0)
            )
    return comparison


def _fmt(value: Any) -> str:
    return NULL_LABEL if value is None else str(value)


def render_report(
    comparison: Comparison,
    problems: Sequence[str],
    *,
    generated_on: str,
    window: tuple[str, str],
    heuristic: str,
    expected_rows: int | None = None,
) -> str:
    """Markdown (pt-BR) of the comparison; `problems` are the failed invariants."""
    lines: list[str] = []
    add = lines.append
    add("# Regeneração final do dataset (Issue #56)")
    add("")
    add(
        f"Relatório gerado em {generated_on} por `pipeline.regenerar`. Compara o dataset "
        "anterior (versionado antes da regeneração) com o regenerado, coluna a coluna."
    )
    add("")
    add("## Resumo")
    add("")
    add(f"- Repositórios: {comparison.rows} (conjunto congelado; a seleção não foi refeita).")
    add(f"- Janela de observação: {window[0]} a {window[1]} (fim do dia incluído).")
    add(f"- Heurística de CFR (b): `{heuristic}`.")
    add(
        f"- Colunas do esquema: {len(SCHEMA_COLUMNS)} "
        f"({len(METADATA_COLUMNS)} de metadados preservadas, {len(METRIC_COLUMNS)} de métricas recalculadas)."
    )
    add(
        f"- Colunas de métricas com alguma linha alterada: "
        f"{len([c for c in comparison.changed_columns if c.column not in METADATA_COLUMNS])}."
    )
    add(f"- Repositórios com a faixa geral (`overall_dora_tier`) alterada: {len(comparison.overall_changes)}.")
    add("")

    add("## Invariantes")
    add("")
    if problems:
        add("**Violadas:**")
        add("")
        lines += [f"- {p}" for p in problems[:50]]
        if len(problems) > 50:
            add(f"- … e mais {len(problems) - 50}")
    else:
        rows_txt = f"{expected_rows} linhas" if expected_rows is not None else f"{comparison.rows} linhas"
        add(f"- {rows_txt}, mesmos repositórios na mesma ordem: OK")
        add("- Colunas de metadados idênticas às do dataset anterior: OK")
        add("- Esquema completo (CSV e Parquet com as mesmas colunas): OK")
    add("")

    add("## Colunas: antes × depois")
    add("")
    add("| Coluna | Linhas alteradas | Nulos antes | Nulos depois | Passou a nulo | Passou a preenchido |")
    add("|---|---:|---:|---:|---:|---:|")
    for c in comparison.columns:
        if c.column in METADATA_COLUMNS:
            continue
        name = f"`{c.column}`" + (" (nova)" if c.is_new else "")
        add(
            f"| {name} | {c.changed_rows} | {c.nulls_before} | {c.nulls_after} "
            f"| {c.became_null} | {c.became_filled} |"
        )
    add("")

    add("## Transições de faixa (tier)")
    add("")
    if not comparison.tier_transitions:
        add("Nenhuma faixa mudou.")
        add("")
    for col, counter in comparison.tier_transitions.items():
        add(f"### `{col}`")
        add("")
        add("| Antes | Depois | Repositórios |")
        add("|---|---|---:|")
        for (before, after), n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            add(f"| {before} | {after} | {n} |")
        add("")

    add("## Repositórios com a faixa geral alterada")
    add("")
    if comparison.overall_changes:
        add("| Repositório | Antes | Depois | Nota antes | Nota depois |")
        add("|---|---|---|---:|---:|")
        for name, tb, ta, sb, sa in comparison.overall_changes:
            add(f"| {name} | {tb} | {ta} | {_fmt(sb)} | {_fmt(sa)} |")
    else:
        add("Nenhum repositório mudou de faixa geral.")
    add("")

    add("## Repositórios fora dos critérios mínimos da seleção")
    add("")
    add(
        "A amostra é congelada: estes repositórios permanecem no dataset mesmo que a "
        "recoleta (janela até o fim do dia, divisão recursiva de runs) os deixe abaixo "
        "de 5 releases ou 50 runs válidos na janela."
    )
    add("")
    if comparison.below_selection_criteria:
        add("| Repositório | Releases na janela | Runs válidos na janela |")
        add("|---|---:|---:|")
        for name, releases, runs in comparison.below_selection_criteria:
            add(f"| {name} | {releases} | {runs} |")
    else:
        add("Nenhum.")
    add("")

    add("## Diagnóstico da coleta de runs")
    add("")
    if comparison.unsplittable:
        add(
            "Intervalos de 1 s ainda com ≥ 1.000 runs (caso residual da Q20): só os "
            "primeiros 1.000 são legíveis."
        )
        add("")
        add("| Repositório | Intervalos não divisíveis |")
        add("|---|---:|")
        for name, n in sorted(comparison.unsplittable.items()):
            add(f"| {name} | {n} |")
    else:
        add("Nenhum intervalo residual não divisível.")
    add("")
    return "\n".join(lines)

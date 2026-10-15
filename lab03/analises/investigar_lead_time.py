"""Diagnose repositories without lead time and cases where LT(b) > LT(a) (Issue #60).

Reads the accepted sample (`dados/repositorios.parquet`) and the persisted
releases (`dados/releases/`), recomputes lead time (a) and (b) with
`metricas.lead_time` and reports:

1. why each repository has no lead time, from the comparison status of its
   releases (first release, tag not found, release without new commits) or a
   missing releases file (clone/collection failure);
2. every repository with LT(b) > LT(a), with the evidence needed to tell a
   legitimate inversion (one release with many commits dominating the pooled
   median of variant b) from a bug (a commit older than its release's oldest
   commit, which would break the per-release invariant b ≤ a).

Execution (from `lab03/`):
    uv run python -m analises.investigar_lead_time
    uv run python -m analises.investigar_lead_time --releases-dir <dir> --saida <csv>
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow.parquet as pq

from metricas.cfr_b import parse_semver
from metricas.lead_time import calculate_lead_time, commit_lead_times, release_lead_time
from metricas.schemas import Commit, Release

STATUS_OK = "ok"
STATUS_FIRST = "first_release"
STATUS_NOT_FOUND = "not_found"

MOTIVO_SEM_ARQUIVO = "sem dados de releases (falha de clone/coleta)"
MOTIVO_LABELS = {
    STATUS_FIRST: "primeira release da história",
    STATUS_NOT_FOUND: "tag não encontrada (equivalente a 404)",
    "empty": "release sem commits novos",
}


@dataclass
class RepoDiagnostico:
    full_name: str
    releases: int
    ok_com_commits: int
    ok_sem_commits: int
    first_release: int
    not_found: int
    lead_time_a_hours: float | None
    lead_time_b_hours: float | None
    motivo_nulo: str | None
    b_maior_que_a: bool
    maior_release: str | None
    maior_release_commits: int
    total_commits: int
    fracao_commits_maior_release: float | None
    violacoes_invariante: int
    releases_fora_de_linha: int


def is_out_of_line(previous_tag: str | None, tag: str) -> bool:
    """True when the chronological predecessor has a higher SemVer (backport line).

    E.g. `v19.0.1` published after `v19.2.0`: `git log v19.2.0..v19.0.1` compares
    two maintenance lines instead of a release with its own ancestor.
    """
    if previous_tag is None:
        return False
    prev, cur = parse_semver(previous_tag), parse_semver(tag)
    return prev is not None and cur is not None and prev > cur


def load_releases(path: Path) -> list[tuple[Release, str, list[Commit]]]:
    """Releases of one repository with their status and commits, oldest first."""
    data = pq.read_table(path).to_pydict()
    rows = []
    for i, tag in enumerate(data["tag_name"]):
        release = Release(tag_name=tag, published_at=data["published_at"][i])
        commits = [
            Commit(sha=c["sha"], committed_at=c["committed_at"], message=c["message"])
            for c in data["commits"][i] or []
        ]
        release.previous_tag = data["previous_release"][i]  # type: ignore[attr-defined]
        rows.append((release, data["status"][i], commits))
    return sorted(rows, key=lambda r: r[0].published_at)


def motivo_nulo(statuses: Counter[str]) -> str:
    """Combination of reasons why no release contributed to the lead time."""
    parts = [MOTIVO_LABELS[k] for k in (STATUS_FIRST, STATUS_NOT_FOUND, "empty") if statuses[k]]
    return " + ".join(parts) if parts else "sem releases na janela"


def diagnose(full_name: str, releases_dir: Path) -> RepoDiagnostico:
    path = releases_dir / f"{full_name.replace('/', '__')}.parquet"
    if not path.is_file():
        return RepoDiagnostico(
            full_name, 0, 0, 0, 0, 0, None, None, MOTIVO_SEM_ARQUIVO, False, None, 0, 0, None, 0, 0
        )

    rows = load_releases(path)
    statuses: Counter[str] = Counter()
    for _, status, commits in rows:
        statuses["empty" if status == STATUS_OK and not commits else status] += 1

    result = calculate_lead_time(
        [(rel, commits if status == STATUS_OK else None) for rel, status, commits in rows]
    )
    a, b = result.median_a_hours, result.median_b_hours

    # Per-release invariant: every commit's lead time <= the release's lead time (a).
    violations = 0
    for rel, status, commits in rows:
        if status == STATUS_OK and commits:
            ceiling = release_lead_time(rel, commits) or 0.0
            violations += sum(v > ceiling + 1e-9 for v in commit_lead_times(rel, commits))

    ok_rows = [(rel, commits) for rel, status, commits in rows if status == STATUS_OK and commits]
    biggest = max(ok_rows, key=lambda r: len(r[1]), default=None)
    total_commits = sum(len(c) for _, c in ok_rows)

    return RepoDiagnostico(
        full_name=full_name,
        releases=len(rows),
        ok_com_commits=statuses[STATUS_OK],
        ok_sem_commits=statuses["empty"],
        first_release=statuses[STATUS_FIRST],
        not_found=statuses[STATUS_NOT_FOUND],
        lead_time_a_hours=a,
        lead_time_b_hours=b,
        motivo_nulo=motivo_nulo(statuses) if a is None else None,
        b_maior_que_a=a is not None and b is not None and b > a,
        maior_release=biggest[0].tag_name if biggest else None,
        maior_release_commits=len(biggest[1]) if biggest else 0,
        total_commits=total_commits,
        fracao_commits_maior_release=(len(biggest[1]) / total_commits) if biggest else None,
        violacoes_invariante=violations,
        releases_fora_de_linha=sum(
            is_out_of_line(rel.previous_tag, rel.tag_name)  # type: ignore[attr-defined]
            for rel, _, _ in rows
        ),
    )


def explain_inversion(full_name: str, releases_dir: Path) -> list[str]:
    """Per-release table (commits, LT a) for a manual check of one LT(b) > LT(a) case."""
    rows = load_releases(releases_dir / f"{full_name.replace('/', '__')}.parquet")
    lines = [f"  {'release':<32} {'commits':>7} {'LT(a) h':>10} {'mediana LT(b) h':>16}"]
    for rel, status, commits in rows:
        if status != STATUS_OK or not commits:
            continue
        lt_a = release_lead_time(rel, commits) or 0.0
        lt_b = statistics.median(commit_lead_times(rel, commits))
        lines.append(f"  {rel.tag_name:<32} {len(commits):>7} {lt_a:>10.1f} {lt_b:>16.1f}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default="dados/repositorios.parquet")
    parser.add_argument("--releases-dir", default="dados/releases")
    parser.add_argument("--saida", default="dados/analises/lead_time_diagnostico.csv")
    parser.add_argument("--exemplos", type=int, default=3)
    args = parser.parse_args()

    names = pq.read_table(args.dataset, columns=["full_name"]).column(0).to_pylist()
    original = pq.read_table(
        args.dataset, columns=["full_name", "lead_time_a_hours", "lead_time_b_hours"]
    ).to_pydict()
    original_null = {
        n for n, a in zip(original["full_name"], original["lead_time_a_hours"]) if a is None
    }
    original_inverted = {
        n
        for n, a, b in zip(
            original["full_name"], original["lead_time_a_hours"], original["lead_time_b_hours"]
        )
        if a is not None and b is not None and b > a
    }

    releases_dir = Path(args.releases_dir)
    diags = [diagnose(n, releases_dir) for n in names]

    out = Path(args.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(diags[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(d) for d in diags)

    nulls = [d for d in diags if d.lead_time_a_hours is None]
    inverted = [d for d in diags if d.b_maior_que_a]
    totals = Counter()
    for d in diags:
        totals.update(
            ok_com_commits=d.ok_com_commits,
            ok_sem_commits=d.ok_sem_commits,
            first_release=d.first_release,
            not_found=d.not_found,
        )

    print(f"Repositórios: {len(diags)} (releases em {releases_dir})")
    print(f"Releases por status: {dict(totals)}")
    print(f"\nLead time nulo: {len(nulls)} (no dataset original: {len(original_null)})")
    for motivo, n in Counter(d.motivo_nulo for d in nulls).most_common():
        print(f"  {n:>3}  {motivo}")
    recovered = sorted(original_null - {d.full_name for d in nulls})
    print(f"Nulos no dataset original que agora têm lead time: {len(recovered)}")

    print(f"\nLT(b) > LT(a): {len(inverted)} (no dataset original: {len(original_inverted)})")
    print(f"Violações do invariante por release (bug): {sum(d.violacoes_invariante for d in diags)}")
    if inverted:
        frac = [d.fracao_commits_maior_release for d in inverted]
        print(f"Fração dos commits na maior release (mediana): {statistics.median(frac):.2f}")
    fora = [d for d in diags if d.releases_fora_de_linha]
    print(
        f"Releases comparadas com predecessora de outra linha (SemVer maior): "
        f"{sum(d.releases_fora_de_linha for d in diags)} em {len(fora)} repositórios "
        f"({sum(d.b_maior_que_a for d in fora)} deles com LT(b) > LT(a))"
    )
    for d in sorted(inverted, key=lambda d: -d.fracao_commits_maior_release)[: args.exemplos]:
        print(
            f"\n{d.full_name}: LT(a) = {d.lead_time_a_hours:.1f} h, "
            f"LT(b) = {d.lead_time_b_hours:.1f} h, maior release {d.maior_release} "
            f"com {d.maior_release_commits}/{d.total_commits} commits"
        )
        print("\n".join(explain_inversion(d.full_name, releases_dir)))

    print(f"\nDiagnóstico por repositório: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

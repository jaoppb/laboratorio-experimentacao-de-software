"""Funnel tracking and export for Lab03 repository selection.

Fulfills requirements of Issue #31 and T4 (Metodologia) of guialab03.md:
- Records each stage of candidate repository filtering
- Tracks remaining counts, discards, and discard reasons
- Exports dados/funil.csv
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunnelStage:
    """Represents a single step in the repository filtering funnel."""

    etapa: str
    quantidade_restante: int
    descartados: int
    motivo_descarte: str


class FunnelTracker:
    """Tracks and records selection funnel counts and exports to CSV."""

    def __init__(self) -> None:
        self.stages: list[FunnelStage] = []

    def record_stage(
        self,
        etapa: str,
        quantidade_restante: int,
        descartados: int = 0,
        motivo_descarte: str = "-",
    ) -> FunnelStage:
        """Record a milestone stage in the filtering funnel."""
        stage = FunnelStage(
            etapa=etapa,
            quantidade_restante=quantidade_restante,
            descartados=descartados,
            motivo_descarte=motivo_descarte,
        )
        self.stages.append(stage)
        return stage

    def export_csv(self, output_path: str | Path) -> Path:
        """Export the funnel data to a CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["etapa", "quantidade_restante", "descartados", "motivo_descarte"]
            )
            for s in self.stages:
                writer.writerow(
                    [
                        s.etapa,
                        s.quantidade_restante,
                        s.descartados,
                        s.motivo_descarte,
                    ]
                )

        return path

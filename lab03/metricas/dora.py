"""Calculation of Deployment Frequency and DORA performance tier classification.

Follows the official specifications of Lab03 (guialab03.md):
- Deployment Frequency = releases publicadas / 52.1 semanas
- Classification into Elite, High, Medium, Low for each of the 4 DORA metrics
- Overall classification = median of the 4 tier scores (4, 3, 2, 1), rounded down
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metricas.schemas import Release


class DORATier(str, Enum):
    """DORA performance tiers."""

    ELITE = "Elite"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


TIER_POINTS: dict[DORATier, int] = {
    DORATier.ELITE: 4,
    DORATier.HIGH: 3,
    DORATier.MEDIUM: 2,
    DORATier.LOW: 1,
}

POINTS_TO_TIER: dict[int, DORATier] = {
    4: DORATier.ELITE,
    3: DORATier.HIGH,
    2: DORATier.MEDIUM,
    1: DORATier.LOW,
}

# Number of weeks in a 12-month observation window
DEFAULT_WINDOW_WEEKS: float = 52.1

# Minimum frequency threshold for ">= 1 por mês" (12 months in 52.1 weeks)
MONTHLY_FREQ_THRESHOLD: float = 12.0 / 52.1


def calculate_deployment_frequency(
    releases: Sequence[Release],
    window_weeks: float = DEFAULT_WINDOW_WEEKS,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> float:
    """Calculate deployment frequency in published releases per week.

    Only releases with `draft == False` and `prerelease == False` are counted.
    If `start_date` and `end_date` are provided, only releases published within
    the observation window are considered.
    """
    if window_weeks <= 0:
        raise ValueError("window_weeks must be greater than zero")

    valid_releases = 0
    for rel in releases:
        if rel.draft or rel.prerelease:
            continue
        if start_date is not None and rel.published_at < start_date:
            continue
        if end_date is not None and rel.published_at > end_date:
            continue
        valid_releases += 1

    return valid_releases / window_weeks


def classify_deployment_frequency(freq: float) -> DORATier:
    """Classify deployment frequency (releases/week) according to Lab03 reference table.

    - Elite: >= 7 por semana (≈ diária ou mais)
    - High: >= 1 e < 7 por semana
    - Medium: >= 1 por mês (≈ 12/52.1) e < 1 por semana
    - Low: < 1 por mês (< 12/52.1)
    """
    if freq >= 7.0:
        return DORATier.ELITE
    if freq >= 1.0:
        return DORATier.HIGH
    if freq >= MONTHLY_FREQ_THRESHOLD:
        return DORATier.MEDIUM
    return DORATier.LOW


def classify_lead_time(lead_time_days: float | None) -> DORATier:
    """Classify median lead time for changes (in days) according to Lab03 reference table.

    - Elite: < 1 dia
    - High: 1 dia a < 1 semana (7 dias)
    - Medium: 1 semana a < 30 dias
    - Low: >= 30 dias (ou se ausente/não mensurável)
    """
    if lead_time_days is None or lead_time_days < 0:
        return DORATier.LOW
    if lead_time_days < 1.0:
        return DORATier.ELITE
    if lead_time_days < 7.0:
        return DORATier.HIGH
    if lead_time_days < 30.0:
        return DORATier.MEDIUM
    return DORATier.LOW


def classify_change_failure_rate(cfr: float | None) -> DORATier:
    """Classify Change Failure Rate (ratio between 0.0 and 1.0) according to Lab03 table.

    - Elite: <= 15% (<= 0.15)
    - High: > 15% e <= 30%
    - Medium: > 30% e <= 45%
    - Low: > 45% (ou se ausente)
    """
    if cfr is None or cfr < 0:
        return DORATier.LOW
    if cfr <= 0.15:
        return DORATier.ELITE
    if cfr <= 0.30:
        return DORATier.HIGH
    if cfr <= 0.45:
        return DORATier.MEDIUM
    return DORATier.LOW


def classify_recovery_time(recovery_hours: float | None) -> DORATier:
    """Classify median recovery time (in hours) according to Lab03 reference table.

    - Elite: < 1 hora
    - High: 1 hora a < 1 dia (24 horas)
    - Medium: 1 dia a < 1 semana (168 horas)
    - Low: >= 1 semana (ou se ausente/censurado sem resolução)
    """
    if recovery_hours is None or recovery_hours < 0:
        return DORATier.LOW
    if recovery_hours < 1.0:
        return DORATier.ELITE
    if recovery_hours < 24.0:
        return DORATier.HIGH
    if recovery_hours < 168.0:
        return DORATier.MEDIUM
    return DORATier.LOW


def calculate_overall_dora_score(scores: Sequence[int]) -> tuple[int, DORATier]:
    """Calculate the overall DORA rating from individual scores.

    Point scale:
    - Elite = 4
    - High = 3
    - Medium = 2
    - Low = 1

    The overall rating is the median of the four scores, rounded down.
    Example: (4, 3, 3, 1) -> median 3.0 -> rounded down 3 -> High.
    """
    if not scores:
        raise ValueError("scores sequence must not be empty")

    for s in scores:
        if s not in (1, 2, 3, 4):
            raise ValueError(f"Each score must be an integer between 1 and 4, got {s}")

    med = statistics.median(scores)
    rounded_score = int(math.floor(med))
    # Guarantee bounded within 1 and 4
    bounded_score = max(1, min(4, rounded_score))
    return bounded_score, POINTS_TO_TIER[bounded_score]


@dataclass
class DORAEvaluation:
    """Full evaluation of a repository across all 4 DORA metrics."""

    deployment_frequency: float
    deployment_tier: DORATier
    lead_time_days: float | None
    lead_time_tier: DORATier
    cfr: float | None
    cfr_tier: DORATier
    recovery_hours: float | None
    recovery_tier: DORATier
    scores: tuple[int, int, int, int]
    overall_score: int
    overall_tier: DORATier


def evaluate_repository_dora(
    deployment_frequency: float,
    lead_time_days: float | None,
    cfr: float | None,
    recovery_hours: float | None,
) -> DORAEvaluation:
    """Evaluate all 4 DORA metrics for a repository and return the overall DORA tier."""
    dep_tier = classify_deployment_frequency(deployment_frequency)
    lead_tier = classify_lead_time(lead_time_days)
    cfr_tier = classify_change_failure_rate(cfr)
    rec_tier = classify_recovery_time(recovery_hours)

    scores = (
        TIER_POINTS[dep_tier],
        TIER_POINTS[lead_tier],
        TIER_POINTS[cfr_tier],
        TIER_POINTS[rec_tier],
    )

    overall_score, overall_tier = calculate_overall_dora_score(scores)

    return DORAEvaluation(
        deployment_frequency=deployment_frequency,
        deployment_tier=dep_tier,
        lead_time_days=lead_time_days,
        lead_time_tier=lead_tier,
        cfr=cfr,
        cfr_tier=cfr_tier,
        recovery_hours=recovery_hours,
        recovery_tier=rec_tier,
        scores=scores,
        overall_score=overall_score,
        overall_tier=overall_tier,
    )

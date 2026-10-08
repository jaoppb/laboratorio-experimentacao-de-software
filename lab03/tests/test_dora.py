"""Unit tests for Deployment Frequency calculation and DORA classification.

Follows requirements of Issue #32:
- deployment_frequency: releases publicadas / 52.1 semanas
- Classificação Elite/High/Medium/Low pela tabela do enunciado
- Classificação geral: mediana das 4 notas, arredondada para baixo
- Testes: (4, 3, 3, 1) -> High; valores nos limites das faixas; repositório com 0 releases
"""

from datetime import datetime, timezone

import pytest
from metricas.dora import (
    DEFAULT_WINDOW_WEEKS,
    MONTHLY_FREQ_THRESHOLD,
    DORAEvaluation,
    DORATier,
    calculate_deployment_frequency,
    calculate_overall_dora_score,
    classify_change_failure_rate,
    classify_deployment_frequency,
    classify_lead_time,
    classify_recovery_time,
    evaluate_repository_dora,
)
from metricas.schemas import Release


class TestDeploymentFrequencyCalculation:
    """Tests for calculate_deployment_frequency."""

    def test_repository_with_zero_releases(self):
        """Repository with 0 releases should yield 0.0 frequency."""
        freq = calculate_deployment_frequency([])
        assert freq == 0.0

    def test_repository_with_valid_releases(self):
        """Calculate frequency correctly over default 52.1 weeks."""
        releases = [
            Release(tag_name=f"v1.{i}.0", published_at=f"2026-0{i+1}-01T00:00:00Z")
            for i in range(5)
        ]
        freq = calculate_deployment_frequency(releases)
        assert pytest.approx(freq) == 5 / 52.1

    def test_ignores_drafts_and_prereleases(self):
        """Drafts and prereleases must be ignored in primary deployment frequency."""
        releases = [
            Release(tag_name="v1.0.0", published_at="2026-01-01T00:00:00Z", draft=False, prerelease=False),
            Release(tag_name="v1.1.0-rc1", published_at="2026-02-01T00:00:00Z", draft=False, prerelease=True),
            Release(tag_name="v1.2.0-draft", published_at="2026-03-01T00:00:00Z", draft=True, prerelease=False),
            Release(tag_name="v2.0.0", published_at="2026-04-01T00:00:00Z", draft=False, prerelease=False),
        ]
        freq = calculate_deployment_frequency(releases, window_weeks=52.1)
        assert pytest.approx(freq) == 2 / 52.1

    def test_filters_by_observation_window(self):
        """Releases outside start_date and end_date must be excluded."""
        start = datetime(2025, 10, 1, tzinfo=timezone.utc)
        end = datetime(2026, 9, 30, tzinfo=timezone.utc)

        releases = [
            Release(tag_name="v0.9.0", published_at="2025-09-15T00:00:00Z"),  # before window
            Release(tag_name="v1.0.0", published_at="2025-10-15T00:00:00Z"),  # inside
            Release(tag_name="v1.1.0", published_at="2026-05-15T00:00:00Z"),  # inside
            Release(tag_name="v2.0.0", published_at="2026-10-05T00:00:00Z"),  # after window
        ]
        freq = calculate_deployment_frequency(releases, start_date=start, end_date=end)
        assert pytest.approx(freq) == 2 / DEFAULT_WINDOW_WEEKS

    def test_invalid_window_weeks_raises_value_error(self):
        """window_weeks <= 0 must raise ValueError."""
        with pytest.raises(ValueError, match="greater than zero"):
            calculate_deployment_frequency([], window_weeks=0)
        with pytest.raises(ValueError, match="greater than zero"):
            calculate_deployment_frequency([], window_weeks=-10)


class TestDORATierClassifications:
    """Tests for classifying individual DORA metrics and checking threshold boundaries."""

    def test_deployment_frequency_tier_boundaries(self):
        # Elite: >= 7 por semana
        assert classify_deployment_frequency(7.0) == DORATier.ELITE
        assert classify_deployment_frequency(10.5) == DORATier.ELITE

        # High: >= 1 e < 7 por semana
        assert classify_deployment_frequency(6.999) == DORATier.HIGH
        assert classify_deployment_frequency(1.0) == DORATier.HIGH

        # Medium: >= 1 por mês (MONTHLY_FREQ_THRESHOLD) e < 1 por semana
        assert classify_deployment_frequency(0.999) == DORATier.MEDIUM
        assert classify_deployment_frequency(MONTHLY_FREQ_THRESHOLD) == DORATier.MEDIUM

        # Low: < 1 por mês
        assert classify_deployment_frequency(MONTHLY_FREQ_THRESHOLD - 0.001) == DORATier.LOW
        assert classify_deployment_frequency(0.0) == DORATier.LOW

    def test_lead_time_tier_boundaries(self):
        # Elite: < 1 dia
        assert classify_lead_time(0.0) == DORATier.ELITE
        assert classify_lead_time(0.999) == DORATier.ELITE

        # High: 1 dia a < 1 semana (7 dias)
        assert classify_lead_time(1.0) == DORATier.HIGH
        assert classify_lead_time(6.999) == DORATier.HIGH

        # Medium: 1 semana a < 30 dias
        assert classify_lead_time(7.0) == DORATier.MEDIUM
        assert classify_lead_time(29.999) == DORATier.MEDIUM

        # Low: >= 30 dias ou None ou negativo
        assert classify_lead_time(30.0) == DORATier.LOW
        assert classify_lead_time(60.0) == DORATier.LOW
        assert classify_lead_time(None) == DORATier.LOW
        assert classify_lead_time(-1.0) == DORATier.LOW

    def test_change_failure_rate_tier_boundaries(self):
        # Elite: <= 15% (0.15)
        assert classify_change_failure_rate(0.0) == DORATier.ELITE
        assert classify_change_failure_rate(0.15) == DORATier.ELITE

        # High: > 15% e <= 30%
        assert classify_change_failure_rate(0.15001) == DORATier.HIGH
        assert classify_change_failure_rate(0.30) == DORATier.HIGH

        # Medium: > 30% e <= 45%
        assert classify_change_failure_rate(0.30001) == DORATier.MEDIUM
        assert classify_change_failure_rate(0.45) == DORATier.MEDIUM

        # Low: > 45% ou None ou negativo
        assert classify_change_failure_rate(0.45001) == DORATier.LOW
        assert classify_change_failure_rate(1.0) == DORATier.LOW
        assert classify_change_failure_rate(None) == DORATier.LOW
        assert classify_change_failure_rate(-0.5) == DORATier.LOW

    def test_recovery_time_tier_boundaries(self):
        # Elite: < 1 hora
        assert classify_recovery_time(0.0) == DORATier.ELITE
        assert classify_recovery_time(0.999) == DORATier.ELITE

        # High: 1 hora a < 1 dia (24 horas)
        assert classify_recovery_time(1.0) == DORATier.HIGH
        assert classify_recovery_time(23.999) == DORATier.HIGH

        # Medium: 1 dia a < 1 semana (168 horas)
        assert classify_recovery_time(24.0) == DORATier.MEDIUM
        assert classify_recovery_time(167.999) == DORATier.MEDIUM

        # Low: >= 1 semana ou None ou negativo
        assert classify_recovery_time(168.0) == DORATier.LOW
        assert classify_recovery_time(500.0) == DORATier.LOW
        assert classify_recovery_time(None) == DORATier.LOW
        assert classify_recovery_time(-2.0) == DORATier.LOW


class TestOverallDORAClassification:
    """Tests for calculate_overall_dora_score according to issue and guide specs."""

    def test_enunciado_example_4_3_3_1(self):
        """As specified in Issue #32 and guide: (4, 3, 3, 1) -> median 3 -> High."""
        score, tier = calculate_overall_dora_score([4, 3, 3, 1])
        assert score == 3
        assert tier == DORATier.HIGH

    def test_rounding_down_median(self):
        """When median is a half value (e.g. 3.5 or 2.5), it must round down."""
        # (4, 4, 3, 2) -> sorted [2, 3, 4, 4] -> median (3+4)/2 = 3.5 -> floor(3.5) = 3 (High)
        score, tier = calculate_overall_dora_score([4, 4, 3, 2])
        assert score == 3
        assert tier == DORATier.HIGH

        # (4, 3, 2, 1) -> sorted [1, 2, 3, 4] -> median (2+3)/2 = 2.5 -> floor(2.5) = 2 (Medium)
        score, tier = calculate_overall_dora_score([4, 3, 2, 1])
        assert score == 2
        assert tier == DORATier.MEDIUM

    def test_all_elite(self):
        score, tier = calculate_overall_dora_score([4, 4, 4, 4])
        assert score == 4
        assert tier == DORATier.ELITE

    def test_all_low(self):
        score, tier = calculate_overall_dora_score([1, 1, 1, 1])
        assert score == 1
        assert tier == DORATier.LOW

    def test_medium_ratings(self):
        score, tier = calculate_overall_dora_score([2, 2, 2, 1])
        assert score == 2
        assert tier == DORATier.MEDIUM

    def test_empty_scores_raises_value_error(self):
        with pytest.raises(ValueError, match="must not be empty"):
            calculate_overall_dora_score([])

    def test_invalid_score_value_raises_value_error(self):
        with pytest.raises(ValueError, match="between 1 and 4"):
            calculate_overall_dora_score([5, 3, 2, 1])
        with pytest.raises(ValueError, match="between 1 and 4"):
            calculate_overall_dora_score([0, 3, 2, 1])


class TestEvaluateRepositoryDORA:
    """Full repository evaluation integration tests."""

    def test_evaluate_full_repository_enunciado(self):
        # Repositório com:
        # deployment_freq = 8.0 (Elite = 4)
        # lead_time = 3 dias (High = 3)
        # cfr = 0.20 (High = 3)
        # recovery_time = 200 horas (Low = 1)
        # Notas: (4, 3, 3, 1) -> High (3)
        evaluation = evaluate_repository_dora(
            deployment_frequency=8.0,
            lead_time_days=3.0,
            cfr=0.20,
            recovery_hours=200.0,
        )
        assert evaluation.deployment_tier == DORATier.ELITE
        assert evaluation.lead_time_tier == DORATier.HIGH
        assert evaluation.cfr_tier == DORATier.HIGH
        assert evaluation.recovery_tier == DORATier.LOW
        assert evaluation.scores == (4, 3, 3, 1)
        assert evaluation.overall_score == 3
        assert evaluation.overall_tier == DORATier.HIGH

    def test_evaluate_repository_with_zero_releases_and_missing_data(self):
        # Repo com 0 releases e sem dados de estabilidade
        evaluation = evaluate_repository_dora(
            deployment_frequency=0.0,
            lead_time_days=None,
            cfr=None,
            recovery_hours=None,
        )
        assert evaluation.deployment_tier == DORATier.LOW
        assert evaluation.lead_time_tier == DORATier.LOW
        assert evaluation.cfr_tier == DORATier.LOW
        assert evaluation.recovery_tier == DORATier.LOW
        assert evaluation.scores == (1, 1, 1, 1)
        assert evaluation.overall_score == 1
        assert evaluation.overall_tier == DORATier.LOW

    def test_repo_schema_with_metadata_and_created_at(self):
        from metricas.schemas import Repo
        r = Repo(
            owner="owner",
            name="repo",
            stars=100,
            language="Python",
            created_at="2024-01-01T00:00:00Z",
            contributors_count=15,
        )
        assert r.language == "Python"
        assert r.contributors_count == 15
        assert isinstance(r.created_at, datetime)
        assert r.created_at.tzinfo is not None



"""Data schemas for Lab03 metrics and pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _parse_datetime(dt_val: datetime | str | None) -> datetime | None:
    """Parse datetime or ISO 8601 string into a timezone-aware UTC datetime."""
    if dt_val is None:
        return None
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val
    if isinstance(dt_val, str):
        cleaned = dt_val.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    raise TypeError(f"Expected datetime or str, got {type(dt_val).__name__}")


@dataclass
class WorkflowRun:
    """Represents a single GitHub Actions workflow run."""

    workflow_id: int | str
    conclusion: str | None
    run_started_at: datetime | str
    updated_at: datetime | str
    id: int | str | None = None
    name: str | None = None
    event: str | None = None
    branch: str | None = None

    def __post_init__(self) -> None:
        parsed_started = _parse_datetime(self.run_started_at)
        parsed_updated = _parse_datetime(self.updated_at)
        if parsed_started is None or parsed_updated is None:
            raise ValueError("run_started_at and updated_at must not be None")
        self.run_started_at = parsed_started
        self.updated_at = parsed_updated


@dataclass
class Repo:
    """Baseline dataclass for repository metadata."""

    owner: str
    name: str
    default_branch: str = "main"
    stars: int = 0
    language: str | None = None
    created_at: datetime | str | None = None
    contributors_count: int = 0
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.created_at is not None:
            self.created_at = _parse_datetime(self.created_at)



@dataclass
class Release:
    """Baseline stub for repository release data."""

    tag_name: str
    published_at: datetime | str
    draft: bool = False
    prerelease: bool = False

    def __post_init__(self) -> None:
        parsed = _parse_datetime(self.published_at)
        if parsed is None:
            raise ValueError("published_at must not be None")
        self.published_at = parsed


@dataclass
class Commit:
    """Baseline stub for commit data between releases."""

    sha: str
    committed_at: datetime | str
    message: str = ""

    def __post_init__(self) -> None:
        parsed = _parse_datetime(self.committed_at)
        if parsed is None:
            raise ValueError("committed_at must not be None")
        self.committed_at = parsed

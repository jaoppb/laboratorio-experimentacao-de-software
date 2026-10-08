"""Pytest configuration for lab03 tests."""

import pytest


@pytest.fixture(autouse=True)
def _default_disable_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable default global cache in tests to avoid disk pollution and shared state.

    Tests that test caching can pass `cache=...` or `cache_path=tmp_path / '...'`.
    """
    monkeypatch.setenv("DISABLE_CACHE", "1")

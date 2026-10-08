"""Unit tests for SQLite-backed HttpCache (pipeline.cache)."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from pipeline.cache import HttpCache


def test_cache_init_and_wal_mode(tmp_path: Path):
    """Verify HttpCache creates database, parent directories, and configures WAL journal mode."""
    db_file = tmp_path / "sub" / "test_cache.sqlite"
    assert not db_file.exists()

    with HttpCache(db_file) as cache:
        assert db_file.exists()
        cursor = cache._conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"


def test_cache_compute_key_canonicalization():
    """Verify compute_key canonicalizes query parameters deterministically."""
    url = "https://api.github.com/repos/owner/repo/pulls"
    key1 = HttpCache.compute_key(url, params={"state": "closed", "per_page": 100})
    key2 = HttpCache.compute_key(url, params={"per_page": 100, "state": "closed"})
    assert key1 == key2
    assert "per_page=100" in key1
    assert "state=closed" in key1


def test_cache_miss_and_hit(tmp_path: Path):
    """Verify cache miss returns None and cache hit reconstructs complete httpx.Response."""
    cache = HttpCache(tmp_path / "cache.sqlite")
    key = "https://api.github.com/users/octocat"

    assert cache.get(key) is None

    mock_resp = httpx.Response(
        200,
        headers={
            "Content-Type": "application/json",
            "Link": '<https://api.github.com/users?page=2>; rel="next"',
        },
        json={"login": "octocat", "id": 1},
        request=httpx.Request("GET", key),
    )

    cache.set(key, key, mock_resp)
    assert cache.count() == 1

    cached = cache.get(key)
    assert cached is not None
    assert cached.status_code == 200
    assert cached.json() == {"login": "octocat", "id": 1}
    assert cached.headers["Link"] == '<https://api.github.com/users?page=2>; rel="next"'
    assert cached.headers["X-Cache"] == "HIT"
    assert cached.links["next"]["url"] == "https://api.github.com/users?page=2"
    cache.close()


def test_cache_ignores_non_2xx(tmp_path: Path):
    """Verify that transient errors (5xx) and rate limits (403, 429) are never saved."""
    cache = HttpCache(tmp_path / "cache.sqlite")

    for status in [401, 403, 404, 429, 500, 502, 503]:
        url = f"https://api.github.com/status/{status}"
        resp = httpx.Response(status, json={"error": True})
        cache.set(url, url, resp)
        assert cache.get(url) is None

    assert cache.count() == 0
    cache.close()


def test_cache_persistence_across_reconnect(tmp_path: Path):
    """Verify that cached data survives process restart / reconnection to the SQLite file."""
    db_file = tmp_path / "persisted.sqlite"

    with HttpCache(db_file) as cache1:
        resp = httpx.Response(200, text="saved-content")
        cache1.set("http://test.local", "http://test.local", resp)
        assert cache1.count() == 1

    # Simulate process restart by opening fresh cache instance
    with HttpCache(db_file) as cache2:
        assert cache2.count() == 1
        cached = cache2.get("http://test.local")
        assert cached is not None
        assert cached.text == "saved-content"


def test_cache_clear(tmp_path: Path):
    """Verify clear() purges all records."""
    cache = HttpCache(tmp_path / "cache.sqlite")
    cache.set("k1", "http://k1", httpx.Response(200, json={"k": 1}))
    cache.set("k2", "http://k2", httpx.Response(200, json={"k": 2}))
    assert cache.count() == 2

    cache.clear()
    assert cache.count() == 0
    assert cache.get("k1") is None
    cache.close()


def test_cache_multithreaded_concurrent_access(tmp_path: Path):
    """Verify thread-safe concurrent reads and writes without database lock contention."""
    cache = HttpCache(tmp_path / "concurrent.sqlite")

    def worker(i: int) -> None:
        key = f"http://test.local/{i}"
        resp = httpx.Response(200, json={"worker": i})
        cache.set(key, key, resp)
        cached = cache.get(key)
        assert cached is not None
        assert cached.json() == {"worker": i}

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(50)))

    assert cache.count() == 50
    cache.close()

"""Unit tests for SQLite-backed HttpCache (pipeline.cache)."""

import asyncio
from pathlib import Path

import httpx
from pipeline.cache import HttpCache


async def test_cache_init_and_wal_mode(tmp_path: Path):
    """Verify HttpCache creates database, parent directories, and configures WAL journal mode."""
    db_file = tmp_path / "sub" / "test_cache.sqlite"
    assert not db_file.exists()

    async with HttpCache(db_file) as cache:
        assert db_file.exists()
        assert cache._conn is not None
        async with cache._conn.execute("PRAGMA journal_mode;") as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[0].lower() == "wal"


def test_cache_compute_key_canonicalization():
    """Verify compute_key canonicalizes query parameters deterministically."""
    url = "https://api.github.com/repos/owner/repo/pulls"
    key1 = HttpCache.compute_key(url, params={"state": "closed", "per_page": 100})
    key2 = HttpCache.compute_key(url, params={"per_page": 100, "state": "closed"})
    assert key1 == key2
    assert "per_page=100" in key1
    assert "state=closed" in key1


async def test_cache_miss_and_hit(tmp_path: Path):
    """Verify cache miss returns None and cache hit reconstructs complete httpx.Response."""
    cache = HttpCache(tmp_path / "cache.sqlite")
    key = "https://api.github.com/users/octocat"

    assert await cache.get(key) is None

    mock_resp = httpx.Response(
        200,
        headers={
            "Content-Type": "application/json",
            "Link": '<https://api.github.com/users?page=2>; rel="next"',
        },
        json={"login": "octocat", "id": 1},
        request=httpx.Request("GET", key),
    )

    await cache.set(key, key, mock_resp)
    assert await cache.count() == 1

    cached = await cache.get(key)
    assert cached is not None
    assert cached.status_code == 200
    assert cached.json() == {"login": "octocat", "id": 1}
    assert cached.headers["Link"] == '<https://api.github.com/users?page=2>; rel="next"'
    assert cached.headers["X-Cache"] == "HIT"
    assert cached.links["next"]["url"] == "https://api.github.com/users?page=2"
    await cache.close()


async def test_cache_ignores_non_2xx(tmp_path: Path):
    """Verify that transient errors (5xx) and rate limits (403, 429) are never saved."""
    cache = HttpCache(tmp_path / "cache.sqlite")

    for status in [401, 403, 404, 429, 500, 502, 503]:
        url = f"https://api.github.com/status/{status}"
        resp = httpx.Response(status, json={"error": True})
        await cache.set(url, url, resp)
        assert await cache.get(url) is None

    assert await cache.count() == 0
    await cache.close()


async def test_cache_persistence_across_reconnect(tmp_path: Path):
    """Verify that cached data survives process restart / reconnection to the SQLite file."""
    db_file = tmp_path / "persisted.sqlite"

    async with HttpCache(db_file) as cache1:
        resp = httpx.Response(200, text="saved-content")
        await cache1.set("http://test.local", "http://test.local", resp)
        assert await cache1.count() == 1

    # Simulate process restart by opening fresh cache instance
    async with HttpCache(db_file) as cache2:
        assert await cache2.count() == 1
        cached = await cache2.get("http://test.local")
        assert cached is not None
        assert cached.text == "saved-content"


async def test_cache_clear(tmp_path: Path):
    """Verify clear() purges all records."""
    cache = HttpCache(tmp_path / "cache.sqlite")
    await cache.set("k1", "http://k1", httpx.Response(200, json={"k": 1}))
    await cache.set("k2", "http://k2", httpx.Response(200, json={"k": 2}))
    assert await cache.count() == 2

    await cache.clear()
    assert await cache.count() == 0
    assert await cache.get("k1") is None
    await cache.close()


async def test_cache_concurrent_access(tmp_path: Path):
    """Verify async concurrent reads and writes without database lock contention."""
    cache = HttpCache(tmp_path / "concurrent.sqlite")

    async def worker(i: int) -> None:
        key = f"http://test.local/{i}"
        resp = httpx.Response(200, json={"worker": i})
        await cache.set(key, key, resp)
        cached = await cache.get(key)
        assert cached is not None
        assert cached.json() == {"worker": i}

    await asyncio.gather(*[worker(i) for i in range(50)])

    assert await cache.count() == 50
    await cache.close()

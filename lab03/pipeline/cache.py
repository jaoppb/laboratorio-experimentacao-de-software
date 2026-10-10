"""SQLite-backed async disk cache for HTTP requests with WAL mode using aiosqlite."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Self

import aiosqlite
import httpx

logger = logging.getLogger(__name__)


class HttpCache:
    """Async thread-safe SQLite persistent cache for HTTP responses using aiosqlite.

    Features:
    - WAL mode enabled for high concurrency and resilience to abrupt interruptions.
    - Immediate commit per write to guarantee durability across pipeline restarts.
    - Transparently reconstructs complete `httpx.Response` instances.
    - Caches successful 2xx responses and ignores transient errors (5xx, 403, 429).
    """

    def __init__(self, db_path: Path | str = "cache/http_cache.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to SQLite database asynchronously and configure PRAGMAs."""
        if self._conn is not None:
            return
        async with self._lock:
            if self._conn is None:
                self._conn = await aiosqlite.connect(str(self.db_path), timeout=30.0)
                await self._conn.execute("PRAGMA journal_mode=WAL;")
                await self._conn.execute("PRAGMA synchronous=NORMAL;")
                await self._init_schema()

    async def _init_schema(self) -> None:
        """Initialize database schema if not present."""
        if self._conn is None:
            return
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS http_cache (
                key TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                headers TEXT NOT NULL,
                content BLOB NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        await self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_http_cache_created
            ON http_cache(created_at);
            """
        )
        await self._conn.commit()

    @staticmethod
    def compute_key(url: str, params: dict[str, Any] | None = None) -> str:
        """Derive a canonical cache key from URL and query parameters with sorted keys."""
        from urllib.parse import urlencode

        req_url = httpx.URL(url)
        all_params: list[tuple[str, str]] = list(req_url.params.multi_items())

        if params:
            for k, v in params.items():
                if isinstance(v, (list, tuple)):
                    for item in v:
                        all_params.append((str(k), str(item)))
                else:
                    all_params.append((str(k), str(v)))

        base_url = str(req_url.copy_with(query=None))
        if not all_params:
            return base_url

        sorted_params = sorted(all_params, key=lambda item: (item[0], item[1]))
        return f"{base_url}?{urlencode(sorted_params)}"

    async def get(self, key: str) -> httpx.Response | None:
        """Retrieve a cached HTTP response if present, reconstructed as httpx.Response."""
        await self.connect()
        assert self._conn is not None

        async with self._lock:
            async with self._conn.execute(
                "SELECT url, status_code, headers, content FROM http_cache WHERE key = ?",
                (key,),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return None

        cached_url, status_code, headers_json, content = row
        try:
            raw_headers = json.loads(headers_json)
        except json.JSONDecodeError:
            logger.warning("Corrupted headers in cache for key %s", key)
            return None

        headers = {
            k: v
            for k, v in raw_headers.items()
            if k.lower() not in ("content-encoding", "content-length")
        }
        headers["X-Cache"] = "HIT"

        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=content,
            request=httpx.Request("GET", cached_url),
        )

    async def set(
        self,
        key: str,
        url: str,
        response: httpx.Response,
        force: bool = False,
    ) -> None:
        """Persist response into cache if status code is 2xx (or forced)."""
        if not force and not (200 <= response.status_code < 300):
            return

        headers_to_store = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in ("x-cache", "content-encoding", "content-length")
        }
        headers_json = json.dumps(headers_to_store)
        now = time.time()

        await self.connect()
        assert self._conn is not None

        async with self._lock:
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO http_cache (key, url, status_code, headers, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    url,
                    response.status_code,
                    headers_json,
                    response.content,
                    now,
                ),
            )
            await self._conn.commit()

    async def clear(self) -> None:
        """Clear all cached responses from the database."""
        await self.connect()
        assert self._conn is not None

        async with self._lock:
            await self._conn.execute("DELETE FROM http_cache;")
            await self._conn.commit()

    async def count(self) -> int:
        """Return the number of cached entries."""
        await self.connect()
        assert self._conn is not None

        async with self._lock:
            async with self._conn.execute("SELECT COUNT(*) FROM http_cache;") as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row else 0

    async def close(self) -> None:
        """Close database connection."""
        async with self._lock:
            if self._conn is not None:
                await self._conn.close()
                self._conn = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

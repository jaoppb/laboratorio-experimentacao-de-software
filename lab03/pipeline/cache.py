"""SQLite-backed disk cache for HTTP requests with WAL mode and crash resilience."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)


class HttpCache:
    """Thread-safe SQLite persistent cache for HTTP responses.

    Features:
    - WAL mode enabled for high concurrency and resilience to abrupt interruptions (Ctrl+C).
    - Immediate commit per write to guarantee durability across pipeline restarts.
    - Transparently reconstructs complete `httpx.Response` instances (status, headers, body).
    - Caches successful 2xx responses and ignores transient errors (5xx, 403, 429).
    """

    def __init__(self, db_path: Path | str = "cache/http_cache.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize SQLite database schema if not present."""
        with self._lock:
            self._conn.execute(
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
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_http_cache_created
                ON http_cache(created_at);
                """
            )
            self._conn.commit()

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

    def get(self, key: str) -> httpx.Response | None:
        """Retrieve a cached HTTP response if present, reconstructed as httpx.Response."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT url, status_code, headers, content FROM http_cache WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        cached_url, status_code, headers_json, content = row
        try:
            raw_headers = json.loads(headers_json)
        except json.JSONDecodeError:
            logger.warning("Corrupted headers in cache for key %s", key)
            return None

        # Reconstructed headers include X-Cache indicator
        headers = dict(raw_headers)
        headers["X-Cache"] = "HIT"

        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=content,
            request=httpx.Request("GET", cached_url),
        )

    def set(
        self,
        key: str,
        url: str,
        response: httpx.Response,
        force: bool = False,
    ) -> None:
        """Persist response into cache if status code is 2xx (or forced)."""
        if not force and not (200 <= response.status_code < 300):
            return

        # Prepare serializable headers dictionary, omitting temporary cache flags
        headers_to_store = {
            k: v for k, v in response.headers.items() if k.lower() != "x-cache"
        }
        headers_json = json.dumps(headers_to_store)
        now = time.time()

        with self._lock:
            self._conn.execute(
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
            self._conn.commit()

    def clear(self) -> None:
        """Clear all cached responses from the database."""
        with self._lock:
            self._conn.execute("DELETE FROM http_cache;")
            self._conn.commit()

    def count(self) -> int:
        """Return the number of cached entries."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM http_cache;")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def close(self) -> None:
        """Close SQLite database connection."""
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.ProgrammingError:
                pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

"""Async and cached GraphQL query file loader.

Loads and caches .graphql query files from the dedicated queries directory.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


class GraphQLQueryLoader:
    """Loads and caches GraphQL queries from disk."""

    def __init__(self, queries_dir: Path | str | None = None) -> None:
        if queries_dir is None:
            self.queries_dir = Path(__file__).parent / "queries"
        else:
            self.queries_dir = Path(queries_dir)
        self._cache: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def get_query_path(self, query_name: str) -> Path:
        """Resolve query file path, appending .graphql extension if missing."""
        filename = query_name if query_name.endswith(".graphql") else f"{query_name}.graphql"
        return self.queries_dir / filename

    def load_query(self, query_name: str) -> str:
        """Load query from disk synchronously, caching the result in memory."""
        if query_name in self._cache:
            return self._cache[query_name]

        path = self.get_query_path(query_name)
        if not path.is_file():
            raise FileNotFoundError(f"GraphQL query file not found: {path}")

        content = path.read_text(encoding="utf-8").strip()
        self._cache[query_name] = content
        return content

    async def load_query_async(self, query_name: str) -> str:
        """Load query asynchronously with thread pool and in-memory cache."""
        if query_name in self._cache:
            return self._cache[query_name]

        async with self._lock:
            if query_name in self._cache:
                return self._cache[query_name]

            path = self.get_query_path(query_name)
            if not path.is_file():
                raise FileNotFoundError(f"GraphQL query file not found: {path}")

            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                None, lambda: path.read_text(encoding="utf-8").strip()
            )
            self._cache[query_name] = content
            return content


_default_loader = GraphQLQueryLoader()


def load_query(query_name: str) -> str:
    """Convenience helper to load a query using the default loader."""
    return _default_loader.load_query(query_name)


async def load_query_async(query_name: str) -> str:
    """Convenience helper to load a query asynchronously using the default loader."""
    return await _default_loader.load_query_async(query_name)

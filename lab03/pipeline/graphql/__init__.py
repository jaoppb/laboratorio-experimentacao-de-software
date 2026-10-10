"""GraphQL module for Lab03 GitHub API v4 integration."""

from pipeline.graphql.loader import (
    GraphQLQueryLoader,
    load_query,
    load_query_async,
)

__all__ = [
    "GraphQLQueryLoader",
    "load_query",
    "load_query_async",
]

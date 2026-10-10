"""Tests for GraphQL query loader and query structures (pipeline.graphql)."""

from pathlib import Path
import pytest

from pipeline.graphql.loader import (
    GraphQLQueryLoader,
    load_query,
    load_query_async,
)


def test_graphql_loader_reads_file():
    """Verify that GraphQLQueryLoader correctly reads a .graphql file."""
    content = load_query("repo_details")
    assert "query GetRepoDetails" in content
    assert "releases(" in content
    assert "stargazerCount" in content


async def test_graphql_loader_async():
    """Verify asynchronous query loading and memory caching."""
    content1 = await load_query_async("repo_details.graphql")
    content2 = await load_query_async("repo_details")
    assert content1 == content2
    assert "GetRepoDetails" in content1


def test_graphql_loader_missing_file_raises(tmp_path):
    """Verify FileNotFoundError is raised when query file does not exist."""
    loader = GraphQLQueryLoader(queries_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load_query("non_existent_query")


async def test_graphql_loader_async_missing_file_raises(tmp_path):
    """Verify FileNotFoundError is raised asynchronously when query file does not exist."""
    loader = GraphQLQueryLoader(queries_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        await loader.load_query_async("non_existent_query")

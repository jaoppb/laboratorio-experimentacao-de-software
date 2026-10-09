"""Tests for commit collection between releases (pipeline.commits)."""

import httpx
import pytest
from metricas.lead_time import calculate_lead_time
from metricas.schemas import Release
from pipeline.commits import (
    ComparisonStatus,
    collect_release_commits,
    count_by_status,
    fetch_compare_commits,
)
from pipeline.http_client import GitHubClient
from pipeline.releases import WindowReleases


def _commit(sha, date, message="chore"):
    return {"sha": sha, "commit": {"author": {"date": date}, "message": message}}


def _client(handler):
    return GitHubClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_fetch_compare_paginates_beyond_250_commits():
    """A compare with 320 commits needs 4 pages of 100."""
    total = 320
    all_commits = [_commit(f"s{i}", "2024-03-01T00:00:00Z") for i in range(total)]
    pages_requested = []

    def handler(request):
        assert request.url.path == "/repos/o/r/compare/v1.0...v1.1"
        page = int(request.url.params["page"])
        per_page = int(request.url.params["per_page"])
        pages_requested.append(page)
        chunk = all_commits[(page - 1) * per_page : page * per_page]
        return httpx.Response(200, json={"total_commits": total, "commits": chunk})

    async with _client(handler) as client:
        commits = await fetch_compare_commits(client, "o", "r", "v1.0", "v1.1")

    assert len(commits) == total
    assert pages_requested == [1, 2, 3, 4]
    assert commits[0].sha == "s0"
    assert commits[-1].sha == "s319"


async def test_fetch_compare_keeps_message_and_author_date():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "total_commits": 1,
                "commits": [
                    _commit(
                        "abc", "2024-03-02T10:00:00Z", "fix: crash ao abrir arquivo"
                    )
                ],
            },
        )

    async with _client(handler) as client:
        [commit] = await fetch_compare_commits(client, "o", "r", "a", "b")
    assert commit.sha == "abc"
    assert commit.message == "fix: crash ao abrir arquivo"
    assert commit.committed_at.isoformat() == "2024-03-02T10:00:00+00:00"


async def test_fetch_compare_encodes_special_characters_in_tags():
    paths = []

    def handler(request):
        paths.append(request.url.raw_path.decode())
        return httpx.Response(200, json={"total_commits": 0, "commits": []})

    async with _client(handler) as client:
        assert await fetch_compare_commits(client, "o", "r", "pkg/v1.0+b1", "pkg/v1.1") == []
    assert paths[0].startswith("/repos/o/r/compare/pkg/v1.0%2Bb1...pkg/v1.1")


async def test_fetch_compare_stops_when_total_is_short_page():
    """Stops on a short page even if `total_commits` is missing."""
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"commits": [_commit("a", "2024-01-01T00:00:00Z")]}
        )

    async with _client(handler) as client:
        assert len(await fetch_compare_commits(client, "o", "r", "a", "b")) == 1
    assert len(calls) == 1


@pytest.fixture
def window():
    return WindowReleases(
        anchor=Release(tag_name="v1.0", published_at="2023-12-01T00:00:00Z"),
        in_window=[
            Release(tag_name="v1.1", published_at="2024-03-15T00:00:00Z"),
            Release(tag_name="v1.2", published_at="2024-04-01T00:00:00Z"),
            Release(tag_name="v1.3", published_at="2024-05-01T00:00:00Z"),
        ],
    )


def _compare_handler(request):
    base_head = request.url.path.rsplit("/", 1)[-1]
    if base_head == "v1.0...v1.1":
        commits = [
            _commit("c1", "2024-03-02T00:00:00Z"),
            _commit("c2", "2024-03-10T00:00:00Z"),
            _commit("c3", "2024-03-14T00:00:00Z"),
        ]
        return httpx.Response(200, json={"total_commits": 3, "commits": commits})
    if base_head == "v1.1...v1.2":
        return httpx.Response(404, json={"message": "Not Found"})
    if base_head == "v1.2...v1.3":
        return httpx.Response(200, json={"total_commits": 0, "commits": []})
    raise AssertionError(f"unexpected compare {base_head}")


async def test_collect_release_commits_uses_anchor_and_handles_404(window):
    async with _client(_compare_handler) as client:
        results = await collect_release_commits(client, "o", "r", window)

    assert [r.release.tag_name for r in results] == ["v1.1", "v1.2", "v1.3"]
    assert [r.previous.tag_name for r in results] == ["v1.0", "v1.1", "v1.2"]
    assert [r.status for r in results] == [
        ComparisonStatus.OK,
        ComparisonStatus.NOT_FOUND,
        ComparisonStatus.OK,
    ]
    assert [c.sha for c in results[0].commits] == ["c1", "c2", "c3"]
    assert results[1].commits_or_none is None
    assert results[2].commits_or_none == []

    counts = count_by_status(results)
    assert counts[ComparisonStatus.NOT_FOUND] == 1
    assert counts[ComparisonStatus.FIRST_RELEASE] == 0

    # Integration with lead time: v1.1 = 13 days; v1.2 skipped; v1.3 has no commits
    lead = calculate_lead_time([(r.release, r.commits_or_none) for r in results])
    assert lead.median_a_hours == pytest.approx(13 * 24)
    assert lead.skipped_releases == 1
    assert lead.releases_without_commits == 1


async def test_first_release_in_history_is_skipped_without_request():
    window = WindowReleases(
        in_window=[
            Release(tag_name="v1.0", published_at="2024-02-01T00:00:00Z"),
            Release(tag_name="v1.1", published_at="2024-03-15T00:00:00Z"),
        ]
    )
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "total_commits": 1,
                "commits": [_commit("x", "2024-03-01T00:00:00Z")],
            },
        )

    async with _client(handler) as client:
        results = await collect_release_commits(client, "o", "r", window)

    assert results[0].status == ComparisonStatus.FIRST_RELEASE
    assert results[0].previous is None
    assert results[0].commits_or_none is None
    assert results[1].status == ComparisonStatus.OK
    assert requests == ["/repos/o/r/compare/v1.0...v1.1"]


async def test_non_404_errors_are_raised(window):
    def handler(request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    async with _client(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await collect_release_commits(client, "o", "r", window)

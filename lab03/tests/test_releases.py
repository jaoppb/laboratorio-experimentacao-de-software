"""Tests for release and tag collection (pipeline.releases)."""

import httpx
import pytest
from metricas.schemas import Release
from pipeline.http_client import GitHubClient
from pipeline.releases import (
    count_valid_releases,
    deploy_units,
    fetch_releases,
    fetch_tags,
    filter_window,
    parse_release,
)

WINDOW_START = "2024-01-01T00:00:00Z"
WINDOW_END = "2024-12-31T23:59:59Z"
API = "https://api.github.com"


def _release(tag, published_at, draft=False, prerelease=False):
    return {
        "tag_name": tag,
        "published_at": published_at,
        "draft": draft,
        "prerelease": prerelease,
    }


@pytest.fixture
def releases():
    """Mixed history: stable releases, a pre-release, all oldest first."""
    return [
        Release(tag_name="v0.9", published_at="2023-11-01T00:00:00Z"),
        Release(
            tag_name="v1.0-rc1", published_at="2023-12-20T00:00:00Z", prerelease=True
        ),
        Release(tag_name="v1.0", published_at="2024-01-10T00:00:00Z"),
        Release(
            tag_name="v1.1-beta", published_at="2024-02-01T00:00:00Z", prerelease=True
        ),
        Release(tag_name="v1.1", published_at="2024-03-01T00:00:00Z"),
        Release(tag_name="v2.0", published_at="2025-01-15T00:00:00Z"),
    ]


def _client(handler):
    return GitHubClient(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_parse_release_discards_drafts():
    assert parse_release(_release("v1", None, draft=True)) is None
    assert parse_release(_release("v1", "2024-01-01T00:00:00Z", draft=True)) is None
    rel = parse_release(_release("v1", "2024-01-01T00:00:00Z", prerelease=True))
    assert rel.tag_name == "v1"
    assert rel.prerelease is True
    assert rel.draft is False


def test_deploy_units_main_and_prerelease_variant(releases):
    assert [r.tag_name for r in deploy_units(releases)] == [
        "v0.9",
        "v1.0",
        "v1.1",
        "v2.0",
    ]
    assert len(deploy_units(releases, include_prerelease=True)) == 6


def test_filter_window_keeps_previous_release_as_anchor(releases):
    window = filter_window(releases, WINDOW_START, WINDOW_END)
    assert [r.tag_name for r in window.in_window] == ["v1.0", "v1.1"]
    assert window.anchor.tag_name == "v0.9"
    assert window.count == 2
    assert [r.tag_name for r in window.with_anchor()] == ["v0.9", "v1.0", "v1.1"]


def test_filter_window_prerelease_variant_anchor(releases):
    window = filter_window(releases, WINDOW_START, WINDOW_END, include_prerelease=True)
    assert [r.tag_name for r in window.in_window] == ["v1.0", "v1.1-beta", "v1.1"]
    assert window.anchor.tag_name == "v1.0-rc1"


def test_filter_window_without_previous_release(releases):
    window = filter_window(releases[2:], WINDOW_START, WINDOW_END)
    assert window.anchor is None
    assert window.with_anchor() == window.in_window


def test_filter_window_bounds_are_inclusive():
    rels = [
        Release(tag_name="start", published_at=WINDOW_START),
        Release(tag_name="end", published_at=WINDOW_END),
    ]
    assert filter_window(rels, WINDOW_START, WINDOW_END).count == 2


def test_count_valid_releases(releases):
    assert count_valid_releases(releases, WINDOW_START, WINDOW_END) == 2


def test_fetch_releases_paginates_and_stops_after_anchor():
    """Pagination stops after the page holding the first stable release before the window."""
    requested_pages = []
    pages = {
        "1": [
            _release("v1.2", "2024-06-01T00:00:00Z"),
            _release("v1.2-draft", None, draft=True),
            _release("v1.1", "2024-03-01T00:00:00Z"),
        ],
        "2": [
            _release("v1.0-rc1", "2023-12-20T00:00:00Z", prerelease=True),
            _release("v0.9", "2023-11-01T00:00:00Z"),
        ],
        "3": [_release("v0.1", "2020-01-01T00:00:00Z")],
    }

    def handler(request):
        page = request.url.params.get("page", "1")
        requested_pages.append(page)
        assert request.url.path == "/repos/o/r/releases"
        headers = {}
        if page != "3":
            headers["Link"] = (
                f'<{API}/repos/o/r/releases?per_page=100&page={int(page) + 1}>; rel="next"'
            )
        return httpx.Response(200, json=pages[page], headers=headers)

    with _client(handler) as client:
        result = fetch_releases(client, "o", "r", window_start=WINDOW_START)

    assert requested_pages == ["1", "2"]
    assert [r.tag_name for r in result] == ["v0.9", "v1.0-rc1", "v1.1", "v1.2"]


def test_fetch_releases_full_history_without_window():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                _release("v2", "2024-02-01T00:00:00Z"),
                _release("v1", "2020-01-01T00:00:00Z"),
            ],
        )

    with _client(handler) as client:
        result = fetch_releases(client, "o", "r")
    assert [r.tag_name for r in result] == ["v1", "v2"]


def test_fetch_tags_dates_by_commit_author_date():
    """Tags are dated by the commit they point to; shared commits are fetched once."""
    commit_requests = []

    def handler(request):
        path = request.url.path
        if path == "/repos/o/r/tags":
            return httpx.Response(
                200,
                json=[
                    {"name": "v2", "commit": {"sha": "bbb"}},
                    {"name": "v2-alias", "commit": {"sha": "bbb"}},
                    {"name": "v1", "commit": {"sha": "aaa"}},
                ],
            )
        sha = path.rsplit("/", 1)[-1]
        commit_requests.append(sha)
        dates = {"aaa": "2024-01-05T00:00:00Z", "bbb": "2024-02-05T00:00:00Z"}
        return httpx.Response(
            200, json={"sha": sha, "commit": {"author": {"date": dates[sha]}}}
        )

    with _client(handler) as client:
        tags = fetch_tags(client, "o", "r")

    assert [t.tag_name for t in tags] == ["v1", "v2", "v2-alias"]
    assert tags[0].published_at.isoformat() == "2024-01-05T00:00:00+00:00"
    assert sorted(commit_requests) == ["aaa", "bbb"]


def test_fetch_tags_respects_max_tags():
    def handler(request):
        if request.url.path == "/repos/o/r/tags":
            return httpx.Response(
                200,
                json=[{"name": f"v{i}", "commit": {"sha": f"s{i}"}} for i in range(5)],
                headers={"Link": f'<{API}/repos/o/r/tags?page=2>; rel="next"'},
            )
        return httpx.Response(
            200, json={"commit": {"author": {"date": "2024-01-01T00:00:00Z"}}}
        )

    with _client(handler) as client:
        tags = fetch_tags(client, "o", "r", max_tags=3)
    assert len(tags) == 3

"""Tests for CFR (b) and the corrective-release heuristic (metricas.cfr_b)."""

import pytest

from metricas.cfr_b import (
    DEFAULT_HEURISTIC,
    HEURISTICS,
    CfrBResult,
    ReleaseOutcome,
    calculate_cfr_b,
    fix_commit_ratio,
    has_fix_commit,
    heuristic_v1,
    heuristic_v1_full_message,
    is_corrective_release,
    is_fix_message,
    is_patch_bump,
    parse_semver,
)
from metricas.dora import DORATier
from metricas.schemas import Commit, Release

WINDOW_END = "2024-09-30T23:59:59Z"


def _commit(sha: str, message: str, date: str = "2024-05-01T00:00:00Z") -> Commit:
    return Commit(sha=sha, committed_at=date, message=message)


@pytest.fixture
def guide_example():
    """Guide example: v2.3.0→v2.3.1 failed; v2.4.0→v2.5.0 did not fail."""
    return [
        (
            Release(tag_name="v2.3.0", published_at="2024-05-10T00:00:00Z"),
            [_commit("a1", "feat: open recent files")],
        ),
        (
            Release(tag_name="v2.3.1", published_at="2024-05-12T00:00:00Z"),
            [_commit("b1", "fix: crash ao abrir arquivo")],
        ),
        (
            Release(tag_name="v2.4.0", published_at="2024-06-01T00:00:00Z"),
            [_commit("c1", "feat: dark mode")],
        ),
        (
            Release(tag_name="v2.5.0", published_at="2024-06-20T00:00:00Z"),
            [_commit("d1", "feat: plugins"), _commit("d2", "fix: typo in docs")],
        ),
    ]


# --- SemVer parsing ---------------------------------------------------------


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("v2.3.1", (2, 3, 1)),
        ("2.3.1", (2, 3, 1)),
        ("v1.2", (1, 2, 0)),
        ("release-4.0.10", (4, 0, 10)),
        ("@scope/pkg@1.2.3", (1, 2, 3)),
        ("v3.0.0-rc.1", (3, 0, 0)),
        ("v1.0.0+build.5", (1, 0, 0)),
    ],
)
def test_parse_semver(tag, expected):
    assert parse_semver(tag) == expected


@pytest.mark.parametrize("tag", ["nightly", "latest", "build-42", "1.2.3.4", ""])
def test_parse_semver_rejects_non_semver(tag):
    assert parse_semver(tag) is None


def test_is_patch_bump():
    assert is_patch_bump("v2.3.0", "v2.3.1") is True
    assert is_patch_bump("v2.4.0", "v2.5.0") is False
    assert is_patch_bump("v2.9.3", "v3.0.0") is False
    assert is_patch_bump("v2.3.1", "v2.3.1") is False


def test_is_patch_bump_unknown_outside_semver():
    assert is_patch_bump("nightly-1", "v2.3.1") is None
    assert is_patch_bump("v2.3.0", "nightly-2") is None


# --- Commit messages --------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "fix: crash ao abrir arquivo",
        "fix(parser): handle empty input",
        "Revert \"feat: new cache\"",
        "hotfix for login",
        "Fixes #123",
        "bugfix: wrong offset",
    ],
)
def test_fix_messages(message):
    assert is_fix_message(message)


@pytest.mark.parametrize(
    "message", ["feat: add prefix option", "chore: bump deps", "docs: suffix", ""]
)
def test_non_fix_messages(message):
    assert not is_fix_message(message)


def test_fix_commit_helpers():
    commits = [_commit("1", "fix: a"), _commit("2", "feat: b")]
    assert has_fix_commit(commits)
    assert fix_commit_ratio(commits) == pytest.approx(0.5)
    assert fix_commit_ratio([]) == 0.0
    assert not has_fix_commit([])


# --- Heuristic v1 -----------------------------------------------------------


def test_heuristic_v1_requires_patch_bump_and_fix_commit():
    fix = [_commit("1", "fix: crash")]
    feat = [_commit("2", "feat: x")]
    assert heuristic_v1("v2.3.0", "v2.3.1", fix) is True
    assert heuristic_v1("v2.3.0", "v2.3.1", feat) is False
    assert heuristic_v1("v2.4.0", "v2.5.0", fix) is False


def test_heuristic_v1_falls_back_to_messages_outside_semver():
    assert heuristic_v1("nightly-1", "nightly-2", [_commit("1", "hotfix")]) is True
    assert heuristic_v1("nightly-1", "nightly-2", [_commit("1", "feat")]) is False


def test_is_corrective_release_dispatches_version():
    commits = [_commit("1", "fix: crash")]
    assert is_corrective_release("v1.0.0", "v1.0.1", commits, version="v1")
    with pytest.raises(KeyError):
        is_corrective_release("v1.0.0", "v1.0.1", commits, version="v999")


# --- CFR (b) ----------------------------------------------------------------


def test_guide_example(guide_example):
    result = calculate_cfr_b(guide_example, window_end=WINDOW_END)
    outcomes = dict(result.outcomes)

    assert outcomes["v2.3.0"] == ReleaseOutcome.FAILED
    assert outcomes["v2.4.0"] == ReleaseOutcome.OK
    # v2.3.1 is followed by v2.4.0 after 20 days; v2.5.0 has no successor.
    assert outcomes["v2.3.1"] == ReleaseOutcome.OK
    assert outcomes["v2.5.0"] == ReleaseOutcome.OK
    assert result.failed_releases == 1
    assert result.evaluated_releases == 4
    assert result.cfr_b == pytest.approx(0.25)
    assert result.tier == DORATier.HIGH


def test_input_order_does_not_matter(guide_example):
    shuffled = list(reversed(guide_example))
    assert calculate_cfr_b(shuffled, WINDOW_END).cfr_b == pytest.approx(0.25)


def test_corrective_release_after_seven_days_does_not_count():
    releases = [
        (Release(tag_name="v1.0.0", published_at="2024-05-01T00:00:00Z"), []),
        (
            Release(tag_name="v1.0.1", published_at="2024-05-08T00:00:01Z"),
            [_commit("1", "fix: late")],
        ),
    ]
    result = calculate_cfr_b(releases, WINDOW_END)
    assert dict(result.outcomes)["v1.0.0"] == ReleaseOutcome.OK
    assert result.cfr_b == 0.0


def test_corrective_release_exactly_seven_days_later_counts():
    releases = [
        (Release(tag_name="v1.0.0", published_at="2024-05-01T00:00:00Z"), []),
        (
            Release(tag_name="v1.0.1", published_at="2024-05-08T00:00:00Z"),
            [_commit("1", "fix: on the edge")],
        ),
    ]
    result = calculate_cfr_b(releases, WINDOW_END)
    assert dict(result.outcomes)["v1.0.0"] == ReleaseOutcome.FAILED


def test_releases_in_last_seven_days_are_censored():
    releases = [
        (Release(tag_name="v1.0.0", published_at="2024-09-20T00:00:00Z"), []),
        (
            Release(tag_name="v1.0.1", published_at="2024-09-25T00:00:00Z"),
            [_commit("1", "fix: crash")],
        ),
    ]
    result = calculate_cfr_b(releases, WINDOW_END)
    outcomes = dict(result.outcomes)
    assert outcomes["v1.0.0"] == ReleaseOutcome.FAILED
    assert outcomes["v1.0.1"] == ReleaseOutcome.CENSORED
    assert result.censored_releases == 1
    assert result.evaluated_releases == 1
    assert result.cfr_b == 1.0


def test_single_release_repository():
    releases = [(Release(tag_name="v1.0.0", published_at="2024-05-01T00:00:00Z"), None)]
    result = calculate_cfr_b(releases, WINDOW_END)
    assert result.evaluated_releases == 1
    assert result.failed_releases == 0
    assert result.cfr_b == 0.0


def test_only_censored_releases_give_none():
    releases = [(Release(tag_name="v1.0.0", published_at="2024-09-29T00:00:00Z"), [])]
    result = calculate_cfr_b(releases, WINDOW_END)
    assert result.cfr_b is None
    assert result.tier is None
    assert result.censored_releases == 1


def test_empty_input():
    assert calculate_cfr_b([], WINDOW_END) == CfrBResult(cfr_b=None)


def test_unknown_commits_of_next_release_skip_the_release():
    """Next release within 7 days but compare returned 404: cannot be judged."""
    releases = [
        (Release(tag_name="v1.0.0", published_at="2024-05-01T00:00:00Z"), []),
        (Release(tag_name="v1.0.1", published_at="2024-05-03T00:00:00Z"), None),
    ]
    result = calculate_cfr_b(releases, WINDOW_END)
    assert dict(result.outcomes)["v1.0.0"] == ReleaseOutcome.SKIPPED
    assert result.skipped_releases == 1
    assert result.evaluated_releases == 1  # v1.0.1 itself has no successor
    assert result.cfr_b == 0.0


def test_non_semver_tags_use_commit_messages():
    releases = [
        (Release(tag_name="nightly-100", published_at="2024-05-01T00:00:00Z"), []),
        (
            Release(tag_name="nightly-101", published_at="2024-05-02T00:00:00Z"),
            [_commit("1", "Revert \"feat: x\"")],
        ),
        (
            Release(tag_name="nightly-102", published_at="2024-05-03T00:00:00Z"),
            [_commit("2", "feat: y")],
        ),
    ]
    result = calculate_cfr_b(releases, WINDOW_END)
    outcomes = dict(result.outcomes)
    assert outcomes["nightly-100"] == ReleaseOutcome.FAILED
    assert outcomes["nightly-101"] == ReleaseOutcome.OK
    assert result.cfr_b == pytest.approx(1 / 3)


def test_unparseable_window_end():
    with pytest.raises(ValueError):
        calculate_cfr_b([], window_end=None)  # type: ignore[arg-type]


# --- Heuristic v1_full_message ---------------------------------------------


def _full(sha: str, subject: str, full: str | None) -> Commit:
    return Commit(sha=sha, committed_at="2024-05-01T00:00:00Z", message=subject, full_message=full)


def test_default_heuristic_is_still_v1_and_both_are_registered():
    assert DEFAULT_HEURISTIC == "v1"
    assert list(HEURISTICS) == ["v1", "v1_full_message"]


def test_v1_ignores_the_body_but_v1_full_message_reads_it():
    commits = [_full("1", "chore: tidy", "chore: tidy\n\nbody\nFixes #123")]
    assert is_corrective_release("v1.0.0", "v1.0.1", commits, version="v1") is False
    assert is_corrective_release("v1.0.0", "v1.0.1", commits, version="v1_full_message") is True
    # default stays v1
    assert is_corrective_release("v1.0.0", "v1.0.1", commits) is False


def test_v1_full_message_keeps_the_version_criterion():
    commits = [_full("1", "chore", "chore\n\nFixes #1")]
    assert heuristic_v1_full_message("v1.0.0", "v1.1.0", commits) is False
    assert heuristic_v1_full_message("nightly-1", "nightly-2", commits) is True


def test_v1_full_message_falls_back_to_subject_for_old_data():
    old = [_commit("1", "fix: crash")]  # full_message=None (collected before the field)
    other = [_commit("2", "feat: x")]
    assert old[0].full_message is None and old[0].text == "fix: crash"
    for tags in (("v1.0.0", "v1.0.1"), ("nightly-1", "nightly-2")):
        assert heuristic_v1_full_message(*tags, old) == heuristic_v1(*tags, old)
        assert heuristic_v1_full_message(*tags, other) == heuristic_v1(*tags, other)


@pytest.mark.parametrize(
    "subject, body, expected",
    [
        ("Merge branch 'x'", "Merge branch 'x'\n\nhotfix: login", True),
        ('Revert "feat: a"', 'Revert "feat: a"\n\nThis reverts commit abc.', True),
        ("docs: café ✓", "docs: café ✓\n\nsem correção aqui", False),
        ("feat: crlf", "feat: crlf\n\nhotfix inside body", True),
        ("feat: prefix", "feat: prefix\n\nsuffix, prefixed, unfixed", False),
    ],
)
def test_v1_full_message_on_synthetic_messages(subject, body, expected):
    commits = [_full("1", subject, body)]
    assert has_fix_commit(commits, full_message=True) is expected
    # v1 only ever sees the subject
    assert has_fix_commit(commits) is is_fix_message(subject)

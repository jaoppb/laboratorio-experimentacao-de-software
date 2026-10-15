"""Change Failure Rate variant (b): delivery proxy based on corrective releases.

A release R fails when it is followed, within 7 days, by a corrective release.
CFR (b) = failed releases / evaluated releases. Releases published in the last
7 days of the window cannot be evaluated yet and are censored (left out of the
denominator).

The corrective-release heuristic is versioned (`HEURISTICS`) so that each
version can be evaluated against the manually labeled gold sample (Issue #62).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from metricas.dora import DORATier, classify_change_failure_rate
from metricas.schemas import _parse_datetime

if TYPE_CHECKING:
    from metricas.schemas import Commit, Release

FAILURE_HORIZON = timedelta(days=7)

# MAJOR.MINOR[.PATCH], optionally preceded by any prefix ("v", "release-",
# "pkg@") and followed by a pre-release/build suffix ("-rc.1", "+build").
_SEMVER_RE = re.compile(
    r"(?:^|[^0-9.])v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-+][0-9A-Za-z.-]*)?$"
)

# Whole-word keywords; "fix" also matches Conventional Commits "fix(scope):".
_FIX_KEYWORDS_RE = re.compile(
    r"\b(revert|reverts|reverted|hotfix|hot-fix|fix|fixes|fixed|bugfix)\b",
    re.IGNORECASE,
)


def parse_semver(tag_name: str) -> tuple[int, int, int] | None:
    """Extract (major, minor, patch) from a tag name, or None if it is not SemVer.

    A missing patch number is read as 0 (`v1.2` → (1, 2, 0)).
    """
    match = _SEMVER_RE.search(tag_name.strip())
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def is_patch_bump(previous_tag: str, tag: str) -> bool | None:
    """True if only the patch number increases (`2.3.0 → 2.3.1`).

    Returns None when either tag is outside SemVer, so the version criterion
    cannot be applied.
    """
    prev = parse_semver(previous_tag)
    cur = parse_semver(tag)
    if prev is None or cur is None:
        return None
    return cur[0] == prev[0] and cur[1] == prev[1] and cur[2] > prev[2]


def is_fix_message(message: str) -> bool:
    """True if the commit message mentions revert, hotfix or fix."""
    return bool(_FIX_KEYWORDS_RE.search(message or ""))


def has_fix_commit(commits: Sequence[Commit]) -> bool:
    """True if at least one commit message mentions revert, hotfix or fix."""
    return any(is_fix_message(c.message) for c in commits)


def fix_commit_ratio(commits: Sequence[Commit]) -> float:
    """Share of commits whose message mentions revert, hotfix or fix."""
    if not commits:
        return 0.0
    return sum(is_fix_message(c.message) for c in commits) / len(commits)


Heuristic = Callable[[str, str, Sequence["Commit"]], bool]


def heuristic_v1(previous_tag: str, tag: str, commits: Sequence[Commit]) -> bool:
    """v1: only the patch changes AND some commit mentions revert/hotfix/fix.

    For tags outside SemVer the version criterion is unknown, so the decision
    falls back to the commit messages alone.
    """
    patch = is_patch_bump(previous_tag, tag)
    fix = has_fix_commit(commits)
    if patch is None:
        return fix
    return patch and fix


HEURISTICS: dict[str, Heuristic] = {
    "v1": heuristic_v1,
}

DEFAULT_HEURISTIC = "v1"


def is_corrective_release(
    previous_tag: str,
    tag: str,
    commits: Sequence[Commit],
    version: str = DEFAULT_HEURISTIC,
) -> bool:
    """Apply the corrective-release heuristic `version` to the release `tag`.

    `commits` are the commits included in `tag` (compare against `previous_tag`).
    """
    return HEURISTICS[version](previous_tag, tag, commits)


class ReleaseOutcome(str, Enum):
    """Classification of one release for CFR (b)."""

    FAILED = "failed"
    OK = "ok"
    CENSORED = "censored"
    SKIPPED = "skipped"


@dataclass
class CfrBResult:
    """CFR (b) of a repository and the counts behind it."""

    cfr_b: float | None
    failed_releases: int = 0
    evaluated_releases: int = 0
    censored_releases: int = 0
    skipped_releases: int = 0
    outcomes: list[tuple[str, ReleaseOutcome]] = field(default_factory=list)

    @property
    def tier(self) -> DORATier | None:
        """DORA tier of CFR (b); None when no release could be evaluated."""
        if self.cfr_b is None:
            return None
        return classify_change_failure_rate(self.cfr_b)


def calculate_cfr_b(
    releases: Sequence[tuple[Release, Sequence[Commit] | None]],
    window_end: datetime | str,
    version: str = DEFAULT_HEURISTIC,
    horizon: timedelta = FAILURE_HORIZON,
) -> CfrBResult:
    """Calculate CFR (b) for the in-window releases of a repository.

    Each item pairs a release with the commits included in it (compare against
    the previous release); `None` means the commits are unknown (first release
    in history or compare/tag not found). Releases must be the deploy units of
    the window, in any order.

    Rules:
    - a release published after `window_end − horizon` is censored;
    - a release is failed when the next release comes within `horizon` and the
      heuristic marks it as corrective;
    - if the next release comes within `horizon` but its commits are unknown,
      the release cannot be judged and is skipped;
    - otherwise (no next release, or next one later than `horizon`) it is ok.

    Censored and skipped releases are left out of the denominator.
    """
    end = _parse_datetime(window_end)
    if end is None:
        raise ValueError("window_end must not be None")
    cutoff = end - horizon

    ordered = sorted(releases, key=lambda item: item[0].published_at)
    outcomes: list[tuple[str, ReleaseOutcome]] = []

    for i, (release, _) in enumerate(ordered):
        if release.published_at > cutoff:
            outcomes.append((release.tag_name, ReleaseOutcome.CENSORED))
            continue

        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        if nxt is None or nxt[0].published_at - release.published_at > horizon:
            outcomes.append((release.tag_name, ReleaseOutcome.OK))
            continue

        next_release, next_commits = nxt
        if next_commits is None:
            outcomes.append((release.tag_name, ReleaseOutcome.SKIPPED))
            continue

        corrective = is_corrective_release(
            release.tag_name, next_release.tag_name, next_commits, version=version
        )
        outcomes.append(
            (release.tag_name, ReleaseOutcome.FAILED if corrective else ReleaseOutcome.OK)
        )

    failed = sum(1 for _, o in outcomes if o == ReleaseOutcome.FAILED)
    ok = sum(1 for _, o in outcomes if o == ReleaseOutcome.OK)
    evaluated = failed + ok

    return CfrBResult(
        cfr_b=failed / evaluated if evaluated else None,
        failed_releases=failed,
        evaluated_releases=evaluated,
        censored_releases=sum(1 for _, o in outcomes if o == ReleaseOutcome.CENSORED),
        skipped_releases=sum(1 for _, o in outcomes if o == ReleaseOutcome.SKIPPED),
        outcomes=outcomes,
    )

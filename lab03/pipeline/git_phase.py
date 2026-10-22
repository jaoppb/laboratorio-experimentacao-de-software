"""Git/commit phase of one repository, in-process or in a short-lived child process.

The phase reads the local bare clone (no GitHub API call, no token): it collects
the commits of C1, C2 and C3 with one SHA table, computes every metric column
that only needs commits (`compute_commit_columns`) and writes `releases/`,
`releases_c2/`, `tags/` and `commits/`. Its result is a small JSON-serialisable
dictionary, so the parent can run it in a child: Python does not give freed
memory back to the OS, and a child returns all of it on exit (Issue #56).

All GitHub API calls (releases, workflow runs) stay in the parent, which owns
the token pool. The parent also does the clone (its 403/429 fallback needs the
pool) and passes the path of the clone.

Child entry point (spec as JSON on stdin, result as one JSON line on stdout):
    python -m pipeline.git_phase
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from metricas.schemas import Commit, Release, _parse_datetime
from pipeline.commits import collect_release_commits
from pipeline.orchestrator import collect_c2_c3_units, compute_commit_columns
from pipeline.releases import filter_window, save_repository_units

logger = logging.getLogger(__name__)

# Whole child: a repository with a huge history still has to finish well inside this
CHILD_TIMEOUT_SECONDS = 3600.0
_SECRET_ENV = ("GITHUB_TOKEN", "GITHUB_TOKENS", "GH_TOKEN", "GITHUB_PAT")


class GitPhaseError(RuntimeError):
    """The git phase failed (an exception in the child, a crash or a timeout)."""


@dataclass
class GitPhaseSpec:
    """Everything the git phase needs (plain data, JSON round-trips exactly)."""

    owner: str
    repo: str
    git_dir: str
    dados_dir: str
    releases: list[dict[str, Any]]
    window_start: str
    window_end: str
    window_weeks: float
    heuristic: str

    @classmethod
    def build(
        cls,
        owner: str,
        repo: str,
        git_dir: Path | str,
        dados_dir: Path | str,
        releases: list[Release],
        window_start: datetime,
        window_end: datetime,
        window_weeks: float,
        heuristic: str,
    ) -> GitPhaseSpec:
        return cls(
            owner=owner,
            repo=repo,
            git_dir=str(git_dir),
            dados_dir=str(dados_dir),
            releases=[
                {
                    "tag_name": r.tag_name,
                    "published_at": r.published_at.isoformat(),  # type: ignore[union-attr]
                    "draft": r.draft,
                    "prerelease": r.prerelease,
                    "commit_sha": r.commit_sha,
                }
                for r in releases
            ],
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
            window_weeks=window_weeks,
            heuristic=heuristic,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, text: str) -> GitPhaseSpec:
        return cls(**json.loads(text))


def peak_rss_mb() -> int | None:
    """Peak resident set of this process in MiB (None when the platform cannot tell)."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):
        return None
    # bytes on macOS, KiB elsewhere
    return int(peak // (1024 * 1024)) if sys.platform == "darwin" else int(peak // 1024)


async def run_git_phase(spec: GitPhaseSpec) -> dict[str, Any]:
    """Collect the commits of one repository, compute their metric columns and persist them.

    Returns `{"columns": ..., "distinct_commits": n, "peak_rss_mb": ...}`.
    `columns` is `compute_commit_columns` (lead time of C1, C2/C3 and CFR (b)
    columns); the persisted files follow `pipeline.commit_store`.
    """
    releases = [
        Release(
            tag_name=r["tag_name"],
            published_at=r["published_at"],
            draft=r["draft"],
            prerelease=r["prerelease"],
            commit_sha=r.get("commit_sha"),
        )
        for r in spec.releases
    ]
    window_start = _parse_datetime(spec.window_start)
    window_end = _parse_datetime(spec.window_end)
    assert window_start is not None and window_end is not None
    window_releases = filter_window(releases, window_start, window_end)

    commit_cache: dict[str, Commit] = {}
    release_commits_c1 = await collect_release_commits(
        client=None,
        owner=spec.owner,
        repo=spec.repo,
        window=window_releases,
        git_dir=spec.git_dir,
        commit_cache=commit_cache,
    )
    units = await collect_c2_c3_units(
        git_dir=spec.git_dir,
        releases=releases,
        window_start=window_start,
        window_end=window_end,
        commit_cache=commit_cache,
    )
    columns = compute_commit_columns(
        releases=releases,
        release_commits_c1=release_commits_c1,
        units=units,
        window_end=window_end,
        window_weeks=spec.window_weeks,
        cfr_b_heuristic=spec.heuristic,
    )
    save_repository_units(
        spec.dados_dir,
        spec.owner,
        spec.repo,
        release_commits_c1,
        units.release_commits_c2,
        units.tag_commits_c3,
        commit_cache,
    )
    return {
        "columns": columns,
        "distinct_commits": len(commit_cache),
        "peak_rss_mb": peak_rss_mb(),
    }


def _child_env() -> dict[str, str]:
    """Environment of the child: the parent's, without tokens, with `pipeline` importable."""
    env = {k: v for k, v in os.environ.items() if k not in _SECRET_ENV}
    root = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = os.pathsep.join([root, *filter(None, [env.get("PYTHONPATH")])])
    return env


async def run_git_phase_in_child(
    spec: GitPhaseSpec, timeout: float = CHILD_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """Run `run_git_phase` in a fresh interpreter and return its result.

    The child gets no GitHub token. A non-zero exit, an unreadable answer or the
    timeout (the child is killed) raise `GitPhaseError`; files are written
    atomically, so a killed child leaves no partial file (at most `*.tmp`,
    removed here).
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pipeline.git_phase",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_child_env(),
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(spec.to_json().encode("utf-8")), timeout=timeout
        )
    except BaseException as exc:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        _remove_temporary_files(spec)
        if isinstance(exc, asyncio.TimeoutError):
            raise GitPhaseError(
                f"git phase of {spec.owner}/{spec.repo} timed out after {timeout:.0f}s"
            ) from None
        raise

    lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
    answer: dict[str, Any] | None = None
    if lines:
        try:
            answer = json.loads(lines[-1])
        except json.JSONDecodeError:
            answer = None
    if proc.returncode != 0 or not isinstance(answer, dict) or not answer.get("ok"):
        _remove_temporary_files(spec)
        detail = (
            answer.get("error")
            if isinstance(answer, dict) and answer.get("error")
            else stderr.decode("utf-8", errors="replace").strip()[-500:]
        )
        raise GitPhaseError(
            f"git phase of {spec.owner}/{spec.repo} failed (exit {proc.returncode}): {detail}"
        )
    return answer["result"]


def _remove_temporary_files(spec: GitPhaseSpec) -> None:
    """Drop the `.tmp` leftovers of a child that died while writing."""
    name = f"{spec.owner}__{spec.repo}.parquet.tmp"
    for sub in ("releases", "releases_c2", "tags", "commits"):
        (Path(spec.dados_dir) / sub / name).unlink(missing_ok=True)


def main() -> int:
    """Child entry point: spec on stdin, `{"ok": ..., "result"|"error": ...}` on stdout."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    try:
        spec = GitPhaseSpec.from_json(sys.stdin.read())
        result = asyncio.run(run_git_phase(spec))
        answer: dict[str, Any] = {"ok": True, "result": result}
        code = 0
    except Exception as exc:
        answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}
        code = 1
    sys.stdout.write(json.dumps(answer) + "\n")
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())

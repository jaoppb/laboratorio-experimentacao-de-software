"""Repository candidate selection and Actions validation.

Fulfills requirements of Issue #29 and guialab03.md:
- Slices GitHub search by star ranges (since each search returns max 1000)
- Discards repositories with actions/workflows total_count == 0
- Collects well over 100 candidates to survive subsequent filters
- Feeds funnel statistics
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.funnel import FunnelTracker
    from pipeline.http_client import GitHubClient

logger = logging.getLogger(__name__)

DEFAULT_STAR_RANGES = [
    "1000..1500",
    "1501..2500",
    "2501..5000",
    "5001..10000",
    ">10000",
]


def search_candidates_by_stars(
    client: GitHubClient,
    star_ranges: list[str] | None = None,
    max_pages_per_range: int = 10,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    """Search repositories sliced by star ranges to exceed GitHub's 1000 items limit.

    Deduplicates repositories by full_name ('owner/repo').
    """
    ranges = star_ranges or DEFAULT_STAR_RANGES
    seen_names: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for star_range in ranges:
        query = f"stars:{star_range}"
        logger.info("Searching repositories with query: %s", query)
        page = 1

        while page <= max_pages_per_range:
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            }
            try:
                response = client.get("/search/repositories", params=params)
                data = response.json()
            except Exception as e:
                logger.error("Error searching page %d of query %s: %s", page, query, e)
                break

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                full_name = item.get("full_name")
                if full_name and full_name not in seen_names:
                    seen_names.add(full_name)
                    candidates.append(item)

            # GitHub search max results is 1000 (page 10 at 100/page)
            if len(items) < per_page or page >= 10:
                break
            page += 1

    return candidates


def filter_repositories_with_actions(
    client: GitHubClient,
    repositories: list[dict[str, Any]],
    funnel: FunnelTracker | None = None,
) -> list[dict[str, Any]]:
    """Filter repositories by checking if they have active GitHub Actions workflows.

    Discards repositories where GET /repos/{owner}/{repo}/actions/workflows has total_count == 0.
    """
    accepted: list[dict[str, Any]] = []
    discarded_no_actions = 0

    for repo in repositories:
        full_name = repo.get("full_name")
        if not full_name:
            continue

        endpoint = f"/repos/{full_name}/actions/workflows"
        try:
            resp = client.get(endpoint)
            wf_data = resp.json()
            total_count = wf_data.get("total_count", 0)

            if total_count > 0:
                accepted.append(repo)
            else:
                discarded_no_actions += 1
                logger.debug("Discarding %s: total_count of workflows is 0", full_name)
        except Exception as exc:
            logger.warning("Error fetching workflows for %s: %s", full_name, exc)
            discarded_no_actions += 1

    if funnel is not None:
        funnel.record_stage(
            etapa="Repositórios candidatos da busca por estrelas",
            quantidade_restante=len(repositories),
            descartados=0,
            motivo_descarte="-",
        )
        funnel.record_stage(
            etapa="Filtro de uso de CI/CD (GitHub Actions)",
            quantidade_restante=len(accepted),
            descartados=discarded_no_actions,
            motivo_descarte="total_count de workflows == 0 ou erro de acesso",
        )

    return accepted

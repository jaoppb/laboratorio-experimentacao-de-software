from typing import Dict, List

import structlog

from src.base_query_runner import BaseQueryRunner
from src.core.concurrency_controller import ConcurrencyController
from src.core.github_client import GitHubClient
from src.engine.extraction_context import ExtractionContext
from src.engine.hydrate_runner import HydrateRunner
from src.engine.star_range_resolver import StarRangeResolver
from src.engine.sweep_runner import SweepRunner
from src.graphql.graphql_util import GraphQLAstModifier
from src.graphql.query import Query

logger = structlog.get_logger(__name__)


class DistributedQueryRunner(BaseQueryRunner):
    def __init__(self, client: GitHubClient, max_concurrent: int = 20):
        self.client = client
        self.max_concurrent = max_concurrent

    async def run_query(
        self,
        query_obj: Query,
        sample_size: int,
        search_query: str = "stars:>1 sort:stars-desc",
    ) -> List[Dict]:
        # Pipeline Context
        context = ExtractionContext(
            sample_size=sample_size, search_query=search_query, query_obj=query_obj
        )
        context.sweep_graphql = GraphQLAstModifier.generate_sweep_query(
            query_obj.content
        )
        context.hydrate_graphql = GraphQLAstModifier.generate_hydrate_query(
            query_obj.content
        )

        # Bind context
        log = logger.bind(
            target_sample_size=sample_size, base_query=search_query
        )
        log.info("pipeline_started", phase="initialization")

        # Create the dynamic concurrency controller
        concurrency_controller = ConcurrencyController(self.client.token_manager)

        # Phase 1: Resolver Pipeline
        resolver = StarRangeResolver(self.client)
        log.info("phase_started", phase="resolution", action="resolving_star_brackets")
        brackets = await resolver.resolve_ranges(
            search_query, sample_size
        )

        log.info("phase_completed", phase="resolution", brackets_resolved=len(brackets))

        # Phase 2: Sweep Pipeline
        sweep_runner = SweepRunner(self.client)
        log.info("phase_started", phase="sweep", action="harvesting_node_ids")
        context.ids = await sweep_runner.run_sweep_all(
            sweep_graphql=context.sweep_graphql,
            search_query=search_query,
            sample_size=sample_size,
            brackets=brackets,
            concurrency_controller=concurrency_controller,
        )

        log.info("phase_completed", phase="sweep", harvested_ids=len(context.ids))

        # Phase 3: Hydration Pipeline
        hydrate_runner = HydrateRunner(self.client)
        log.info(
            "phase_started",
            phase="hydration",
            action="fetching_ast_fields",
            total_to_hydrate=len(context.ids),
        )
        context.data = await hydrate_runner.run_hydrate_all(
            hydrate_graphql=context.hydrate_graphql,
            query_obj=query_obj,
            all_ids=context.ids,
            concurrency_controller=concurrency_controller,
        )

        log.info(
            "pipeline_completed",
            phase="finalization",
            final_hydrated_count=len(context.data),
        )

        return context.data[:sample_size]

import argparse
import asyncio
import logging
import os

import structlog

from src.core.config import settings
from src.core.github_client import GitHubClient
from src.engine.distributed_query_runner import DistributedQueryRunner
from src.graphql.query_loader import QueryLoader
from src.storage.csv_manager import CSVManager

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger(__name__)


async def run_all():
    parser = argparse.ArgumentParser(description="Run Lab 01 Data Extractions")
    parser.add_argument(
        "--rq",
        choices=["1", "2", "3", "4", "5", "6", "all", "unified"],
        default="all",
        help="Which research question extraction to run",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge all outputs into a single CSV file (all_results.csv)",
    )
    args = parser.parse_args()

    client = GitHubClient(
        tokens=settings.github_tokens, url=settings.github_graphql_url
    )

    # Setup Managers
    output_dir = os.path.join(os.path.dirname(__file__), "dados")
    csv_manager = CSVManager(output_dir)

    queries_dir = os.path.join(os.path.dirname(__file__), "queries")
    query_loader = QueryLoader(queries_dir)
    query_runner = DistributedQueryRunner(client)

    if args.rq == "all":
        rqs_to_run = ["1", "2", "3", "4", "5", "6"]
    elif args.rq == "unified":
        rqs_to_run = ["unified"]
    else:
        rqs_to_run = [args.rq]

    async def execute_rq(rq):
        rq_name = f"rq0{rq}" if rq != "unified" else "unified"

        # Bind context to a local logger instance for this entire RQ run
        log = logger.bind(
            research_question=rq_name, target_sample_size=settings.sample_size
        )
        log.info("starting_extraction")

        query_obj = query_loader.load_query(rq_name)
        data = await query_runner.run_query(query_obj, settings.sample_size)

        csv_manager.save(data, f"{rq_name}_sample.csv")
        log.info(
            "extraction_completed",
            extracted_records=len(data),
            destination=f"{rq_name}_sample.csv",
        )
        return data

    tasks = [execute_rq(rq) for rq in rqs_to_run]
    all_datasets = await asyncio.gather(*tasks)

    await client.close()

    if args.merge:
        logger.info("merging_results_started", destination="all_results.csv")
        csv_manager.merge_and_save(all_datasets, "all_results.csv", merge_key="repo")
        logger.info("merging_results_completed", destination="all_results.csv")


def main():
    asyncio.run(run_all())


if __name__ == "__main__":
    main()

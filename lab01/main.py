import os
import argparse
from src.config import settings
from src.github_client import GitHubClient
from src.csv_manager import CSVManager
from src.query_runner import QueryRunner
from src.query_loader import QueryLoader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run Lab 01 Data Extractions")
    parser.add_argument(
        "--rq", 
        choices=["1", "2", "3", "4", "5", "6", "all", "unified"], 
        default="all", 
        help="Which research question extraction to run"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge all outputs into a single CSV file (all_results.csv)"
    )
    args = parser.parse_args()

    client = GitHubClient(tokens=settings.github_tokens, url=settings.github_graphql_url)
    
    # Setup Managers
    output_dir = os.path.join(os.path.dirname(__file__), "dados")
    csv_manager = CSVManager(output_dir)
    
    queries_dir = os.path.join(os.path.dirname(__file__), "queries")
    query_loader = QueryLoader(queries_dir)
    query_runner = QueryRunner(client)

    if args.rq == "all":
        rqs_to_run = ["1", "2", "3", "4", "5", "6"]
    elif args.rq == "unified":
        rqs_to_run = ["unified"]
    else:
        rqs_to_run = [args.rq]

    all_datasets = []

    for rq in rqs_to_run:
        rq_name = f"rq0{rq}" if rq != "unified" else "unified"
        logger.info(f"Running {rq_name.upper()}...")
        
        query_obj = query_loader.load_query(rq_name)
        data = query_runner.run_query(query_obj, settings.sample_size)
        
        csv_manager.save(data, f"{rq_name}_sample.csv")
        all_datasets.append(data)
        logger.info(f"Saved {len(data)} records for {rq_name.upper()}.\n")

    if args.merge:
        logger.info("Merging all results into a single CSV...")
        csv_manager.merge_and_save(all_datasets, "all_results.csv", merge_key="repo")
        logger.info("Successfully merged and saved to all_results.csv.\n")

if __name__ == "__main__":
    main()

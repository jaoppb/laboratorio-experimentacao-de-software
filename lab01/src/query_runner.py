import os
from datetime import datetime, timezone
from typing import List, Dict
from src.github_client import GitHubClient
from src.query import Query
import logging

logger = logging.getLogger(__name__)

class QueryRunner:
    def __init__(self, client: GitHubClient):
        self.client = client

    def run_query(self, query_obj: Query, sample_size: int) -> List[Dict]:
        results = []
        cursor = None
        
        # Dynamically load the best batch size from the JSON declarative configuration
        connections = query_obj.metadata.connections
        batch_size = query_obj.metadata.optimal_batch_size
            
        logger.info(f"  [Optimizer] Selected batch size of {batch_size} for {connections} connection(s)")
        
        while len(results) < sample_size:
            fetch_count = min(batch_size, sample_size - len(results))
            variables = {
                "searchQuery": "stars:>1 sort:stars-desc",
                "first": fetch_count,
                "after": cursor
            }
            
            # Print the calculated metadata points before querying
            theoretical_cost = query_obj.calculate_theoretical_cost(fetch_count)
            query_obj.metadata.last_theoretical_cost = theoretical_cost
            logger.info(f"  [Calculated Metadata] Expected Cost: {theoretical_cost} points")
            
            data = self.client.run_query(query_obj.content, variables)
            
            if "rateLimit" in data["data"]:
                rl = data["data"]["rateLimit"]
                query_obj.metadata.last_actual_cost = rl['cost']
                logger.info(f"  [RateLimit] Actual Cost: {rl['cost']} points | Remaining: {rl['remaining']} points")
                
            search_data = data["data"]["search"]
            nodes = search_data["nodes"]
            
            for repo in nodes:
                # Add check in case nodes is smaller than fetch_count somehow (e.g. at end of list)
                if not repo:
                    continue
                
                parsed_row = {}
                env = {
                    "repo": repo,
                    "datetime": datetime,
                    "timezone": timezone
                }
                
                for target_col, python_expr in query_obj.metadata.mappings.items():
                    try:
                        parsed_row[target_col] = eval(python_expr, env)
                    except Exception as e:
                        logger.error(f"Error evaluating '{python_expr}' for {target_col}: {e}")
                        parsed_row[target_col] = None
                        
                results.append(parsed_row)
            
            page_info = search_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break
                
            cursor = page_info["endCursor"]
            
        return results

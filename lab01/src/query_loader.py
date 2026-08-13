import os
import json
from src.query import Query, QueryMetadata

class QueryLoader:
    def __init__(self, queries_dir: str):
        self.queries_dir = queries_dir

    def load_query(self, rq_name: str) -> Query:
        query_path = os.path.join(self.queries_dir, f"{rq_name}.graphql")
        json_path = os.path.join(self.queries_dir, f"{rq_name}.json")
        
        with open(query_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        with open(json_path, "r", encoding="utf-8") as f:
            raw_mappings = json.load(f)
            
        connections = raw_mappings.pop("__connections__", 0)
        optimal_batch_size = raw_mappings.pop("__optimal_batch_size__", 5)
        
        metadata = QueryMetadata(
            connections=connections,
            optimal_batch_size=optimal_batch_size,
            mappings=raw_mappings
        )
            
        return Query(name=rq_name, content=content, metadata=metadata)

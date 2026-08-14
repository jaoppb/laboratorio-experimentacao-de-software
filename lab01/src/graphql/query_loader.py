import json
import os

from src.graphql.query import Query, QueryMetadata


class QueryLoader:
    def __init__(self, queries_dir: str):
        self.queries_dir = queries_dir

    def load_query(self, rq_name: str) -> Query:
        query_path = os.path.join(self.queries_dir, f"{rq_name}.graphql")
        json_path = os.path.join(self.queries_dir, f"{rq_name}.json")

        with open(query_path, "r", encoding="utf-8") as f:
            content = f.read()

        with open(json_path, "r", encoding="utf-8") as f:
            metadata_json = json.load(f)

        metadata = QueryMetadata(**metadata_json)

        return Query(name=rq_name, content=content, metadata=metadata)

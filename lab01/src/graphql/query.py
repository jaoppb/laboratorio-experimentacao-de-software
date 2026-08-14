from dataclasses import dataclass
from typing import Dict

from pydantic import BaseModel


class QueryConfig(BaseModel):
    connections: int
    optimal_batch_size: int = 10
    cost: int


class QueryMetadata(BaseModel):
    config: QueryConfig
    extractors: Dict[str, str]
    last_theoretical_cost: int = 0
    last_actual_cost: int = 0


@dataclass
class Query:
    name: str
    content: str
    metadata: QueryMetadata

    def calculate_theoretical_cost(self, first: int) -> int:
        """
        Calculates the theoretical GitHub GraphQL point cost.
        Reads the declarative cost directly from the JSON metadata.
        """
        return self.metadata.config.cost

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class QueryMetadata:
    connections: int
    optimal_batch_size: int
    mappings: Dict[str, str] = field(default_factory=dict)
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
        Base cost is 1 point for the initial query.
        Each nested connection adds 1 point per node.
        """
        return 1 + (first * self.metadata.connections)

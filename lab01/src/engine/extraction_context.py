from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.graphql.query import Query


@dataclass
class ExtractionContext:
    """
    Pipeline Context that flows through the DistributedQueryRunner.
    Holds the state of the extraction process across all phases.
    """

    sample_size: int
    search_query: str
    query_obj: Query

    # State populated during the pipeline execution
    brackets: List[Tuple[int, int, int]] = field(default_factory=list)
    ids: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)

from abc import ABC, abstractmethod
from typing import Dict, List

from src.graphql.query import Query


class BaseQueryRunner(ABC):
    @abstractmethod
    async def run_query(
        self,
        query_obj: Query,
        sample_size: int,
        search_query: str = "stars:>1 sort:stars-desc",
    ) -> List[Dict]:
        pass

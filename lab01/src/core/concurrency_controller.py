import asyncio
from contextlib import asynccontextmanager
from enum import Enum

import structlog

from src.core.token_manager import TokenManager

logger = structlog.get_logger(__name__)


class QueryWeight(Enum):
    LIGHT = 10  # High concurrency (e.g., ID Sweeping)
    MEDIUM = 5  # Moderate concurrency
    HEAVY = 3  # Strict throttling (e.g., deeply nested Hydration)


class ConcurrencyController:
    def __init__(self, token_manager: TokenManager):
        """
        Calculates maximum mathematically safe concurrency ceilings based on token health and query weight.
        """
        self.token_manager = token_manager
        self.current_active_tasks = 0

    def get_max_concurrency(self, weight: QueryWeight) -> int:
        """
        Returns the safe limit based on currently active tokens and query weight.
        """
        active_tokens = len(self.token_manager.get_active_tokens())
        return max(1, active_tokens * weight.value)

    @asynccontextmanager
    async def acquire(self, weight: QueryWeight = QueryWeight.HEAVY):
        """
        Dynamic async semaphore context manager that adapts to weight.
        """
        while self.current_active_tasks >= self.get_max_concurrency(weight):
            await asyncio.sleep(0.05)
        self.current_active_tasks += 1
        try:
            yield self
        finally:
            self.current_active_tasks -= 1

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TokenState:
    key: str
    remaining: int = 5000
    reset_at: datetime = None

    def is_active(self) -> bool:
        if self.remaining > 50:
            return True
        if self.reset_at and datetime.now(timezone.utc) >= self.reset_at:
            return True
        return False


class TokenManager:
    def __init__(self, tokens: List[str]):
        if not tokens:
            raise ValueError("No GitHub tokens provided.")
        self.tokens = [TokenState(key=t) for t in tokens]
        self.current_index = 0
        self._lock = asyncio.Lock()

    def get_active_tokens(self) -> List[TokenState]:
        return [t for t in self.tokens if t.is_active()]

    async def get_next_token(self) -> str:
        """
        Returns the next active token using round-robin.
        If all tokens are exhausted, pauses execution until the closest reset time.
        """
        async with self._lock:
            active_tokens = self.get_active_tokens()

            if not active_tokens:
                # All tokens exhausted! Find the closest reset time
                valid_resets = [
                    t.reset_at for t in self.tokens if t.reset_at is not None
                ]
                if not valid_resets:
                    # Fallback if reset times aren't parsed yet
                    sleep_time = 60
                else:
                    closest_reset = min(valid_resets)
                    sleep_time = (
                        closest_reset - datetime.now(timezone.utc)
                    ).total_seconds() + 5
                    sleep_time = max(10, sleep_time)  # Minimum sleep 10s

                logger.warning(
                    f"ALL TOKENS EXHAUSTED! Global pause for {sleep_time:.0f} seconds until next reset..."
                )
                await asyncio.sleep(sleep_time)
                # After sleeping, tokens should be active again
                # But we just return the first one safely to resume
                return self.tokens[0].key

            # Find the next active token starting from current_index
            for _ in range(len(self.tokens)):
                self.current_index = (self.current_index + 1) % len(self.tokens)
                if self.tokens[self.current_index].is_active():
                    return self.tokens[self.current_index].key

            # Fallback
            return active_tokens[0].key

    def update_token_state(self, token_key: str, remaining: int, reset_at_iso: str):
        """
        Passively called after successful API queries to update perfect token health.
        """
        try:
            # Parse GitHub ISO 8601 string (e.g. "2024-03-01T12:00:00Z")
            reset_dt = datetime.strptime(
                reset_at_iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z"
            )
            for t in self.tokens:
                if t.key == token_key:
                    t.remaining = remaining
                    t.reset_at = reset_dt
                    break
        except Exception as e:
            logger.error(f"Failed to parse token state: {e}")

    def mark_exhausted(self, token_key: str):
        """
        Forcefully exhaust a token if a 403 Rate Limit is hit before parsing.
        """
        for t in self.tokens:
            if t.key == token_key:
                t.remaining = 0
                break

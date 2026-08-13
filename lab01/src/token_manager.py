import logging
from typing import List

logger = logging.getLogger(__name__)

class TokenManager:
    def __init__(self, tokens: List[str]):
        if not tokens:
            raise ValueError("No GitHub tokens provided.")
        self.tokens = tokens
        self.current_token_index = 0

    @property
    def current_token(self) -> str:
        return self.tokens[self.current_token_index]

    @property
    def current_index(self) -> int:
        return self.current_token_index

    def rotate(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        logger.info(f"Rotated to token index {self.current_token_index}")

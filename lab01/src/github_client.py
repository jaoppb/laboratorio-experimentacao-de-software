import asyncio
import logging
import httpx
from httpx import RequestError, HTTPStatusError
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, tokens: list[str], url: str):
        self.token_manager = TokenManager(tokens)
        self.url = url
        self.async_client = httpx.AsyncClient(timeout=30.0)

    async def run_query(self, query: str, variables: dict = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            token = self.token_manager.current_token
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            try:
                response = await self.async_client.post(
                    self.url,
                    json={"query": query, "variables": variables or {}},
                    headers=headers
                )
                
                if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
                    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                    if remaining == 0:
                        logger.warning(f"Rate limit hit for token {self.token_manager.current_index}.")
                        self.token_manager.rotate()
                        continue
                
                response.raise_for_status()
                payload = response.json()
                
                if "errors" in payload:
                    error_messages = [err.get("message", "") for err in payload.get("errors", [])]
                    if any("rate limit" in msg.lower() for msg in error_messages):
                        logger.warning("Rate limit hit in GraphQL response.")
                        self.token_manager.rotate()
                        continue
                    raise RuntimeError(payload["errors"])
                
                return payload
            
            except (RequestError, HTTPStatusError) as e:
                logger.error(f"Request failed: {e}")
                await asyncio.sleep(2 ** attempt)
                
        raise Exception("Max retries exceeded or all tokens exhausted")
        
    async def close(self):
        await self.async_client.aclose()

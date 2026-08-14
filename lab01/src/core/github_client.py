import httpx
import structlog

from src.core.resilience import with_graphql_retry
from src.core.token_manager import TokenManager

logger = structlog.get_logger(__name__)


class GitHubClient:
    def __init__(self, tokens: list[str], url: str):
        self.token_manager = TokenManager(tokens)
        self.url = url
        self.async_client = httpx.AsyncClient(timeout=30.0)

    @with_graphql_retry(max_retries=10, abuse_cooldown=15)
    async def run_query(self, query: str, variables: dict | None = None) -> dict:
        token = await self.token_manager.get_next_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await self.async_client.post(
            self.url,
            json={"query": query, "variables": variables or {}},
            headers=headers,
        )

        if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            if remaining == 0:
                logger.warning("primary_rate_limit_exhausted", token_masked=token[:4])
                self.token_manager.mark_exhausted(token)
                # Since the decorator catches errors, we raise here to trigger a retry
                response.raise_for_status()

        response.raise_for_status()
        payload = response.json()

        if "errors" in payload:
            error_messages = [
                err.get("message", "") for err in payload.get("errors", [])
            ]
            if any("rate limit" in msg.lower() for msg in error_messages):
                logger.warning("graphql_rate_limit_error", token_masked=token[:4])
                self.token_manager.mark_exhausted(token)
                raise RuntimeError("GraphQL Rate Limit Hit")
            raise RuntimeError(payload["errors"])

        # Passively map real-time token health from the successful response payload
        rate_limit_info = payload.get("data", {}).get("rateLimit")
        if rate_limit_info:
            self.token_manager.update_token_state(
                token,
                remaining=rate_limit_info.get("remaining", 0),
                reset_at_iso=rate_limit_info.get("resetAt", ""),
            )

        return payload

    async def close(self):
        await self.async_client.aclose()

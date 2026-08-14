import asyncio

import httpx

from src.core.config import settings


async def check():
    tokens = settings.github_tokens
    print(f"Found {len(tokens)} tokens in .env")

    query = """
    query {
      rateLimit {
        cost
        remaining
        resetAt
      }
    }
    """

    async with httpx.AsyncClient() as client:
        for i, token in enumerate(tokens):
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            resp = await client.post(
                "https://api.github.com/graphql", json={"query": query}, headers=headers
            )

            masked = token[:6] + "..." + token[-4:] if len(token) > 10 else token
            if resp.status_code == 200:
                data = resp.json().get("data", {}).get("rateLimit", {})
                remaining = data.get("remaining")
                reset = data.get("resetAt")
                print(
                    f"Token {i + 1} ({masked}): {remaining} points remaining. Resets at {reset}"
                )
            else:
                print(
                    f"Token {i + 1} ({masked}): FAILED ({resp.status_code}) - {resp.text}"
                )


asyncio.run(check())

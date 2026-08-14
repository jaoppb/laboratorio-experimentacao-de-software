import asyncio
from typing import Any, Callable, List, Union

import structlog
from httpx import HTTPStatusError, RequestError

logger = structlog.get_logger(__name__)


def is_gateway_timeout(e: Exception) -> bool:
    if isinstance(e, RequestError):
        return True
    if isinstance(e, HTTPStatusError) and e.response.status_code in (502, 504):
        return True
    return False


def with_graphql_retry(max_retries: int = 10, abuse_cooldown: int = 15):
    """
    Decorator for purely handling network drops and 403 Secondary Rate Limits.
    It instantly re-raises 502/504 errors so the adaptive payload halver can catch them.
    """

    def decorator(func: Callable):
        async def wrapper(self, *args, **kwargs):
            for _attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    if is_gateway_timeout(e):
                        raise e  # Immediately propagate to adaptive halving logic

                    if isinstance(e, HTTPStatusError) and e.response.status_code == 403:
                        logger.warning(
                            "secondary_rate_limit_triggered",
                            cooldown_seconds=abuse_cooldown,
                        )
                        await asyncio.sleep(abuse_cooldown)
                        continue

                    logger.error(
                        "network_request_failed", error=str(e), next_retry_in="1s"
                    )
                    await asyncio.sleep(1)

            raise Exception("Max retries exceeded")

        return wrapper

    return decorator


async def execute_with_adaptive_halving(
    func: Callable, payload: Union[List[str], int], *args, **kwargs
) -> Any:
    """
    Universally executes a function and recursively halves its payload if a 502/504 occurs.
    If `payload` is a List, it splits it in half, runs both halves concurrently, and merges the results.
    If `payload` is an int (e.g. max_batch_size), it reduces the int and yields the smaller execution.
    """
    try:
        return await func(payload, *args, **kwargs)
    except Exception as e:
        if is_gateway_timeout(e):
            logger.warning("gateway_timeout_detected", action="adapting_payload")

            if isinstance(payload, list):
                if len(payload) <= 1:
                    logger.error(
                        "payload_cannot_be_halved_further", payload_size=len(payload)
                    )
                    raise e

                mid = len(payload) // 2
                logger.info(
                    "splitting_payload",
                    original_size=len(payload),
                    left_size=mid,
                    right_size=len(payload) - mid,
                )

                left_results, right_results = await asyncio.gather(
                    execute_with_adaptive_halving(func, payload[:mid], *args, **kwargs),
                    execute_with_adaptive_halving(func, payload[mid:], *args, **kwargs),
                )
                return left_results + right_results

            elif isinstance(payload, int):
                if payload <= 10:
                    logger.error(
                        "batch_size_cannot_be_reduced_further", batch_size=payload
                    )
                    raise e

                new_payload = max(10, payload // 2)
                logger.info(
                    "reducing_batch_size", original_size=payload, new_size=new_payload
                )
                await asyncio.sleep(5)
                return await execute_with_adaptive_halving(
                    func, new_payload, *args, **kwargs
                )

        # If it's not a gateway timeout, propagate it
        raise e

"""One bounded connection pool per process; never log Redis credentials."""

from functools import lru_cache
from redis import Redis
from .settings import settings


@lru_cache
def redis_client() -> Redis | None:
    url = settings().redis_url
    if not url:
        return None
    return Redis.from_url(
        url,
        socket_connect_timeout=0.5,
        socket_timeout=1,
        max_connections=30,
        decode_responses=False,
        health_check_interval=30,
    )


def close_redis() -> None:
    client = redis_client()
    if client is not None:
        client.close()
    redis_client.cache_clear()

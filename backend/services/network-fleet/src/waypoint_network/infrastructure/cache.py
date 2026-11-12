"""Cache transport-safe reference snapshots; invalidate only committed owner changes."""

from collections.abc import Callable
from typing import TypeVar
from pydantic import TypeAdapter
from waypoint_runtime.cache import JsonCache, scoped_key
from waypoint_runtime.redis_client import redis_client
from waypoint_runtime.settings import settings
from waypoint_security import Principal

T = TypeVar("T")


def reference_cache() -> JsonCache:
    return JsonCache(
        redis_client(), settings().runtime_namespace + ":network-reference"
    )


def cached_reference(
    user: Principal,
    operation: str,
    filters: dict[str, str | bool | None],
    adapter: TypeAdapter[T],
    load: Callable[[], object],
) -> T:
    key = scoped_key(
        user.role, user.id, user.outlet_id, user.depot_id, operation, filters
    )
    return reference_cache().get_or_load(
        key,
        adapter,
        lambda: adapter.validate_python(load()),
        settings().reference_cache_ttl_seconds,
    )

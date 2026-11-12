"""Schema-validated cache-aside with generation invalidation and owned distributed locks."""

import hashlib
import json
import secrets
import time
from collections.abc import Callable
from typing import TypeVar
from pydantic import TypeAdapter, ValidationError
from redis import Redis
from redis.exceptions import RedisError

T = TypeVar("T")
RELEASE = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end"


class JsonCache:
    def __init__(self, client: Redis | None, namespace: str) -> None:
        self.client = client
        self.namespace = namespace

    def invalidate(self) -> None:
        if self.client is not None:
            try:
                self.client.incr(self.namespace + ":generation")
            except RedisError:
                # Existing entries expire; a Redis outage must not turn a committed write into HTTP 500.
                return

    def get_or_load(
        self, key: str, adapter: TypeAdapter[T], load: Callable[[], T], ttl: int = 30
    ) -> T:
        client = self.client
        if client is None:
            return load()
        try:
            generation = client.get(self.namespace + ":generation") or b"0"
            digest = hashlib.sha256(key.encode()).hexdigest()
            stamp = generation.decode() if isinstance(generation, bytes) else generation
            cache_key = f"{self.namespace}:{stamp}:{digest}"
            encoded = client.get(cache_key)
            if encoded is not None:
                try:
                    return adapter.validate_json(encoded)
                except (ValidationError, ValueError):
                    client.delete(cache_key)
            lock = cache_key + ":lock"
            token = secrets.token_hex(16)
            owned = client.set(lock, token, nx=True, px=5000)
            if not owned:
                # Bounded contention wait; API route handlers execute in worker threads.
                deadline = time.monotonic() + 0.15
                while time.monotonic() < deadline:
                    time.sleep(0.01)
                    encoded = client.get(cache_key)
                    if encoded is not None:
                        try:
                            return adapter.validate_json(encoded)
                        except ValidationError:
                            break
                return load()
        except RedisError:
            return load()
        try:
            result = load()
            try:
                client.set(cache_key, adapter.dump_json(result), ex=ttl)
            except RedisError:
                pass
            return result
        finally:
            if owned:
                try:
                    client.eval(RELEASE, 1, lock, token)
                except RedisError:
                    pass


def scoped_key(
    role: str,
    user_id: int,
    outlet: str | None,
    depot: str | None,
    operation: str,
    filters: dict[str, str | bool | None],
) -> str:
    return json.dumps(
        [role, user_id, outlet, depot, operation, filters],
        sort_keys=True,
        separators=(",", ":"),
    )

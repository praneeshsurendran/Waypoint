"""Atomic token buckets across replicas; unverified claims never select a user bucket."""

import hashlib
import ipaddress
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal
from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError
from .redis_client import redis_client
from .settings import settings

Category = Literal["login", "client", "reads", "writes", "planning", "bulk"]
# Redis TIME avoids clock skew between API replicas; TTL bounds abandoned buckets.
TOKEN_BUCKET = """
local now = redis.call('TIME')
local stamp = tonumber(now[1]) * 1000 + tonumber(now[2]) / 1000
local capacity = tonumber(ARGV[1])
local window = tonumber(ARGV[2]) * 1000
local state = redis.call('HMGET', KEYS[1], 'tokens', 'stamp')
local tokens = tonumber(state[1]) or capacity
local previous = tonumber(state[2]) or stamp
tokens = math.min(capacity, tokens + math.max(0, stamp - previous) * capacity / window)
local allowed = 0
local retry = 0
if tokens >= 1 then tokens = tokens - 1; allowed = 1
else retry = math.ceil((1 - tokens) * window / capacity / 1000) end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'stamp', stamp)
redis.call('PEXPIRE', KEYS[1], math.ceil(window * 2))
return {allowed, retry}
"""


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0


class TokenBucket:
    def __init__(self, client: Redis, namespace: str) -> None:
        self.client = client
        self.namespace = namespace

    def consume(
        self, identity: str, category: Category, capacity: int, window: int
    ) -> Decision:
        digest = hashlib.sha256(identity.encode()).hexdigest()
        result = self.client.eval(
            TOKEN_BUCKET,
            1,
            f"{self.namespace}:rate:{category}:{digest}",
            capacity,
            window,
        )
        return Decision(bool(result[0]), max(1, int(result[1])) if not result[0] else 0)


class LocalReadFallback:
    """Bounded per-instance reads during Redis failure; never used for login or mutations."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()

    def consume(self, key: str, capacity: int, window: int) -> Decision:
        with self.lock:
            now = time.monotonic()
            tokens, previous = self.buckets.pop(key, (float(capacity), now))
            tokens = min(capacity, tokens + max(0, now - previous) * capacity / window)
            allowed = tokens >= 1
            self.buckets[key] = (tokens - 1 if allowed else tokens, now)
            while len(self.buckets) > 4096:
                self.buckets.popitem(last=False)
            return Decision(
                allowed,
                0 if allowed else max(1, math.ceil((1 - tokens) * window / capacity)),
            )


_fallback = LocalReadFallback()


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    networks = [
        ipaddress.ip_network(value.strip())
        for value in settings().trusted_proxy_cidrs.split(",")
        if value.strip()
    ]

    def trusted(value: str) -> bool:
        try:
            address = ipaddress.ip_address(value)
            return any(address in network for network in networks)
        except ValueError:
            return False

    if not trusted(peer):
        return peer
    chain = [
        part.strip()
        for part in request.headers.get("x-forwarded-for", "").split(",")
        if part.strip()
    ]
    # Walk from the actual peer through explicitly trusted proxies, never trust an arbitrary leftmost header.
    for candidate in reversed(chain):
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return peer
        if not trusted(candidate):
            return candidate
    return chain[0] if chain else peer


def category_for(request: Request) -> Category:
    path = request.url.path
    if path.endswith("/auth/login"):
        return "login"
    if (
        "/planning/jobs" in path
        and request.method == "POST"
        or path.endswith("/auto-plan")
    ):
        return "planning"
    if (
        path.endswith("/driver/sync")
        and request.method == "POST"
        or path.endswith("/uploads")
    ):
        return "bulk"
    return "reads" if request.method in ("GET", "HEAD") else "writes"


def enforce(request: Request, identity: str, category: Category) -> None:
    config = settings()
    client = redis_client()
    if client is None:
        return
    capacity = {
        "login": config.rate_login,
        "client": config.rate_client,
        "reads": config.rate_reads,
        "writes": config.rate_writes,
        "planning": config.rate_planning,
        "bulk": config.rate_bulk,
    }[category]
    scope = request.app.title
    key = scope + ":" + identity
    try:
        result = TokenBucket(client, config.runtime_namespace).consume(
            key, category, capacity, config.rate_window_seconds
        )
    except RedisError:
        if request.method not in ("GET", "HEAD"):
            raise HTTPException(
                503,
                detail={
                    "code": "RATE_LIMIT_UNAVAILABLE",
                    "message": "Request protection is temporarily unavailable.",
                },
                headers={"Retry-After": "1"},
            ) from None
        result = _fallback.consume(
            category + ":" + key, capacity, config.rate_window_seconds
        )
    if not result.allowed:
        raise HTTPException(
            429,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please retry later.",
            },
            headers={"Retry-After": str(result.retry_after)},
        )


def enforce_user(request: Request, user_id: int) -> None:
    if getattr(request.state, "user_rate_checked", False):
        return
    enforce(request, f"user:{user_id}", category_for(request))
    request.state.user_rate_checked = True

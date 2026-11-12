"""Real Redis integration; keys belong to an isolated, per-test namespace."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, TypeAdapter
from redis import Redis
from starlette.requests import Request
from waypoint_runtime.cache import JsonCache
from waypoint_runtime.rate_limit import TokenBucket, client_address, enforce
from waypoint_runtime.settings import settings
from waypoint_runtime.redis_client import redis_client, close_redis


@pytest.fixture
def runtime(monkeypatch):
    url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:6398/15")
    client = Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=1)
    client.ping()
    prefix = "waypoint-test-" + uuid4().hex
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("REDIS_URL", url)
    monkeypatch.setenv("RUNTIME_NAMESPACE", prefix)
    close_redis()
    settings.cache_clear()
    redis_client.cache_clear()
    try:
        yield client, prefix
    finally:
        keys = list(client.scan_iter(prefix + "*"))
        if keys:
            client.delete(*keys)
        close_redis()
        settings.cache_clear()
        client.close()


def test_atomic_threshold_shared_between_replicas(runtime):
    client, prefix = runtime
    replicas = [TokenBucket(client, prefix), TokenBucket(client, prefix)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(
            pool.map(
                lambda i: replicas[i % 2].consume("user-7", "writes", 8, 60), range(64)
            )
        )
    assert sum(result.allowed for result in outcomes) == 8
    assert all(result.retry_after >= 1 for result in outcomes if not result.allowed)
    assert replicas[0].consume("user-8", "writes", 8, 60).allowed
    assert replicas[0].consume("user-7", "reads", 8, 60).allowed


def test_limit_recovers_with_redis_server_time(runtime):
    client, prefix = runtime
    bucket = TokenBucket(client, prefix)
    assert bucket.consume("client", "login", 1, 1).allowed
    assert not bucket.consume("client", "login", 1, 1).allowed
    time.sleep(1.05)
    assert bucket.consume("client", "login", 1, 1).allowed


def request(method="GET", peer="198.51.100.1", forwarded="203.0.113.2"):
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/api/v1/orders",
            "headers": [(b"x-forwarded-for", forwarded.encode())],
            "client": (peer, 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
            "app": FastAPI(title="test-runtime"),
        }
    )


def test_untrusted_forwarded_headers_do_not_choose_rate_identity(runtime, monkeypatch):
    assert client_address(request()) == "198.51.100.1"
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.16.0.0/12")
    settings.cache_clear()
    assert (
        client_address(request(peer="172.18.0.10", forwarded="1.2.3.4, 198.51.100.8"))
        == "198.51.100.8"
    )
    assert (
        client_address(request(peer="172.18.0.10", forwarded="invalid"))
        == "172.18.0.10"
    )


class Snapshot(BaseModel):
    value: int


def test_schema_cache_hit_invalidation_expiration_and_corruption(runtime):
    client, prefix = runtime
    cache = JsonCache(client, prefix)
    adapter = TypeAdapter(Snapshot)
    calls = []

    def load():
        calls.append(1)
        return Snapshot(value=len(calls))

    assert cache.get_or_load("scope:A", adapter, load, 1).value == 1
    assert cache.get_or_load("scope:A", adapter, load, 1).value == 1
    assert cache.get_or_load("scope:B", adapter, load, 1).value == 2
    cache.invalidate()
    assert cache.get_or_load("scope:A", adapter, load, 1).value == 3
    time.sleep(1.05)
    assert cache.get_or_load("scope:A", adapter, load, 1).value == 4
    for key in client.scan_iter(prefix + ":1:*"):
        client.set(key, b'{"value":"not-an-integer"}', ex=1)
    assert cache.get_or_load("scope:A", adapter, load, 1).value == 5


def test_cache_stampede_is_coordinated_between_instances(runtime):
    client, prefix = runtime
    caches = [JsonCache(client, prefix), JsonCache(client, prefix)]
    calls = []

    def load():
        calls.append(1)
        time.sleep(0.04)
        return Snapshot(value=17)

    with ThreadPoolExecutor(max_workers=12) as pool:
        values = list(
            pool.map(
                lambda i: caches[i % 2].get_or_load(
                    "same", TypeAdapter(Snapshot), load
                ),
                range(24),
            )
        )
    assert all(value.value == 17 for value in values)
    assert len(calls) == 1


def test_redis_outage_falls_back_for_cache_and_bounds_reads_but_denies_writes(
    runtime, monkeypatch
):
    offline = Redis.from_url(
        "redis://127.0.0.1:1/15", socket_connect_timeout=0.05, socket_timeout=0.05
    )
    assert (
        JsonCache(offline, "offline")
        .get_or_load("x", TypeAdapter(Snapshot), lambda: Snapshot(value=9))
        .value
        == 9
    )
    monkeypatch.setattr("waypoint_runtime.rate_limit.redis_client", lambda: offline)
    enforce(request(), "unique-" + uuid4().hex, "reads")
    with pytest.raises(HTTPException) as result:
        enforce(request(method="POST"), "actor", "writes")
    assert result.value.status_code == 503
    assert result.value.headers["Retry-After"] == "1"
    offline.close()


def test_http_429_retry_after_and_verified_identity_isolation(
    runtime, service_clients, monkeypatch
):
    monkeypatch.setenv("RATE_READS", "3")
    settings.cache_clear()
    headers = {}
    for user in ("driver", "dispatcher"):
        response = service_clients["identity"].post(
            "/api/v1/auth/login",
            json={"username": user, "password": "test-role-password"},
        )
        assert response.status_code == 200
        headers[user] = {"Authorization": "Bearer " + response.json()["access_token"]}
    for _ in range(3):
        assert (
            service_clients["network"]
            .get("/api/v1/reference/vehicles", headers=headers["driver"])
            .status_code
            == 200
        )
    denied = service_clients["network"].get(
        "/api/v1/reference/vehicles", headers=headers["driver"]
    )
    assert denied.status_code == 429, denied.text
    assert int(denied.headers["Retry-After"]) > 0
    assert (
        service_clients["network"]
        .get("/api/v1/reference/vehicles", headers=headers["dispatcher"])
        .status_code
        == 200
    )


def test_reference_cache_is_invalidated_after_committed_owner_write(
    runtime, service_clients
):
    client = service_clients["network"]
    token = (
        service_clients["identity"]
        .post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-role-password"},
        )
        .json()["access_token"]
    )
    headers = {"Authorization": "Bearer " + token}
    path = "/api/v1/reference/vehicles/SYNV001"
    assert client.get(path, headers=headers).json()["status"] == "available"
    changed = client.patch(
        path + "/availability", headers=headers, json={"status": "in_workshop"}
    )
    assert changed.status_code == 200, changed.text
    assert client.get(path, headers=headers).json()["status"] == "in_workshop"


def test_login_limit_responses_keep_cors_and_correlation_headers(runtime, monkeypatch):
    from fastapi.testclient import TestClient
    from waypoint_identity.main import create_app

    monkeypatch.setenv("RATE_LOGIN", "1")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    settings.cache_clear()
    with TestClient(create_app()) as client:
        headers = {"Origin": "http://localhost:5173"}
        assert (
            client.post("/api/v1/auth/login", json={}, headers=headers).status_code
            == 422
        )
        limited = client.post("/api/v1/auth/login", json={}, headers=headers)
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) >= 1
        assert limited.headers["Access-Control-Allow-Origin"] == headers["Origin"]
        assert "Retry-After" in limited.headers["Access-Control-Expose-Headers"]
        assert limited.headers["X-Correlation-ID"]

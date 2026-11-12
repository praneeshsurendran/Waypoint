"""Cross-service integration fixtures use real, separately owned PostgreSQL databases."""

import importlib
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-use-only-32")
os.environ.setdefault("UPLOAD_DIR", "/tmp/waypoint-test-uploads")
os.environ.setdefault("DEMO_DELIVERY_DATE", "2024-04-10")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://waypoint@localhost:5432/waypoint_operations_test",
    ),
)


@pytest.fixture
def contexts(monkeypatch):
    url = make_url(os.environ["DATABASE_URL"])
    if not (url.database or "").endswith("_test"):
        raise RuntimeError("Integration fixtures require a disposable _test database")
    modules = {
        "identity": "waypoint_identity.bootstrap",
        "network": "waypoint_network.bootstrap",
        "operations": "app.infrastructure.db.session",
        "notifications": "waypoint_notifications.bootstrap",
    }
    factories = {}
    engines = {}
    connections = []
    try:
        for name, modname in modules.items():
            module = importlib.import_module(modname)
            if name == "operations":
                from app.infrastructure.db.base import Base
                import app.infrastructure.db.all_models  # noqa: F401
            else:
                Base = module.Base
            engine = create_engine(
                url.set(database=f"waypoint_{name}_services_test"), pool_pre_ping=True
            )
            Base.metadata.create_all(engine)
            engines[name] = (engine, Base)
            connection = engine.connect()
            transaction = connection.begin()
            connections.append((connection, transaction))
            factory = sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            factories[name] = factory
            monkeypatch.setattr(module, "SessionLocal", factory)
            if name in ("identity", "network"):
                events = importlib.import_module(
                    f"waypoint_{name}.infrastructure.messaging.outbox"
                )
                events.install(factory)
        for modname, name in [
            ("app.infrastructure.messaging.consumer", "operations"),
            ("app.workers.planning", "operations"),
            ("waypoint_identity.infrastructure.messaging.consumer", "identity"),
            ("waypoint_notifications.application.services.events", "notifications"),
        ]:
            module = importlib.import_module(modname)
            monkeypatch.setattr(module, "SessionLocal", factories[name])
        yield factories
    finally:
        for connection, transaction in reversed(connections):
            if transaction.is_active:
                transaction.rollback()
            connection.close()
        for engine, Base in engines.values():
            Base.metadata.drop_all(engine)
            engine.dispose()


@pytest.fixture
def synthetic(contexts):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "synthetic_seed", Path(__file__).parent / "scripts/seed/synthetic.py"
    )
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed.seed(
        contexts["identity"],
        contexts["network"],
        contexts["operations"],
        password="test-role-password",
        day=__import__("datetime").date(2024, 4, 10),
        sample_orders=False,
    )
    return contexts


@pytest.fixture
def service_clients(synthetic, monkeypatch):
    import httpx
    import waypoint_security
    from fastapi.testclient import TestClient
    from waypoint_identity.main import create_app as identity_app
    from waypoint_network.main import create_app as network_app
    from waypoint_notifications.main import create_app as notifications_app
    from app.main import create_app as operations_app
    from app.core.config import get_settings

    monkeypatch.setenv("IDENTITY_URL", "http://identity")
    monkeypatch.setenv("SERVICE_MODE", "operations")
    get_settings.cache_clear()
    identity = TestClient(identity_app())

    def route_identity(request):
        response = identity.request(
            request.method,
            request.url.path,
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            response.status_code, headers=response.headers, content=response.content
        )

    monkeypatch.setattr(
        waypoint_security,
        "client_factory",
        lambda **kwargs: httpx.Client(
            transport=httpx.MockTransport(route_identity), **kwargs
        ),
    )
    clients = {
        "identity": identity,
        "network": TestClient(network_app()),
        "operations": TestClient(operations_app()),
        "notifications": TestClient(notifications_app()),
    }
    try:
        yield clients
    finally:
        for client in clients.values():
            client.close()
        get_settings.cache_clear()

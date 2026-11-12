import json
from pathlib import Path
from waypoint_identity.main import create_app as identity_app
from waypoint_network.main import create_app as network_app
from waypoint_notifications.main import create_app as notifications_app
from app.main import create_app as operations_app
from app.core.config import get_settings


def test_every_legacy_method_and_path_has_an_owner(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "operations")
    get_settings.cache_clear()
    try:
        services = [
            identity_app(),
            network_app(),
            operations_app(),
            notifications_app(),
        ]
        actual = {
            (method, path)
            for app in services
            for path, methods in app.openapi()["paths"].items()
            for method in methods
        }
        baseline = json.loads(
            (
                Path(__file__).parents[2] / "packages/contracts/openapi/legacy-v1.json"
            ).read_text()
        )
        expected = {
            (method, path)
            for path, methods in baseline["paths"].items()
            for method in methods
        }
        assert expected <= actual
        # Existing success statuses are retained for each frontend-used operation.
        for path, methods in baseline["paths"].items():
            for method, contract in methods.items():
                statuses = {key for key in contract["responses"] if key.startswith("2")}
                matches = [
                    app.openapi()["paths"][path][method]
                    for app in services
                    if method in app.openapi()["paths"].get(path, {})
                ]
                assert any(statuses <= set(value["responses"]) for value in matches), (
                    method,
                    path,
                )
    finally:
        get_settings.cache_clear()


def test_isolated_services_never_expose_other_owners_routes(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "operations")
    get_settings.cache_clear()
    try:
        paths = operations_app().openapi()["paths"]
        assert "/api/v1/auth/login" not in paths
        assert "/api/v1/admin/users" not in paths
        assert "/api/v1/reference/vehicles" not in paths
    finally:
        get_settings.cache_clear()


def test_legacy_request_fields_and_response_shapes_are_preserved(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "operations")
    get_settings.cache_clear()
    baseline = json.loads(
        (
            Path(__file__).parents[2] / "packages/contracts/openapi/legacy-v1.json"
        ).read_text()
    )
    try:
        documents = [
            factory().openapi()
            for factory in (
                identity_app,
                network_app,
                operations_app,
                notifications_app,
            )
        ]

        def compare(old, new, document, response, seen=None):
            seen = set() if seen is None else seen
            pair = (old.get("$ref"), new.get("$ref"))
            if pair != (None, None):
                if pair in seen:
                    return
                seen = seen | {pair}
            if "$ref" in old:
                old = baseline["components"]["schemas"][old["$ref"].rsplit("/", 1)[1]]
            if "$ref" in new:
                new = document["components"]["schemas"][new["$ref"].rsplit("/", 1)[1]]
            if "properties" in old:
                assert set(old["properties"]) <= set(new.get("properties", {}))
                if not response:
                    assert set(new.get("required", [])) <= set(old.get("required", []))
                for key, schema in old["properties"].items():
                    compare(schema, new["properties"][key], document, response, seen)
            if "items" in old:
                compare(old["items"], new["items"], document, response, seen)
            for key in ("anyOf", "oneOf"):
                if key in old:
                    assert len(old[key]) == len(new[key])
                    for left, right in zip(old[key], new[key]):
                        compare(left, right, document, response, seen)

        for path, methods in baseline["paths"].items():
            for method, operation in methods.items():
                document = next(
                    doc for doc in documents if method in doc["paths"].get(path, {})
                )
                current = document["paths"][path][method]
                old_parameters = {
                    (p["in"], p["name"]) for p in operation.get("parameters", [])
                }
                assert old_parameters <= {
                    (p["in"], p["name"]) for p in current.get("parameters", [])
                }
                for media, body in (
                    operation.get("requestBody", {}).get("content", {}).items()
                ):
                    compare(
                        body["schema"],
                        current["requestBody"]["content"][media]["schema"],
                        document,
                        False,
                    )
                for status, result in operation["responses"].items():
                    if not status.startswith("2"):
                        continue
                    for media, body in result.get("content", {}).items():
                        compare(
                            body["schema"],
                            current["responses"][status]["content"][media]["schema"],
                            document,
                            True,
                        )
    finally:
        get_settings.cache_clear()

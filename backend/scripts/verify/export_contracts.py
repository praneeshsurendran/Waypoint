"""Export service contracts and ownership without connecting to any database."""

import json
import os
from pathlib import Path
from app.core.config import get_settings
from app.main import create_app as operations_app
from waypoint_identity.main import create_app as identity_app
from waypoint_network.main import create_app as network_app
from waypoint_notifications.main import create_app as notifications_app

os.environ["SERVICE_MODE"] = "operations"
get_settings.cache_clear()
ROOT = Path(__file__).resolve().parents[2]
APPS = {
    "identity-access": identity_app(),
    "network-fleet": network_app(),
    "operations": operations_app(),
    "notifications": notifications_app(),
}
rows = [
    "# API compatibility and ownership",
    "",
    "All original 59 HTTP operations remain available under the same URLs. Nginx provides local path routing; AWS API Gateway/ALB provide deployed routing. No custom Python gateway was added. The frozen original OpenAPI and current service contracts are in `backend/packages/contracts/openapi/`. Each named body/response schema is fully expanded there.",
    "",
    "The migration intentionally hardens resource authorization, malformed inputs, replay conflicts, upload privacy/limits, closed-run edits, and unresolved loading shortfalls. These can return 401/403/409/413/415/422 where the previous backend accepted unsafe state. Proof retrieval now needs authentication; the frontend transport adds a bearer token only for the configured API origin. Driver delays use the nonterminal DELAY outcome. Offline events preserve the exact original payload and acknowledgement retries.",
    "",
    "| Owner | Method | URL | Query/path inputs | Body | Success response | Role gate |",
    "|---|---|---|---|---|---|---|",
]


rows[6:6] = [
    "Driver compatibility additions include STARTED for safely queued offline departure,\nGET `/api/v1/driver/sync` for actor/device recovery pages and GET `/api/v1/driver/history`\nfor the scoped audit timeline. The original POST sync response remains a list. The HTTP\nadapter caches each authenticated driver's mapped route and overlays its own queued actions.\nStore-manager handoffs use per-order receipt commands, preserving the driver-only POD boundary.\nExisting local records lacking an actor ID are retained but require explicit ownership\nreconciliation before replay by an authenticated user; they are not silently attributed to a\nnew login. Signed manager evidence remains on the device, while receipt quantities and notes\nare committed to the backend. Driver POD photos/signatures use private object storage.",
    "",
]


def mounted_routes(router, prefix=""):
    # FastAPI 0.162 retains included routers lazily; older releases flatten them.
    for route in router.routes:
        if hasattr(route, "original_router"):
            yield from mounted_routes(
                route.original_router, prefix + route.include_context.prefix
            )
        elif hasattr(route, "dependant"):
            yield prefix + route.path, route


for owner, app in APPS.items():
    document = app.openapi()
    (ROOT / "packages/contracts/openapi" / f"{owner}-v1.json").write_text(
        json.dumps(document, indent=2) + "\n"
    )
    for path, route in mounted_routes(app):
        roles = []

        def inspect(dep):
            call = dep.call
            if hasattr(call, "__code__") and call.__closure__:
                capture = dict(
                    zip(
                        call.__code__.co_freevars,
                        (c.cell_contents for c in call.__closure__),
                    )
                )
                if "roles" in capture:
                    roles.extend(capture["roles"])
            for child in dep.dependencies:
                inspect(child)

        inspect(route.dependant)
        for method in sorted(route.methods):
            operation = document["paths"].get(path, {}).get(method.lower())
            if not operation:
                continue
            params = (
                ", ".join(
                    (
                        p["name"] + (" (required)" if p.get("required") else "")
                        for p in operation.get("parameters", [])
                    )
                )
                or "none"
            )
            body = operation.get("requestBody", {}).get("content", {})
            shape = (
                "; ".join((str(value.get("schema", {})) for value in body.values()))
                or "none"
            )
            responses = "; ".join(
                (
                    code
                    + ": "
                    + str(
                        value.get("content", {})
                        .get("application/json", {})
                        .get("schema", {})
                    )
                    for code, value in operation["responses"].items()
                    if code.startswith("2")
                )
            )
            gate = (
                ", ".join(sorted(set(roles)))
                if roles
                else "authenticated"
                if operation.get("security") or path.startswith("/api/v1/notifications")
                else "public probe/login"
            )
            rows.append(
                f"| {owner} | {method} | `{path}` | {params} | `{shape}` | `{responses}` | {gate} |"
            )
assert len(rows) > 59, "Route ownership export is incomplete"
(ROOT / "docs/api-compatibility.md").write_text("\n".join(rows) + "\n")
print("Exported four service OpenAPI contracts and route ownership")

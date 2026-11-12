"""Check service ownership and pure domain dependencies using Python's AST."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = {
    "operations": "app",
    "identity-access": "waypoint_identity",
    "network-fleet": "waypoint_network",
    "notifications": "waypoint_notifications",
}
errors = []
for service, package in PACKAGES.items():
    for path in (ROOT / "services" / service / "src").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for module in modules:
                if (
                    module.split(".")[0] in PACKAGES.values()
                    and module.split(".")[0] != package
                ):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: imports another service implementation {module}"
                    )
                if "application" in path.parts and module.startswith(package + ".api"):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: application imports API transport"
                    )
                if "domain" in path.parts and (
                    module.split(".")[0]
                    in ("fastapi", "sqlalchemy", "boto3", "botocore")
                    or module.startswith(
                        (package + ".infrastructure", package + ".api")
                    )
                ):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: domain imports implementation {module}"
                    )
for path in (ROOT / "packages/contracts").rglob("*.py"):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        module = node.module if isinstance(node, ast.ImportFrom) else ""
        if module and module.split(".")[0] in (
            *PACKAGES.values(),
            "sqlalchemy",
            "fastapi",
            "boto3",
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: shared contracts import implementation"
            )
if errors:
    raise SystemExit("\n".join(errors))
print("Service ownership and domain dependency checks passed")

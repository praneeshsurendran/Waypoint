"""Apply each migration history twice to explicitly supplied disposable owner databases."""

import json
import os
import subprocess
import sys
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def main():
    root = Path(__file__).resolve().parents[2]
    reports = {}
    for owner, variable in (
        ("identity-access", "IDENTITY_TEST_DATABASE_URL"),
        ("network-fleet", "NETWORK_TEST_DATABASE_URL"),
        ("operations", "OPERATIONS_TEST_DATABASE_URL"),
        ("notifications", "NOTIFICATIONS_TEST_DATABASE_URL"),
    ):
        url = os.environ[variable]
        if not (make_url(url).database or "").endswith("_test"):
            raise RuntimeError(
                "Migration verification requires disposable _test databases"
            )
        directory = root / "services" / owner
        environment = {**os.environ, "DATABASE_URL": url, "ENVIRONMENT": "test"}
        for _ in range(2):
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=directory,
                env=environment,
                check=True,
            )
        config = Config(str(directory / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(
                directory / "alembic"
                if owner == "operations"
                else directory / "migrations"
            ),
        )
        expected = ScriptDirectory.from_config(config).get_current_head()
        engine = create_engine(url, hide_parameters=True)
        try:
            with engine.connect() as connection:
                actual = MigrationContext.configure(connection).get_current_revision()
            assert actual == expected, owner
            reports[owner] = {"head": actual, "second_upgrade": "idempotent"}
        finally:
            engine.dispose()
    print(json.dumps(reports))


if __name__ == "__main__":
    main()

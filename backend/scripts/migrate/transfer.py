"""Non-destructive owner transfer. Dry-run by default; URLs come only from environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from sqlalchemy import MetaData, Table, create_engine, select, text
from waypoint_identity.infrastructure.db.accounts import User
from waypoint_identity.infrastructure.db.projections import (
    Depot as IdentityDepot,
    Outlet as IdentityOutlet,
    Vehicle as IdentityVehicle,
    Trip as IdentityTrip,
)
from waypoint_network.infrastructure.db.reference import (
    Depot,
    Outlet,
    Vehicle,
    CalendarDay,
    VehicleWeeklyFuel,
)

OWNERS = {
    "identity": {"users": User.__table__},
    "network": {
        cls.__tablename__: cls.__table__
        for cls in (Depot, Outlet, Vehicle, CalendarDay, VehicleWeeklyFuel)
    },
}


def checksum(rows):
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def transfer(source, targets, apply=False):
    report = {}
    with source.connect().execution_options(isolation_level="REPEATABLE READ") as old:
        for owner, tables in OWNERS.items():
            with targets[owner].begin() as new:
                for name, target in tables.items():
                    original = Table(name, MetaData(), autoload_with=old)
                    keys = [col.key for col in target.columns if col.key in original.c]
                    pk = [col.key for col in target.primary_key]
                    rows = [
                        dict(row)
                        for row in old.execute(
                            select(*[original.c[key] for key in keys]).order_by(
                                *[original.c[key] for key in pk]
                            )
                        ).mappings()
                    ]
                    for row in rows:
                        where = [target.c[key] == row[key] for key in pk]
                        existing = (
                            new.execute(
                                select(*[target.c[key] for key in keys]).where(*where)
                            )
                            .mappings()
                            .first()
                        )
                        if existing is not None and dict(existing) != row:
                            raise RuntimeError(
                                f"Conflicting existing {owner}/{name} primary key; no overwrite allowed"
                            )
                        if apply and existing is None:
                            new.execute(target.insert().values(**row))
                    if apply:
                        copied = [
                            dict(
                                new.execute(
                                    select(*[target.c[key] for key in keys]).where(
                                        *[target.c[key] == row[key] for key in pk]
                                    )
                                )
                                .mappings()
                                .one()
                            )
                            for row in rows
                        ]
                        if checksum(rows) != checksum(copied):
                            raise RuntimeError(f"Checksum mismatch for {owner}/{name}")
                        for col in target.primary_key:
                            if col.key == "id" and new.dialect.name == "postgresql":
                                new.execute(
                                    text(
                                        "SELECT setval(pg_get_serial_sequence(:table, 'id'), COALESCE((SELECT MAX(id) FROM "
                                        + name
                                        + "),1), EXISTS(SELECT 1 FROM "
                                        + name
                                        + "))"
                                    ),
                                    {"table": name},
                                )
                    report[f"{owner}/{name}"] = {
                        "rows": len(rows),
                        "checksum": checksum(rows),
                        "copied": apply,
                    }
        # Bootstrap identity validation/read projections from the same consistent legacy snapshot.
        with targets["identity"].begin() as identity:
            for name, cls, key in [
                ("depots", IdentityDepot, "code"),
                ("outlets", IdentityOutlet, "outlet_id"),
                ("vehicles", IdentityVehicle, "vehicle_id"),
            ]:
                original = Table(name, MetaData(), autoload_with=old)
                for value in old.scalars(select(original.c[key])):
                    if (
                        apply
                        and identity.scalar(
                            select(cls.__table__.c[key]).where(
                                cls.__table__.c[key] == value
                            )
                        )
                        is None
                    ):
                        identity.execute(cls.__table__.insert().values(**{key: value}))
            original = Table("trips", MetaData(), autoload_with=old)
            for row in old.execute(
                select(
                    original.c.id,
                    original.c.vehicle_id,
                    original.c.trip_number,
                    original.c.status,
                )
            ).mappings():
                if (
                    apply
                    and identity.scalar(
                        select(IdentityTrip.id).where(IdentityTrip.id == row["id"])
                    )
                    is None
                ):
                    identity.execute(
                        IdentityTrip.__table__.insert().values(**dict(row))
                    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-file", type=Path)
    args = parser.parse_args()
    if args.apply and (
        args.backup_file is None
        or not args.backup_file.is_file()
        or args.backup_file.stat().st_size == 0
    ):
        parser.error(
            "--apply requires a nonempty verified backup file; validate it with pg_restore --list first"
        )
    source = create_engine(os.environ["LEGACY_DATABASE_URL"])
    targets = {
        key: create_engine(os.environ[key.upper() + "_DATABASE_URL"]) for key in OWNERS
    }
    if any(engine.url == source.url for engine in targets.values()):
        raise RuntimeError("Source and target databases must differ")
    print(json.dumps(transfer(source, targets, args.apply), indent=2))


if __name__ == "__main__":
    main()

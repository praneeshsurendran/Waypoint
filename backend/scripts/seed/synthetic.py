"""Independent synthetic examples. Never reads or redistributes competition CSVs."""

import datetime as dt
import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from waypoint_identity.infrastructure.db.accounts import User as IdentityUser
from waypoint_identity.infrastructure.db import projections as identity_projection
from waypoint_identity.infrastructure.messaging.outbox import install as identity_events
from waypoint_identity.core.security import hash_password
from waypoint_network.infrastructure.db.reference import (
    Depot,
    Outlet,
    Vehicle,
    CalendarDay,
)
from waypoint_network.infrastructure.messaging.outbox import install as network_events
from app.infrastructure.db.models.user import User
from app.infrastructure.db.models import reference as operation_reference


def seed(identity, network, operations, password, day=None, sample_orders=True):
    day = day or dt.date.fromisoformat(
        os.environ.get(
            "DEMO_DELIVERY_DATE", str(dt.date.today() + dt.timedelta(days=1))
        )
    )
    while day.weekday() == 6:
        day += dt.timedelta(days=1)
    with network.begin() as db:
        for code, lat, lng in [("Peliyagoda", 6.96, 79.90), ("Kandy", 7.29, 80.64)]:
            if not db.get(Depot, code):
                db.add(Depot(code=code, name=code, lat=lat, lng=lng))
        db.flush()
        for index in range(120):
            key = f"SYN{index+1:03}"
            if db.get(Outlet, key):
                continue
            depot = "Peliyagoda" if index % 2 == 0 else "Kandy"
            lat, lng = (6.96, 79.90) if depot == "Peliyagoda" else (7.29, 80.64)
            brand = "Fresh" if index < 80 else "Style" if index < 105 else "Tech"
            db.add(
                Outlet(
                    outlet_id=key,
                    name=f"Synthetic outlet {index+1}",
                    brand=brand,
                    district=f"Synthetic zone {index%12}",
                    depot_code=depot,
                    dock_type="street",
                    parking_constraint="van_only" if index % 20 == 0 else "normal",
                    van_only=index % 20 == 0,
                    is_mall=False,
                    window_open_time=dt.time(5 if brand == "Fresh" else 8),
                    window_close_time=dt.time(8 if brand == "Fresh" else 17),
                    lat=lat + (index % 10) * 0.001,
                    lng=lng + (index % 8) * 0.001,
                )
            )
        for index in range(60):
            key = f"SYNV{index+1:03}"
            if db.get(Vehicle, key):
                continue
            reefer = index < 16
            kind = "van" if 12 <= index < 16 or index >= 48 else "truck"
            db.add(
                Vehicle(
                    vehicle_id=key,
                    type=kind,
                    temp="reefer" if reefer else "ambient",
                    is_refrigerated=reefer,
                    weight_cap_kg=1500 if kind == "van" else 5000,
                    volume_cap_m3=8 if kind == "van" else 25,
                    fuel_type="diesel",
                    km_per_l=8,
                    weekly_fuel_quota_l=450,
                    depot_code="Peliyagoda" if index % 2 == 0 else "Kandy",
                    status="available",
                )
            )
        for offset in range(-7, 29):
            value = day + dt.timedelta(days=offset)
            if db.get(CalendarDay, value):
                continue
            iso = value.isocalendar()
            db.add(
                CalendarDay(
                    date=value,
                    dow=value.weekday(),
                    dow_name=value.strftime("%a"),
                    is_weekend=value.weekday() >= 5,
                    iso_year=iso.year,
                    iso_week=iso.week,
                    is_payday=False,
                    festival_ramp=0,
                    is_holiday=False,
                    monsoon=False,
                    is_operating=value.weekday() != 6,
                )
            )
    with network() as db:
        snapshots = {
            cls.__tablename__: [
                {c.key: getattr(row, c.key) for c in cls.__table__.columns}
                for row in db.scalars(select(cls)).all()
            ]
            for cls in (Depot, Outlet, Vehicle, CalendarDay)
        }
    with identity.begin() as db:
        # Bootstrap only: event consumers maintain these validation projections thereafter.
        for name, cls, key in [
            ("depots", identity_projection.Depot, "code"),
            ("outlets", identity_projection.Outlet, "outlet_id"),
            ("vehicles", identity_projection.Vehicle, "vehicle_id"),
        ]:
            for record in snapshots[name]:
                if not db.get(cls, record[key]):
                    db.add(cls(**{key: record[key]}))
        db.flush()
        for username, role, links in [
            ("dispatcher", "DISPATCHER", {}),
            ("loader", "LOADER", {"depot_id": "Peliyagoda"}),
            ("driver", "DRIVER", {"vehicle_id": "SYNV001", "depot_id": "Peliyagoda"}),
            ("manager", "STORE_MANAGER", {"outlet_id": "SYN001"}),
            ("admin", "ADMIN", {}),
        ]:
            if db.scalar(select(IdentityUser).where(IdentityUser.username == username)):
                continue
            db.add(
                IdentityUser(
                    username=username,
                    password_hash=hash_password(password),
                    full_name=f"Synthetic {role}",
                    role=role,
                    is_active=True,
                    **links,
                )
            )
    with operations.begin() as db:
        for name, records in snapshots.items():
            cls = {
                "depots": operation_reference.Depot,
                "outlets": operation_reference.Outlet,
                "vehicles": operation_reference.Vehicle,
                "calendar_days": operation_reference.CalendarDay,
            }[name]
            key = next(iter(cls.__table__.primary_key)).key
            for record in records:
                if not db.get(cls, record[key]):
                    db.add(
                        cls(
                            **{
                                k: v
                                for k, v in record.items()
                                if k in cls.__table__.columns
                            }
                        )
                    )
        db.flush()
        with identity() as identities:
            users = identities.scalars(select(IdentityUser)).all()
            for user in users:
                if not db.get(User, user.id):
                    data = {
                        c.key: getattr(user, c.key)
                        for c in User.__table__.columns
                        if hasattr(user, c.key)
                    }
                    data["password_hash"] = "!external-identity"
                    db.add(User(**data))
        db.flush()
        if sample_orders:
            from app.infrastructure.db.models.order import Order

            for index in range(120):
                reference = f"SYN-{day}-{index+1:03}"
                if db.scalar(select(Order).where(Order.reference == reference)):
                    continue
                key = f"SYN{index+1:03}"
                brand = "Fresh" if index < 80 else "Style" if index < 105 else "Tech"
                db.add(
                    Order(
                        reference=reference,
                        outlet_id=key,
                        brand=brand,
                        temperature_class="CHILLED" if index < 40 else "AMBIENT",
                        delivery_date=day,
                        status="PLACED",
                        total_cases=20,
                        total_weight=200,
                        total_volume=1,
                        priority=False,
                        cutoff_missed=False,
                    )
                )
    return {"outlets": 120, "vehicles": 60, "roles": 5, "delivery_date": str(day)}


def main():
    if os.environ.get("ENVIRONMENT", "local") == "production":
        raise RuntimeError("Synthetic seeding is local/test only")
    factories = []
    for key in ["IDENTITY_DATABASE_URL", "NETWORK_DATABASE_URL", "DATABASE_URL"]:
        factories.append(
            sessionmaker(
                bind=create_engine(os.environ[key], pool_pre_ping=True),
                expire_on_commit=False,
            )
        )
    identity_events(factories[0])
    network_events(factories[1])
    print(seed(*factories, password=os.environ["DEMO_PASSWORD"]))


if __name__ == "__main__":
    main()

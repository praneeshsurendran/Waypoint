from sqlalchemy.dialects.postgresql import insert
from waypoint_contracts.events import EventEnvelope
from waypoint_identity.bootstrap import SessionLocal
from waypoint_identity.infrastructure.db.models import Inbox, ProjectionVersion
from waypoint_identity.infrastructure.db.projections import Depot, Outlet, Vehicle, Trip


def handle(event: EventEnvelope):
    digest = event.fingerprint()
    with SessionLocal.begin() as db:
        accepted = db.execute(
            insert(Inbox)
            .values(event_id=str(event.event_id), payload_hash=digest)
            .on_conflict_do_nothing()
            .returning(Inbox.event_id)
        ).scalar_one_or_none()
        if not accepted:
            existing = db.get(Inbox, str(event.event_id))
            if existing.payload_hash != digest:
                raise ValueError("event identity conflict")
            return
        if event.event_type == "network.reference_changed":
            if event.source != "network-fleet":
                raise ValueError("untrusted reference producer")
            record = event.data["record"]
            cls, key = {
                "depots": (Depot, "code"),
                "outlets": (Outlet, "outlet_id"),
                "vehicles": (Vehicle, "vehicle_id"),
            }.get(event.data["entity"], (None, None))
            if cls:
                identity = event.aggregate_id
                version = int(event.data["revision"])
                current = db.get(ProjectionVersion, identity, with_for_update=True)
                if current and current.version >= version:
                    return
                if not db.get(cls, record[key]):
                    db.add(cls(**{key: record[key]}))
                db.merge(ProjectionVersion(key=identity, version=version))
        elif event.event_type in (
            "delivery.started",
            "stop.completed",
            "delivery.failed",
            "plan.published",
        ):
            if event.source != "operations":
                raise ValueError("untrusted trip producer")
            for row in event.data.get("trips", []):
                key = f'trip:{row["id"]}'
                version = int(row.get("revision", event.data.get("revision", 0)))
                current = db.get(ProjectionVersion, key, with_for_update=True)
                if current and current.version >= version:
                    continue
                db.merge(
                    Trip(
                        id=row["id"],
                        vehicle_id=row["vehicle_id"],
                        trip_number=row["trip_number"],
                        status=row["status"],
                    )
                )
                db.merge(ProjectionVersion(key=key, version=version))

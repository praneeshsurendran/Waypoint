"""Owned local read projections; never imports identity/network ORM models."""

import datetime as dt
from sqlalchemy.dialects.postgresql import insert
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.messaging.models import Inbox, ProjectionVersion
from app.infrastructure.db.models.user import User
from app.infrastructure.db.models.reference import Depot, Outlet, Vehicle, CalendarDay
from app.infrastructure.db.models.audit import AuditLog

MODELS = {
    "users": User,
    "depots": Depot,
    "outlets": Outlet,
    "vehicles": Vehicle,
    "calendar_days": CalendarDay,
}


def handle(event):
    digest = event.fingerprint()
    with SessionLocal.begin() as db:
        accepted = db.execute(
            insert(Inbox)
            .values(event_id=str(event.event_id), payload_hash=digest)
            .on_conflict_do_nothing()
            .returning(Inbox.event_id)
        ).scalar_one_or_none()
        if not accepted:
            if db.get(Inbox, str(event.event_id)).payload_hash != digest:
                raise ValueError("event identity conflict")
            return
        if event.event_type == "intake.close_requested":
            from app.core import clock
            from app.application.use_cases.orders import close_intake

            if event.source != "scheduler":
                raise ValueError("invalid intake command producer")
            if not clock.is_past_cutoff():
                raise ValueError("cutoff has not occurred")
            actor = db.get(User, event.data["actor_user_id"])
            if actor is None or not actor.is_active or actor.role not in ("DISPATCHER", "ADMIN"):
                raise ValueError("scheduled actor is not authorized")
            # close_intake commits its business state and outbox together; the inbox claim
            # must share that transaction rather than be committed beforehand.
            close_intake(db, actor, None, clock.delivery_date(), commit=False)
            return
        if event.event_type == "orders.closed":
            if event.source != "operations":
                raise ValueError("invalid closure producer")
            import uuid
            from app.infrastructure.messaging.models import PlanningJob
            from app.infrastructure.db.models.plan import Plan
            from app.application.use_cases.locking import lock_run
            from app.infrastructure.messaging.outbox import enqueue

            day = dt.date.fromisoformat(event.data["delivery_date"])
            lock_run(db, day)
            if (
                db.query(Plan)
                .filter(Plan.delivery_date == day, Plan.status.in_(["DRAFT", "PUBLISHED"]))
                .first()
            ):
                return
            if (
                db.query(PlanningJob)
                .filter(PlanningJob.delivery_date == day, PlanningJob.status == "pending")
                .first()
            ):
                return
            key = "closure:" + str(day)
            if not db.query(PlanningJob).filter(PlanningJob.request_key == key).first():
                job = PlanningJob(
                    id=str(uuid.uuid4()),
                    request_key=key,
                    delivery_date=day,
                    requested_by=event.data["actor_user_id"],
                )
                db.add(job)
                enqueue(db, "planning.job_requested", job.id, {"job_id": job.id})
            return
        if event.event_type == "audit.recorded":
            db.add(
                AuditLog(
                    action=event.data["action"],
                    entity_type=event.data["entity_type"],
                    entity_id=event.data["entity_id"],
                    actor_user_id=event.data.get("actor_user_id"),
                    before_json=event.data.get("before"),
                    after_json=event.data.get("after"),
                    created_at=event.occurred_at,
                )
            )
            return
        if event.event_type not in ("identity.user_changed", "network.reference_changed"):
            return
        expected = (
            "identity-access" if event.event_type == "identity.user_changed" else "network-fleet"
        )
        if event.source != expected:
            raise ValueError("event source does not own this projection")
        cls = MODELS[event.data["entity"]]
        version = int(event.data["revision"])
        current = db.get(ProjectionVersion, event.aggregate_id, with_for_update=True)
        if current and current.version >= version:
            return
        data = {
            key: value
            for key, value in event.data["record"].items()
            if key in cls.__table__.columns and key != "password_hash"
        }
        for col in cls.__table__.columns:
            if data.get(col.key) is not None and isinstance(data[col.key], str):
                from sqlalchemy import DateTime, Date, Time

                if isinstance(col.type, DateTime):
                    data[col.key] = dt.datetime.fromisoformat(data[col.key])
                elif isinstance(col.type, Date):
                    data[col.key] = dt.date.fromisoformat(data[col.key])
                elif isinstance(col.type, Time):
                    data[col.key] = dt.time.fromisoformat(data[col.key])
        primary = next(iter(cls.__table__.primary_key)).key
        obj = db.get(cls, data[primary])
        if obj is None:
            if cls is User:
                data["password_hash"] = "!external-identity"
            obj = cls(**data)
            db.add(obj)
        else:
            for key, value in data.items():
                setattr(obj, key, value)
        db.merge(ProjectionVersion(key=event.aggregate_id, version=version))

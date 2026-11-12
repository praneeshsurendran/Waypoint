import datetime as dt
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException


def test_only_one_concurrent_publish_commits():
    from app.infrastructure.db.base import Base
    from app.infrastructure.db.models.plan import Plan
    from app.infrastructure.db.models.user import User
    from app.infrastructure.messaging.models import Outbox
    from app.application.use_cases.plans import publish_plan

    url = make_url(os.environ["DATABASE_URL"])
    assert (url.database or "").endswith("_test")
    engine = create_engine(url.set(database="waypoint_concurrency_test"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory.begin() as db:
            actor = User(
                username="concurrent",
                password_hash="!not-a-login",
                full_name="Concurrent",
                role="DISPATCHER",
                is_active=True,
            )
            db.add(actor)
            db.flush()
            actor_id = actor.id
            plan = Plan(
                delivery_date=dt.date(2024, 4, 10), status="DRAFT", created_by=actor_id
            )
            db.add(plan)
            db.flush()
            plan_id = plan.id
        barrier = Barrier(2)

        def publish():
            with factory() as db:
                actor = db.get(User, actor_id)
                barrier.wait(timeout=10)
                try:
                    result = publish_plan(plan_id, db, actor, None)
                    return result["status"]
                except HTTPException as exc:
                    db.rollback()
                    return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: publish(), range(2)))
        assert sorted(results, key=str) == [409, "PUBLISHED"]
        with factory() as db:
            assert (
                len(db.scalars(select(Plan).where(Plan.status == "PUBLISHED")).all())
                == 1
            )
            assert len(db.scalars(select(Outbox)).all()) == 1
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

"""One job transaction per run; crash rolls back plan and job state together."""

import os
from fastapi import HTTPException
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models.user import User
from app.application.use_cases.locking import lock_run
from app.application.use_cases.planning import run
from waypoint_messaging import SQSQueue
from waypoint_messaging.worker import consume


def handle(event):
    if event.event_type != "planning.job_requested" or event.source != "operations":
        raise ValueError("invalid planning command")
    from app.infrastructure.db.unit_of_work import OperationsUnitOfWork

    with OperationsUnitOfWork(SessionLocal) as uow:
        db = uow.session
        job = uow.jobs.get(event.data["job_id"])
        if job is None:
            raise ValueError("unknown planning job")
        lock_run(db, job.delivery_date)
        job = uow.jobs.get(job.id, for_update=True)
        if job.status in ("cancelled", "succeeded", "failed"):
            return
        user = db.get(User, job.requested_by)
        if not user or not user.is_active or user.role not in ("DISPATCHER", "ADMIN"):
            job.status = "failed"
            job.error_code = "ACTOR_FORBIDDEN"
            uow.jobs.save(job)
            return
        # Bound CPU/DB execution using the worker process/task limit plus a DB timeout.
        from sqlalchemy import text

        db.execute(text("SET LOCAL statement_timeout = '60s'"))
        try:
            with db.begin_nested():
                plan = run(db, user, job.delivery_date)
                job.plan_id = plan.id
                job.status = "succeeded"
        except HTTPException as exc:
            job.status = "failed"
            job.error_code = exc.detail["code"]
        uow.jobs.save(job)


def run_isolated(event):
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "app.workers.planning", "--execute"],
        input=event.model_dump_json(),
        text=True,
        check=True,
        timeout=90,
    )


if __name__ == "__main__":
    import sys

    if "--execute" in sys.argv:
        from waypoint_contracts.events import EventEnvelope

        event = EventEnvelope.model_validate_json(sys.stdin.read())
        from waypoint_observability import correlation_id, traceparent

        correlation_id.set(event.correlation_id)
        traceparent.set(event.traceparent)
        handle(event)
    else:
        consume(SQSQueue(os.environ["PLANNING_QUEUE_URL"]), run_isolated)

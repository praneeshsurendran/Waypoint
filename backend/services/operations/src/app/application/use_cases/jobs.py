from pydantic import TypeAdapter
from waypoint_contracts.jobs import JobRequest
from waypoint_contracts.runtime import JobResult, JobStatus
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from waypoint_security import Actor as Principal
from app.infrastructure.messaging.models import PlanningJob
from app.infrastructure.messaging.outbox import enqueue
from app.application.use_cases.locking import lock_run


def create_job(body: JobRequest, db: Session, user: Principal, _: None = None) -> JobResult:
    lock_run(db, body.delivery_date)
    existing = db.query(PlanningJob).filter(PlanningJob.request_key == body.request_key).first()
    if existing:
        if existing.delivery_date != body.delivery_date or existing.requested_by != user.id:
            raise HTTPException(
                409,
                detail={
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "Job request key is already in use.",
                },
            )
        return TypeAdapter(JobResult).validate_python(
            {"job_id": existing.id, "status": existing.status}
        )
    job = PlanningJob(
        id=str(uuid.uuid4()),
        request_key=body.request_key,
        delivery_date=body.delivery_date,
        requested_by=user.id,
    )
    db.add(job)
    enqueue(db, "planning.job_requested", job.id, {"job_id": job.id})
    db.commit()
    return TypeAdapter(JobResult).validate_python({"job_id": job.id, "status": job.status})


def get_job(job_id: str, db: Session, user: Principal, _: None = None) -> JobStatus:
    job = db.get(PlanningJob, job_id)
    if not job:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Job not found."})
    return TypeAdapter(JobStatus).validate_python(
        {
            "job_id": job.id,
            "status": job.status,
            "plan_id": job.plan_id,
            "error_code": job.error_code,
        }
    )


def cancel_job(job_id: str, db: Session, user: Principal, _: None = None) -> JobResult:
    job = db.get(PlanningJob, job_id)
    if not job:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Job not found."})
    lock_run(db, job.delivery_date)
    db.refresh(job)
    if job.status != "pending":
        raise HTTPException(
            409, detail={"code": "JOB_STARTED", "message": "Only pending jobs may be cancelled."}
        )
    job.status = "cancelled"
    db.commit()
    return TypeAdapter(JobResult).validate_python({"job_id": job.id, "status": job.status})

from typing import Annotated
from waypoint_security import Actor
from pydantic import TypeAdapter
from waypoint_contracts.runtime import JobResult, JobStatus
from fastapi import APIRouter
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.jobs import JobRequest
from app.application.use_cases import jobs as use_cases

router = APIRouter(prefix="/planning/jobs", tags=["planning jobs"])
_DISPATCHER = require_role("DISPATCHER")


@router.post("", status_code=202, response_model=JobResult, response_model_exclude_unset=True)
def create_job(
    body: JobRequest, db: DbDep, user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> JobResult:
    return TypeAdapter(JobResult).validate_python(
        use_cases.create_job(body=body, db=db, user=user, _=None)
    )


@router.get("/{job_id}", response_model=JobStatus, response_model_exclude_unset=True)
def get_job(
    job_id: str, db: DbDep, user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> JobStatus:
    return TypeAdapter(JobStatus).validate_python(
        use_cases.get_job(job_id=job_id, db=db, user=user, _=None)
    )


@router.post("/{job_id}/cancel", response_model=JobResult, response_model_exclude_unset=True)
def cancel_job(
    job_id: str, db: DbDep, user: CurrentUser, _: Annotated[Actor, _DISPATCHER]
) -> JobResult:
    return TypeAdapter(JobResult).validate_python(
        use_cases.cancel_job(job_id=job_id, db=db, user=user, _=None)
    )

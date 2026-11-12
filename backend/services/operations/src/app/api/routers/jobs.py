from fastapi import APIRouter
from app.api.deps import CurrentUser, DbDep, require_role
from waypoint_contracts.jobs import JobRequest
from app.application.use_cases import jobs as use_cases

router = APIRouter(prefix="/planning/jobs", tags=["planning jobs"])
_DISPATCHER = require_role("DISPATCHER")


@router.post("", status_code=202)
def create_job(body: JobRequest, db: DbDep, user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.create_job(body=body, db=db, user=user, _=_)


@router.get("/{job_id}")
def get_job(job_id: str, db: DbDep, user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.get_job(job_id=job_id, db=db, user=user, _=_)


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: DbDep, user: CurrentUser, _: None = _DISPATCHER):
    return use_cases.cancel_job(job_id=job_id, db=db, user=user, _=_)

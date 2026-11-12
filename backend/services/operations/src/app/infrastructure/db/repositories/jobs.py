from dataclasses import asdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.jobs import Job
from app.infrastructure.messaging.models import PlanningJob


class SQLJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, identity: str, for_update: bool = False) -> Job | None:
        row = self.session.get(
            PlanningJob, identity, with_for_update=for_update, populate_existing=True
        )
        return self.record(row)

    def by_request(self, key: str) -> Job | None:
        return self.record(
            self.session.scalar(select(PlanningJob).where(PlanningJob.request_key == key))
        )

    def record(self, row: PlanningJob | None) -> Job | None:
        return (
            Job(**{name: getattr(row, name) for name in Job.__dataclass_fields__}) if row else None
        )

    def save(self, job: Job) -> None:
        row = self.session.get(PlanningJob, job.id)
        if row is None:
            self.session.add(PlanningJob(**asdict(job)))
        else:
            for key, value in asdict(job).items():
                setattr(row, key, value)

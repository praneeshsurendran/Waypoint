from dataclasses import asdict
from sqlalchemy import select
from app.domain.jobs import Job
from app.infrastructure.messaging.models import PlanningJob


class SQLJobRepository:
    def __init__(self, session):
        self.session = session

    def get(self, identity, for_update=False):
        row = self.session.get(
            PlanningJob, identity, with_for_update=for_update, populate_existing=True
        )
        return self.record(row)

    def by_request(self, key):
        return self.record(
            self.session.scalar(select(PlanningJob).where(PlanningJob.request_key == key))
        )

    def record(self, row):
        return (
            Job(**{name: getattr(row, name) for name in Job.__dataclass_fields__}) if row else None
        )

    def save(self, job):
        row = self.session.get(PlanningJob, job.id)
        if row is None:
            self.session.add(PlanningJob(**asdict(job)))
        else:
            for key, value in asdict(job).items():
                setattr(row, key, value)

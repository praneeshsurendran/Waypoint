"""One local transaction contains business writes, job state and outbox/inbox effects."""

from app.infrastructure.db.repositories.jobs import SQLJobRepository
from app.application.interfaces.jobs import JobRepository


class OperationsUnitOfWork:
    def __init__(self, factory):
        self.factory = factory

    def __enter__(self):
        self.session = self.factory()
        self.transaction = self.session.begin()
        self.jobs: JobRepository = SQLJobRepository(self.session)
        return self

    def __exit__(self, kind, error, traceback):
        try:
            self.transaction.__exit__(kind, error, traceback)
        finally:
            self.session.close()

"""One local transaction contains business writes, job state and outbox/inbox effects."""

from types import TracebackType
from sqlalchemy.orm import Session, sessionmaker
from app.infrastructure.db.repositories.jobs import SQLJobRepository
from app.application.interfaces.jobs import JobRepository


class OperationsUnitOfWork:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def __enter__(self) -> "OperationsUnitOfWork":
        self.session = self.factory()
        self.transaction = self.session.begin()
        self.jobs: JobRepository = SQLJobRepository(self.session)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.transaction.__exit__(kind, error, traceback)
        finally:
            self.session.close()

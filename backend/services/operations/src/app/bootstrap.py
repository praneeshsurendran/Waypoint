"""Operations composition root: concrete adapters stay outside use-case/domain contracts."""

import os
from app.application.interfaces.storage import ProofStorage
from app.infrastructure.db.session import engine
from app.infrastructure.storage.proofs import storage
from waypoint_messaging import EventBridgePublisher, SQSQueue


def proof_storage() -> ProofStorage:
    return storage()


def event_publisher():
    return EventBridgePublisher()


def planning_queue():
    return SQSQueue(os.environ["PLANNING_QUEUE_URL"])


def shutdown():
    engine.dispose()

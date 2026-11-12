from app.infrastructure.db.session import SessionLocal
from app.infrastructure.messaging.outbox import publish_pending
from app.bootstrap import event_publisher, planning_queue
from waypoint_messaging.worker import publish_loop

if __name__ == "__main__":
    publisher = event_publisher()
    jobs = planning_queue()
    publish_loop(lambda: publish_pending(SessionLocal, publisher, jobs))

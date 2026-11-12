from waypoint_network.bootstrap import SessionLocal
from waypoint_network.infrastructure.messaging.outbox import publish_pending
from waypoint_messaging import EventBridgePublisher
from waypoint_messaging.worker import publish_loop


def main() -> None:
    publisher = EventBridgePublisher()
    publish_loop(lambda: publish_pending(SessionLocal, publisher))


if __name__ == "__main__":
    main()

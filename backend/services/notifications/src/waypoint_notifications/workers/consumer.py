import os
from waypoint_messaging import SQSQueue
from waypoint_messaging.worker import consume
from waypoint_notifications.application.services.events import handle

if __name__ == "__main__":
    consume(SQSQueue(os.environ["CONSUMER_QUEUE_URL"]), handle)

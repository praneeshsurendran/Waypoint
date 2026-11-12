import os
from app.infrastructure.messaging.consumer import handle
from waypoint_messaging import SQSQueue
from waypoint_messaging.worker import consume

if __name__ == "__main__":
    consume(SQSQueue(os.environ["CONSUMER_QUEUE_URL"]), handle)

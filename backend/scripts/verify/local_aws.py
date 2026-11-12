"""Smoke an already-running local emulator; refuse AWS cloud endpoints."""

import os
from urllib.parse import urlparse
from uuid import uuid4
from waypoint_contracts.events import EventEnvelope
from waypoint_messaging import EventBridgePublisher, aws_client, decode_message


def main():
    host = urlparse(os.environ.get("AWS_ENDPOINT_URL", "")).hostname
    if host not in (
        "localhost",
        "127.0.0.1",
        "localstack",
        "localhost.localstack.cloud",
    ):
        raise RuntimeError(
            "Explicit local emulator endpoint required; no AWS resources will be created"
        )
    sqs = aws_client("sqs")
    s3 = aws_client("s3")
    events = aws_client("events")
    bus = os.environ.get("EVENT_BUS_NAME", "waypoint")
    events.describe_event_bus(Name=bus)
    verify_fanout(sqs, events, bus)
    key = "smoke/" + str(uuid4())
    s3.put_object(
        Bucket=os.environ["POD_BUCKET"],
        Key=key,
        Body=b"synthetic-smoke",
        ServerSideEncryption="AES256",
    )
    assert (
        s3.get_object(Bucket=os.environ["POD_BUCKET"], Key=key)["Body"].read()
        == b"synthetic-smoke"
    )
    s3.delete_object(Bucket=os.environ["POD_BUCKET"], Key=key)
    verify_redrive(sqs)
    print(
        "Local EventBridge/SQS delivery, DLQ redrive/replay and private object roundtrip passed"
    )


def verify_fanout(sqs, events, bus):
    name = "smoke-" + uuid4().hex
    queue = sqs.create_queue(QueueName=name)["QueueUrl"]
    try:
        arn = sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]
        import json

        events.put_rule(
            Name=name, EventBusName=bus, EventPattern=json.dumps({"source": [name]})
        )
        result = events.put_targets(
            Rule=name, EventBusName=bus, Targets=[{"Id": name, "Arn": arn}]
        )
        assert result["FailedEntryCount"] == 0
        event = EventEnvelope(
            event_type="order.confirmed",
            source=name,
            aggregate_id=name,
            data={"order_id": 1},
        )
        EventBridgePublisher(events, bus).publish(event)
        for _ in range(10):
            result = sqs.receive_message(
                QueueUrl=queue, WaitTimeSeconds=2, MaxNumberOfMessages=10
            )
            for message in result.get("Messages", []):
                if decode_message(message["Body"]).event_id == event.event_id:
                    sqs.delete_message(
                        QueueUrl=queue, ReceiptHandle=message["ReceiptHandle"]
                    )
                    return
        raise RuntimeError("EventBridge-to-SQS fan-out was not observed")
    finally:
        events.remove_targets(Rule=name, EventBusName=bus, Ids=[name])
        events.delete_rule(Name=name, EventBusName=bus)
        sqs.delete_queue(QueueUrl=queue)


def verify_redrive(sqs):
    """Isolated, short-lived local queues; no application queue is purged or modified."""
    import json
    import time

    name = "smoke-" + uuid4().hex
    dead = sqs.create_queue(QueueName=name + "-dlq")["QueueUrl"]
    main = None
    try:
        arn = sqs.get_queue_attributes(QueueUrl=dead, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]
        main = sqs.create_queue(
            QueueName=name,
            Attributes={
                "VisibilityTimeout": "1",
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": arn, "maxReceiveCount": "2"}
                ),
            },
        )["QueueUrl"]
        body = json.dumps({"synthetic_poison": name})
        sqs.send_message(QueueUrl=main, MessageBody=body)
        for _ in range(8):
            sqs.receive_message(QueueUrl=main, WaitTimeSeconds=1, VisibilityTimeout=0)
            result = sqs.receive_message(QueueUrl=dead, WaitTimeSeconds=1)
            if result.get("Messages"):
                message = result["Messages"][0]
                assert message["Body"] == body
                sqs.send_message(QueueUrl=main, MessageBody=message["Body"])
                sqs.delete_message(
                    QueueUrl=dead, ReceiptHandle=message["ReceiptHandle"]
                )
                replay = sqs.receive_message(QueueUrl=main, WaitTimeSeconds=2)[
                    "Messages"
                ][0]
                assert replay["Body"] == body
                sqs.delete_message(QueueUrl=main, ReceiptHandle=replay["ReceiptHandle"])
                return
            time.sleep(0.1)
        raise RuntimeError("Local queue redrive was not observed")
    finally:
        if main:
            sqs.delete_queue(QueueUrl=main)
        sqs.delete_queue(QueueUrl=dead)


if __name__ == "__main__":
    main()

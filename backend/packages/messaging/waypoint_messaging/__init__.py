"""AWS transport adapters, independent of service persistence and business logic."""

from __future__ import annotations


import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, overload

if TYPE_CHECKING:
    from mypy_boto3_events import EventBridgeClient
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_s3 import S3Client

import boto3
from botocore.config import Config
from waypoint_contracts.events import EventEnvelope


class EventPublisher(Protocol):
    def publish(self, event: EventEnvelope) -> None: ...


class EventBridgePublisher:
    def __init__(
        self, client: EventBridgeClient | None = None, bus: str | None = None
    ) -> None:
        self.client = client or aws_client("events")
        self.bus = bus or os.environ["EVENT_BUS_NAME"]

    def publish(self, event: EventEnvelope) -> None:
        result = self.client.put_events(
            Entries=[
                {
                    "Source": event.source,
                    "DetailType": event.event_type,
                    "Detail": event.model_dump_json(),
                    "EventBusName": self.bus,
                }
            ]
        )
        if result.get("FailedEntryCount", 0):
            raise RuntimeError("EventBridge rejected event")


@overload
def aws_client(service: Literal["events"]) -> EventBridgeClient: ...
@overload
def aws_client(service: Literal["sqs"]) -> SQSClient: ...
@overload
def aws_client(service: Literal["s3"]) -> S3Client: ...
def aws_client(
    service: Literal["events", "sqs", "s3"],
) -> EventBridgeClient | SQSClient | S3Client:
    # An explicit endpoint is for local emulation; production uses task-role credentials.
    return boto3.client(
        service,
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        config=Config(
            connect_timeout=2,
            read_timeout=25,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


@dataclass
class Message:
    receipt: str
    body: str
    attempts: int


class SQSQueue:
    def __init__(self, url: str, client: SQSClient | None = None) -> None:
        self.client = client or aws_client("sqs")
        self.url = url

    def receive(self) -> list[Message]:
        response = self.client.receive_message(
            QueueUrl=self.url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=120,
            AttributeNames=["ApproximateReceiveCount"],
        )
        return [
            Message(
                m["ReceiptHandle"],
                m["Body"],
                int(m.get("Attributes", {}).get("ApproximateReceiveCount", "1")),
            )
            for m in response.get("Messages", [])
        ]

    def acknowledge(self, message: Message) -> None:
        self.client.delete_message(QueueUrl=self.url, ReceiptHandle=message.receipt)

    def extend(self, message: Message, seconds: int = 120) -> None:
        self.client.change_message_visibility(
            QueueUrl=self.url, ReceiptHandle=message.receipt, VisibilityTimeout=seconds
        )

    def retry(self, message: Message) -> None:
        self.extend(message, min(900, 2 ** min(message.attempts, 9)))

    def send(self, event: EventEnvelope) -> None:
        self.client.send_message(QueueUrl=self.url, MessageBody=event.model_dump_json())


def decode_message(body: str) -> EventEnvelope:
    payload = json.loads(body)
    # EventBridge -> SQS wraps the versioned application envelope under detail.
    return EventEnvelope.model_validate(payload.get("detail", payload))


class MessageQueue(Protocol):
    def receive(self) -> list[Message]: ...
    def acknowledge(self, message: Message) -> None: ...
    def extend(self, message: Message, seconds: int = 120) -> None: ...
    def retry(self, message: Message) -> None: ...

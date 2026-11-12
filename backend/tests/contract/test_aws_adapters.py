"""Validate SDK request/response contracts locally; no AWS endpoint is contacted."""

import boto3
from botocore.stub import Stubber
from waypoint_contracts.events import EventEnvelope
from waypoint_messaging import EventBridgePublisher, SQSQueue
from app.infrastructure.storage.proofs import S3ProofStorage


def client(service):
    return boto3.client(
        service,
        region_name="ap-south-1",
        endpoint_url="http://127.0.0.1:4566",
        aws_access_key_id="local-test",
        aws_secret_access_key="local-test",
    )


def test_eventbridge_request_keeps_typed_envelope_and_bus():
    api = client("events")
    event = EventEnvelope(
        event_type="order.confirmed",
        source="operations",
        aggregate_id="1",
        data={"order_id": 1},
    )
    with Stubber(api) as stub:
        stub.add_response(
            "put_events",
            {"FailedEntryCount": 0, "Entries": [{"EventId": str(event.event_id)}]},
            {
                "Entries": [
                    {
                        "Source": "operations",
                        "DetailType": "order.confirmed",
                        "Detail": event.model_dump_json(),
                        "EventBusName": "test-bus",
                    }
                ]
            },
        )
        EventBridgePublisher(api, "test-bus").publish(event)
        stub.assert_no_pending_responses()


def test_queue_acknowledgement_and_visibility_contract():
    api = client("sqs")
    url = "http://127.0.0.1:4566/000000000000/test"
    queue = SQSQueue(url, api)
    with Stubber(api) as stub:
        stub.add_response(
            "receive_message",
            {
                "Messages": [
                    {
                        "MessageId": "1",
                        "ReceiptHandle": "receipt",
                        "Body": "{}",
                        "Attributes": {"ApproximateReceiveCount": "2"},
                    }
                ]
            },
            {
                "QueueUrl": url,
                "MaxNumberOfMessages": 1,
                "WaitTimeSeconds": 20,
                "VisibilityTimeout": 120,
                "AttributeNames": ["ApproximateReceiveCount"],
            },
        )
        stub.add_response(
            "change_message_visibility",
            {},
            {"QueueUrl": url, "ReceiptHandle": "receipt", "VisibilityTimeout": 120},
        )
        stub.add_response(
            "delete_message", {}, {"QueueUrl": url, "ReceiptHandle": "receipt"}
        )
        message = queue.receive()[0]
        assert message.attempts == 2
        queue.extend(message)
        queue.acknowledge(message)
        stub.assert_no_pending_responses()


def test_private_s3_upload_prevents_key_overwrite(monkeypatch):
    monkeypatch.setenv("POD_BUCKET", "private-test")
    api = client("s3")
    storage = S3ProofStorage(api)
    with Stubber(api) as stub:
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "private-test",
                "Key": "proofs/object.jpg",
                "Body": b"photo",
                "ContentType": "image/jpeg",
                "ServerSideEncryption": "AES256",
                "IfNoneMatch": "*",
            },
        )
        storage.put("object.jpg", b"photo", "image/jpeg")
        stub.assert_no_pending_responses()

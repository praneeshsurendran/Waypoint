import json
import pytest
from pydantic import ValidationError
from waypoint_contracts.events import EventEnvelope
from waypoint_messaging import EventBridgePublisher, decode_message


def test_versioned_envelope_roundtrip_and_eventbridge_wrapper():
    event = EventEnvelope(
        event_type="order.confirmed",
        source="operations",
        aggregate_id="1",
        data={"order_id": 1},
    )
    assert (
        decode_message(json.dumps({"detail": event.model_dump(mode="json")})) == event
    )
    assert event.occurred_at.utcoffset().total_seconds() == 0


def test_unsupported_versions_and_naive_times_are_rejected():
    for patch in [
        {"version": 2},
        {"event_type": "unknown"},
        {"occurred_at": "2024-01-01T12:00:00"},
    ]:
        with pytest.raises(ValidationError):
            EventEnvelope.model_validate(
                {
                    "event_type": "order.confirmed",
                    "source": "operations",
                    "aggregate_id": "1",
                    "data": {},
                    **patch,
                }
            )


def test_eventbridge_partial_failure_is_not_marked_published():
    class RejectingClient:
        def put_events(self, **kwargs):
            return {"FailedEntryCount": 1}

    publisher = EventBridgePublisher(RejectingClient(), "local-test")
    with pytest.raises(RuntimeError):
        publisher.publish(
            EventEnvelope(
                event_type="order.confirmed",
                source="operations",
                aggregate_id="1",
                data={"order_id": 1},
            )
        )

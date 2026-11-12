from waypoint_contracts.events import EventEnvelope
from waypoint_notifications.application.services.events import handle


def test_notification_reads_are_outlet_scoped(service_clients):
    login = service_clients["identity"].post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "test-role-password"},
    )
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    event = EventEnvelope(
        event_type="order.deferred",
        source="operations",
        aggregate_id="9",
        data={"order_id": 9, "outlet_id": "SYN002", "reason_code": "CAPACITY"},
    )
    handle(event)
    client = service_clients["notifications"]
    assert client.get("/api/v1/notifications", headers=headers).json() == []
    assert (
        client.post(
            f"/api/v1/notifications/{event.event_id}/read", headers=headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/notifications/push-subscriptions", headers=headers, json={}
        ).status_code
        == 501
    )

"""Contact editing and assignment requests preserve identity ownership and durable audit."""

from sqlalchemy import select


def test_own_contact_and_account_request_are_scoped_and_durable(
    service_clients, contexts
):
    from waypoint_identity.infrastructure.db.audit import AuditLog
    from waypoint_identity.infrastructure.db.models import Outbox

    client = service_clients["identity"]
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "test-role-password"},
    )
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    before = client.get("/api/v1/auth/me", headers=headers).json()
    response = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Manager",
            "phone": "+94771111222",
            "email": "manager.updated@example.test",
        },
    )
    assert response.status_code == 200, response.text
    after = client.get("/api/v1/auth/me", headers=headers).json()
    assert after["full_name"] == "Updated Manager"
    assert after["phone"] == "+94771111222"
    assert (
        after["outlet_id"] == before["outlet_id"] and after["role"] == "STORE_MANAGER"
    )
    assert (
        client.post(
            "/api/v1/auth/account-change-requests",
            json={"detail": "Move outlet assignment"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/account-change-requests",
            headers=headers,
            json={"detail": "    "},
        ).status_code
        == 422
    )
    result = client.post(
        "/api/v1/auth/account-change-requests",
        headers=headers,
        json={"detail": "  Please review my outlet assignment  "},
    )
    assert result.status_code == 201, result.text
    with contexts["identity"]() as db:
        audit = db.scalar(
            select(AuditLog).where(AuditLog.action == "ACCOUNT_CHANGE_REQUEST")
        )
        assert audit.actor_user_id == before["id"]
        assert audit.after_json == {
            "detail": "Please review my outlet assignment",
            "status": "pending",
        }
        events = [row.envelope for row in db.scalars(select(Outbox))]
        assert any(
            event["event_type"] == "audit.recorded"
            and event["data"]["action"] == "ACCOUNT_CHANGE_REQUEST"
            for event in events
        )
    final = client.get("/api/v1/auth/me", headers=headers).json()
    assert final["outlet_id"] == before["outlet_id"] and final["role"] == before["role"]

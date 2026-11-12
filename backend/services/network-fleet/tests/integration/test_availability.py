from sqlalchemy import select


def test_availability_is_authorized_durable_and_evented(service_clients, contexts):
    clients = service_clients

    def auth(name):
        response = clients["identity"].post(
            "/api/v1/auth/login",
            json={"username": name, "password": "test-role-password"},
        )
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    path = "/api/v1/reference/vehicles/SYNV001/availability"
    assert (
        clients["network"]
        .patch(path, headers=auth("driver"), json={"status": "in_workshop"})
        .status_code
        == 403
    )
    result = clients["network"].patch(
        path, headers=auth("admin"), json={"status": "in_workshop"}
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "in_workshop"
    from waypoint_network.infrastructure.db.models import Outbox

    with contexts["network"]() as db:
        rows = db.scalars(select(Outbox)).all()
        assert any(
            r.envelope["data"].get("record", {}).get("status") == "in_workshop"
            for r in rows
        )

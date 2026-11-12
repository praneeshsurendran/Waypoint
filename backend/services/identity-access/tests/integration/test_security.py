from sqlalchemy import select


def auth(clients, name):
    result = clients["identity"].post(
        "/api/v1/auth/login", json={"username": name, "password": "test-role-password"}
    )
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_password_reset_revokes_existing_tokens(service_clients):
    clients = service_clients
    admin = auth(clients, "admin")
    driver = auth(clients, "driver")
    users = clients["identity"].get("/api/v1/admin/users", headers=admin).json()
    user = next(u for u in users if u["username"] == "driver")
    result = clients["identity"].post(
        f'/api/v1/admin/users/{user["id"]}/reset-password',
        headers=admin,
        json={"password": "new-role-password"},
    )
    assert result.status_code == 204, result.text
    assert clients["identity"].get("/api/v1/auth/me", headers=driver).status_code == 401
    assert (
        clients["network"].get("/api/v1/reference/vehicles", headers=driver).status_code
        == 401
    )


def test_role_headers_and_malformed_jwt_cannot_authorize(service_clients):
    for client in service_clients.values():
        response = client.get(
            "/api/v1/notifications"
            if client is service_clients["notifications"]
            else "/api/v1/admin/users",
            headers={"X-Role": "ADMIN", "X-User-Id": "1"},
        )
        assert response.status_code in (401, 404)
    assert (
        service_clients["identity"]
        .get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        .status_code
        == 401
    )
    manager = auth(service_clients, "manager")
    assert (
        service_clients["identity"]
        .get("/api/v1/admin/users", headers=manager)
        .status_code
        == 403
    )


def test_owner_events_never_contain_password_hashes(contexts):
    from waypoint_identity.infrastructure.db.accounts import User
    from waypoint_identity.infrastructure.db.models import Outbox
    from waypoint_identity.core.security import hash_password

    with contexts["identity"].begin() as db:
        db.add(
            User(
                username="one",
                password_hash=hash_password("password"),
                full_name="One",
                role="DISPATCHER",
                is_active=True,
            )
        )
    with contexts["identity"]() as db:
        event = db.scalars(select(Outbox)).one().envelope
        assert event["event_type"] == "identity.user_changed"
        assert "password_hash" not in event["data"]["record"]


def test_invalid_issuer_audience_expiry_and_signature_are_rejected(service_clients):
    import datetime as dt
    import jwt
    from waypoint_identity.core.settings import get_settings

    clients = service_clients
    headers = auth(clients, "driver")
    token = headers["Authorization"].removeprefix("Bearer ")
    settings = get_settings()
    payload = jwt.decode(token, options={"verify_signature": False})
    variants = [
        ({**payload, "iss": "another-issuer"}, settings.jwt_secret),
        ({**payload, "aud": "another-api"}, settings.jwt_secret),
        (
            {
                **payload,
                "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1),
            },
            settings.jwt_secret,
        ),
        (payload, "forged-key-at-least-thirty-two-characters"),
        (
            {key: value for key, value in payload.items() if key != "iss"},
            settings.jwt_secret,
        ),
    ]
    for claims, key in variants:
        forged = jwt.encode(claims, key, algorithm=settings.jwt_algorithm)
        assert (
            clients["identity"]
            .get("/api/v1/auth/me", headers={"Authorization": "Bearer " + forged})
            .status_code
            == 401
        )


def test_invalid_password_inputs_return_validation_error_without_echo(service_clients):
    clients = service_clients
    admin = auth(clients, "admin")
    users = clients["identity"].get("/api/v1/admin/users", headers=admin).json()
    user = next(user for user in users if user["username"] == "driver")
    for password in ("zx!", "密" * 30, "x" * 73):
        response = clients["identity"].post(
            f'/api/v1/admin/users/{user["id"]}/reset-password',
            headers=admin,
            json={"password": password},
        )
        assert response.status_code == 422
        assert password not in response.text
        assert '"input"' not in response.text
    assert (
        clients["identity"]
        .get("/api/v1/auth/me", headers=auth(clients, "driver"))
        .status_code
        == 200
    )

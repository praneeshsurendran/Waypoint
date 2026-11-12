"""Four-role HTTP smoke for an already running synthetic local stack; no cloud provisioning."""

import datetime as dt
import json
import os
import time
from urllib.parse import urlparse
from uuid import uuid4
import httpx


def main():
    base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    if urlparse(base).hostname not in ("localhost", "127.0.0.1", "ingress"):
        raise RuntimeError("This write smoke is restricted to a synthetic local stack")
    password = os.environ["DEMO_PASSWORD"]
    with httpx.Client(base_url=base, timeout=120) as client:

        def request(method, path, headers=None, expected=200, **kwargs):
            result = client.request(method, path, headers=headers, **kwargs)
            if result.status_code != expected:
                raise AssertionError(
                    f"{method} {path}: {result.status_code} {result.text}"
                )
            return result.json() if result.content else None

        headers = {}
        for name in ("manager", "dispatcher", "loader", "driver", "admin"):
            token = request(
                "POST",
                "/api/v1/auth/login",
                json={"username": name, "password": password},
            )["access_token"]
            headers[name] = {"Authorization": "Bearer " + token}
        request("GET", "/health/ready")
        # Use an unseeded future operating day, retaining all existing synthetic example orders.
        intake = request("GET", "/api/v1/orders/intake-status", headers["manager"])
        day = dt.date.fromisoformat(intake["next_delivery_date"]) + dt.timedelta(days=1)
        occupied = {
            row["delivery_date"]
            for row in request("GET", "/api/v1/orders", headers["dispatcher"])
        }
        while day.weekday() == 6 or str(day) in occupied:
            day += dt.timedelta(days=1)
        order = request(
            "POST",
            "/api/v1/orders",
            headers["manager"],
            expected=201,
            json={
                "outlet_id": "SYN001",
                "temperature_class": "CHILLED",
                "delivery_date": str(day),
                "cases": 5,
            },
        )
        request("POST", "/api/v1/orders/close?date=" + str(day), headers["dispatcher"])
        queued_at = time.perf_counter()
        job = request(
            "POST",
            "/api/v1/planning/jobs",
            headers["dispatcher"],
            expected=202,
            json={"delivery_date": str(day), "request_key": str(uuid4())},
        )
        for _ in range(60):
            status = request(
                "GET", "/api/v1/planning/jobs/" + job["job_id"], headers["dispatcher"]
            )
            if status["status"] in ("succeeded", "failed"):
                break
            time.sleep(1)
        assert status["status"] == "succeeded", status
        queue_completion_seconds = round(time.perf_counter() - queued_at, 3)
        drafts = request(
            "GET",
            "/api/v1/plans?date=" + str(day) + "&status=DRAFT",
            headers["dispatcher"],
        )
        plan = drafts[0]
        request("POST", f'/api/v1/plans/{plan["id"]}/publish', headers["dispatcher"])
        trip = next(
            t
            for t in plan["trips"]
            if any(s["outlet_id"] == "SYN001" for s in t["stops"])
        )
        stop = next(s for s in trip["stops"] if s["outlet_id"] == "SYN001")
        users = request("GET", "/api/v1/admin/users", headers["admin"])
        driver = next(u for u in users if u["username"] == "driver")
        request(
            "PATCH",
            f'/api/v1/admin/users/{driver["id"]}',
            headers["admin"],
            json={"vehicle_id": trip["vehicle_id"]},
        )
        load = f'/api/v1/loading/trips/{trip["id"]}'
        request(
            "POST",
            load + "/flags",
            headers["loader"],
            expected=201,
            json={
                "status": "MISSING",
                "order_id": order["id"],
                "note": "Synthetic replacement needed",
            },
        )
        request("POST", load + "/release", headers["loader"], expected=409)
        request(
            "POST",
            load + "/flags",
            headers["loader"],
            expected=201,
            json={
                "status": "OK",
                "order_id": order["id"],
                "note": "Synthetic replacement loaded",
            },
        )
        request("POST", load + "/release", headers["loader"])
        departed = request(
            "POST",
            "/api/v1/driver/sync",
            headers["driver"],
            json={
                "events": [
                    {
                        "client_op_id": str(uuid4()),
                        "stop_id": stop["id"],
                        "outcome": "STARTED",
                    }
                ]
            },
        )
        assert departed[0]["accepted"]
        current = request("GET", "/api/v1/driver/trips/current", headers["driver"])
        assert (
            next(row for row in current["stops"] if row["id"] == stop["id"])["status"]
            == "PENDING"
        )
        request("POST", "/api/v1/driver/trips/start", headers["driver"])
        request(
            "POST",
            f'/api/v1/driver/stops/{stop["id"]}/events',
            headers["driver"],
            expected=201,
            json={
                "client_op_id": str(uuid4()),
                "stop_id": stop["id"],
                "outcome": "ARRIVED",
            },
        )
        upload = request(
            "POST",
            "/api/v1/driver/uploads",
            headers["driver"],
            files={
                "file": (
                    "proof.png",
                    b"\x89PNG\r\n\x1a\nsynthetic-validation",
                    "image/png",
                )
            },
            data={"stop_id": str(stop["id"])},
        )
        assert client.get(upload["path"]).status_code == 401
        assert client.get(upload["path"], headers=headers["manager"]).status_code == 200
        event = {
            "client_op_id": str(uuid4()),
            "stop_id": stop["id"],
            "outcome": "DELIVERED",
            "device_id": str(uuid4()),
            "device_sequence": 1,
            "pod_photo_path": upload["path"],
            "receiver_name": "Synthetic receiver",
        }
        results = request(
            "POST",
            "/api/v1/driver/sync",
            headers["driver"],
            json={"events": [event, event]},
        )
        assert (
            all(row["accepted"] for row in results)
            and results[1]["message"] == "duplicate"
        ), results
        history = request(
            "GET",
            "/api/v1/driver/sync",
            headers["driver"],
            params={"device_id": event["device_id"]},
        )
        assert history["server_cursor"] == 1 and history["next_cursor"] == 1
        assert history["events"][0]["client_op_id"] == event["client_op_id"]
        timeline = request("GET", "/api/v1/driver/history", headers["driver"])
        assert {"started", "arrived", "accepted"} <= {row["kind"] for row in timeline}
        for _ in range(2):
            request(
                "POST",
                f'/api/v1/orders/{order["id"]}/receipt',
                headers["manager"],
                expected=201,
                json={"outcome": "FULL"},
            )
        for _ in range(30):
            notices = request("GET", "/api/v1/notifications", headers["manager"])
            if any(row["type"] == "proof_of_delivery.recorded" for row in notices):
                break
            time.sleep(1)
        assert any(
            row["type"] == "proof_of_delivery.recorded" for row in notices
        ), notices
        print(
            json.dumps(
                {
                    "four_role_http_workflow": "passed",
                    "async_job": "succeeded",
                    "queue_completion_seconds": queue_completion_seconds,
                    "duplicate_replay": "deduplicated",
                    "private_evidence": "authorized",
                    "notifications": len(notices),
                    "order_id": order["id"],
                    "plan_id": plan["id"],
                }
            )
        )


if __name__ == "__main__":
    main()

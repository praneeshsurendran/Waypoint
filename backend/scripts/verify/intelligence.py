"""Read-only inference acceptance checks against an already running local stack."""

import csv
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import httpx


def main():
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    if urlparse(base).hostname not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Local acceptance stack required")
    with httpx.Client(base_url=base, timeout=60) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "dispatcher", "password": os.environ["DEMO_PASSWORD"]},
        )
        login.raise_for_status()
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        root = Path(__file__).resolve().parents[2] / "private/intelligence/data"
        with (root / "Test Data/task1_test_inputs.csv").open() as file:
            identities = [
                row["delivery_id"] for _, row in zip(range(3), csv.DictReader(file))
            ]
        samples = client.post(
            "/api/v1/intelligence/predictions",
            headers=headers,
            json={"delivery_ids": identities},
        )
        samples.raise_for_status()
        assert [
            row["delivery_id"] for row in samples.json()["predictions"]
        ] == identities
        forecast = client.get("/api/v1/analytics/demand-forecast", headers=headers)
        forecast.raise_for_status()
        assert len(forecast.json()["forecast"]) == 60
        assert "Saved datathon Ridge" in forecast.json()["method"]
        planned = client.get(
            "/api/v1/analytics/plan-predictions",
            headers=headers,
            params={"plan_id": int(os.getenv("VERIFY_PLAN_ID", "1"))},
        )
        planned.raise_for_status()
        assert planned.json()["predictions"]
        assert client.get("/api/v1/intelligence/forecast").status_code == 401
        print(
            json.dumps(
                {
                    "model_version": samples.json()["model_version"],
                    "known_id_predictions": len(identities),
                    "forecast_rows": len(forecast.json()["forecast"]),
                    "live_plan_predictions": len(planned.json()["predictions"]),
                    "unauthenticated": "denied",
                }
            )
        )


if __name__ == "__main__":
    main()

"""Inference boundaries, depot isolation and independently checked artifact outputs."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from waypoint_security import Principal, verified_principal
from waypoint_contracts.intelligence import PlannedDelivery, ForecastRow
from waypoint_intelligence import engine
from waypoint_intelligence.main import create_app


def principal(role="DISPATCHER", depot=None):
    return Principal(
        id=1,
        username="planner",
        full_name="Planner",
        role=role,
        is_active=True,
        depot_id=depot,
    )


def test_verified_forecast_preserves_keys_and_physical_constraints():
    result = engine.demand_forecast()
    template = engine.read("Test Data", "task2a_test_inputs.csv")
    assert [r.row_id for r in result.rows] == template.row_id.tolist()
    assert len(result.rows) == 60
    assert len({(r.iso_year, r.iso_week) for r in result.rows}) == 10
    assert all(0 <= row.chilled_m3 <= row.total_m3 for row in result.rows)
    assert all(row.chilled_m3 == 0 for row in result.rows if row.brand != "Fresh")
    assert 0 < result.backtest["wape_percent"] < 100


def test_prediction_ids_are_unique_and_known():
    with pytest.raises(ValueError):
        engine.predict_ids(["unknown"])
    identity = str(engine.test_frame().delivery_id.iloc[0])
    with pytest.raises(ValueError):
        engine.predict_ids([identity, identity])
    prediction = engine.predict_ids([identity]).predictions[0]
    assert prediction.delivery_id == identity
    assert prediction.pred_service_min >= 0
    assert 0 <= prediction.pred_late_prob <= 1


def test_live_features_match_dataset_features_without_outcomes():
    frame = engine.test_frame().iloc[0]
    # A live plan supplies only planned inputs; neither arrival outcomes nor labels are accepted.
    data = engine.test_frame()
    route = data.loc[data.route_id == frame.route_id].sort_values("seq_in_route")
    rows = [
        PlannedDelivery.model_validate(
            {key: record[key] for key in PlannedDelivery.model_fields}
        )
        for _, record in route.iterrows()
    ]
    actual = engine.predict_planned(rows).predictions
    expected = engine.predict_ids([row.delivery_id for row in rows]).predictions
    for left, right in zip(actual, expected, strict=True):
        assert left.delivery_id == right.delivery_id
        assert left.pred_service_min == pytest.approx(right.pred_service_min)
        assert left.pred_late_prob == pytest.approx(right.pred_late_prob)
    row = rows[0]
    with pytest.raises(ValidationError):
        PlannedDelivery.model_validate({**row.model_dump(), "arrival_time": "07:00"})


def test_model_integrity_checked_before_deserialization(tmp_path, monkeypatch):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/manifest.json").write_text(
        '{"sha256":{"service.joblib":"wrong"}}'
    )
    (tmp_path / "artifacts/service.joblib").write_bytes(b"untrusted bytes")
    engine.bundle.cache_clear()
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    with pytest.raises(engine.ModelUnavailable, match="integrity"):
        engine.bundle("service")
    engine.bundle.cache_clear()


def test_http_auth_role_and_depot_scope():
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/intelligence/forecast").status_code == 401
        app.dependency_overrides[verified_principal] = lambda: principal("DRIVER")
        assert client.get("/api/v1/intelligence/forecast").status_code == 403
        app.dependency_overrides[verified_principal] = lambda: principal(depot="Kandy")
        response = client.get("/api/v1/intelligence/forecast")
        assert response.status_code == 200
        assert {row["depot"] for row in response.json()["rows"]} == {"Kandy"}
        other = engine.test_frame().query('depot == "Peliyagoda"').delivery_id.iloc[0]
        assert (
            client.post(
                "/api/v1/intelligence/predictions", json={"delivery_ids": [other]}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/intelligence/predictions", json={"delivery_ids": []}
            ).status_code
            == 422
        )
    app.dependency_overrides.clear()


def test_forecast_rejects_nonfinite_and_invalid_chilled():
    values = dict(
        row_id="x",
        depot="Kandy",
        brand="Style",
        iso_year=2026,
        iso_week=1,
        total_m3=10,
        chilled_m3=1,
    )
    with pytest.raises(ValidationError):
        ForecastRow(**values)
    with pytest.raises(ValidationError):
        ForecastRow(**{**values, "chilled_m3": 0, "total_m3": float("nan")})

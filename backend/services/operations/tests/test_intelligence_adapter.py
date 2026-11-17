"""Inference failures never produce plausible fake predictions or expose upstream internals."""

from types import SimpleNamespace
import httpx
import pytest
from fastapi import HTTPException
from app.infrastructure import intelligence


@pytest.mark.parametrize(
    "status,body",
    [(503, {"detail": "private /model/path"}), (200, {"rows": []}), (200, {"bad": "contract"})],
)
def test_unavailable_or_invalid_forecast_is_a_safe_503(monkeypatch, status, body):
    monkeypatch.setattr(
        intelligence, "get_settings", lambda: SimpleNamespace(intelligence_url="http://models")
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    ) as client:
        monkeypatch.setattr(intelligence, "client", lambda: client)
        with pytest.raises(HTTPException) as error:
            intelligence.forecast("Bearer verified-token")
    assert error.value.status_code == 503
    assert "/model/path" not in str(error.value.detail)


def test_missing_identity_is_denied_before_inference(monkeypatch):
    monkeypatch.setattr(
        intelligence, "get_settings", lambda: SimpleNamespace(intelligence_url="http://models")
    )
    with pytest.raises(HTTPException) as error:
        intelligence.forecast(None)
    assert error.value.status_code == 401

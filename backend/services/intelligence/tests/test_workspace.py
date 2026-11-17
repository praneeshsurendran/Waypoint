"""Workspace migration preserves configured deployments and isolates private artifacts."""

from pathlib import Path
import runpy
import pytest

PATHS = Path(__file__).resolve().parents[1] / "src/waypoint_intelligence/paths.py"
RUNTIME = Path(__file__).resolve().parents[3] / "intelligence/runtime.py"


@pytest.mark.parametrize("script", [PATHS, RUNTIME])
def test_new_workspace_takes_precedence_and_legacy_variable_still_works(
    script, monkeypatch, tmp_path
):
    legacy = tmp_path / "legacy"
    current = tmp_path / "current"
    monkeypatch.delenv("WAYPOINT_INTELLIGENCE_WORKSPACE", raising=False)
    monkeypatch.setenv("WAYPOINT_DATATHON_WORKSPACE", str(legacy))
    assert runpy.run_path(str(script))["ROOT"] == legacy.resolve()
    monkeypatch.setenv("WAYPOINT_INTELLIGENCE_WORKSPACE", str(current))
    assert runpy.run_path(str(script))["ROOT"] == current.resolve()


def test_default_inference_workspace_is_backend_owned(monkeypatch):
    monkeypatch.delenv("WAYPOINT_INTELLIGENCE_WORKSPACE", raising=False)
    monkeypatch.delenv("WAYPOINT_DATATHON_WORKSPACE", raising=False)
    expected = PATHS.parents[4] / "private/intelligence"
    assert runpy.run_path(str(PATHS))["ROOT"] == expected.resolve()

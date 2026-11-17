from pathlib import Path
import os

_backend_root = Path(__file__).resolve().parents[4]
_default_workspace = _backend_root / "private" / "intelligence"
_legacy_workspace = _backend_root / "private" / "datathon"
if not _default_workspace.exists() and _legacy_workspace.exists():
    _default_workspace = _legacy_workspace
ROOT = (
    Path(
        os.getenv("WAYPOINT_INTELLIGENCE_WORKSPACE")
        or os.getenv("WAYPOINT_DATATHON_WORKSPACE")
        or _default_workspace
    )
    .expanduser()
    .resolve()
)
DATA_ROOT = ROOT / "data"

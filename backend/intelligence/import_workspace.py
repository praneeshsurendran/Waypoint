"""Copy authorized challenge assets into a private, backend-owned workspace (offline only)."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", type=Path, help="Directory containing data/ and notebook_outputs/"
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "private/intelligence",
    )
    args = parser.parse_args()
    source, target = args.source.resolve(), args.destination.resolve()
    if source == target or source in target.parents:
        parser.error("Use a separate destination outside the source directory")
    files = list((source / "data").rglob("*.csv"))
    model = source / "notebook_outputs/task2a/artifacts/forecast.joblib"
    if not files or not model.is_file():
        parser.error("Expected authorized CSV datasets and saved forecast artifact")
    manifest = {}
    assets = [
        (item, Path("data") / item.relative_to(source / "data")) for item in files
    ]
    assets.append((model, Path("artifacts/forecast.joblib")))
    selected = source / "notebook_outputs/task2b/submissions/submission_task2b.csv"
    if selected.is_file():
        assets.append((selected, Path("artifacts/submission_task2b.csv")))
    for item, relative in assets:
        destination = target / relative
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if (
            destination.exists()
            and hashlib.sha256(destination.read_bytes()).hexdigest() != digest
        ):
            raise FileExistsError(
                f"Refusing to overwrite a different private file: {relative}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        manifest[str(relative)] = digest
    (target / "source-assets.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Copied {len(files)} CSV files and the forecast artifact to {target}")


if __name__ == "__main__":
    main()

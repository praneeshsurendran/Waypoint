"""Backfill private metadata for existing local evidence, retaining URLs and originals."""

import argparse
import hashlib
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy import select
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models.delivery import DeliveryEvent
from app.infrastructure.db.models.loading import LoadCheck
from app.infrastructure.messaging.models import ProofObject
from app.infrastructure.storage.proofs import storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-upload-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        references = []
        for event in db.scalars(select(DeliveryEvent)):
            for path in [event.pod_photo_path, event.pod_signature_path, event.note]:
                if path and urlparse(path).path.startswith("/uploads/"):
                    references.append((path, event.recorded_by, event.stop_id))
        for check in db.scalars(select(LoadCheck)):
            if check.photo_path:
                references.append((check.photo_path, check.flagged_by, None))
        pending = {}
        for path, owner, stop in references:
            key = urlparse(path).path.removeprefix("/uploads/")
            if Path(key).name != key or not owner:
                raise RuntimeError(
                    "Ambiguous evidence ownership/key; review before applying"
                )
            source = args.legacy_upload_dir / key
            if not source.is_file():
                raise RuntimeError(
                    "Referenced proof file is missing; restore it before cutover"
                )
            content = source.read_bytes()
            mime = mimetypes.guess_type(key)[0]
            if mime not in ("image/jpeg", "image/png", "image/webp"):
                raise RuntimeError(
                    "Unsupported legacy proof type; manual review required"
                )
            digest = hashlib.sha256(content).hexdigest()
            prior = pending.get(key)
            if prior and prior[0:2] != (owner, stop):
                raise RuntimeError(
                    "Proof has conflicting owners; resolve before cutover"
                )
            pending[key] = (owner, stop, mime, content, digest)
        for key, (owner, stop, mime, content, digest) in pending.items():
            existing = db.get(ProofObject, key)
            if existing:
                if existing.sha256 != digest:
                    raise RuntimeError("Proof digest conflict")
                continue
            if args.apply:
                # Keep original files. Copy to private S3 only when that backend is selected.
                if os.environ.get("STORAGE_BACKEND") == "s3":
                    storage().put(key, content, mime)
                db.add(
                    ProofObject(
                        key=key,
                        owner_id=owner,
                        stop_id=stop,
                        content_type=mime,
                        size=len(content),
                        sha256=digest,
                    )
                )
        print({"proofs_verified": len(pending), "applied": args.apply})


if __name__ == "__main__":
    main()

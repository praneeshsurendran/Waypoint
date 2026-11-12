from pydantic import TypeAdapter
from waypoint_contracts.runtime import DownloadResult
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.api.deps import CurrentUser, DbDep
from app.application.use_cases.proofs import authorize_proof
from app.infrastructure.messaging.models import ProofObject
from app.infrastructure.storage.proofs import storage

router = APIRouter(tags=["evidence"])


@router.get(
    "/uploads/{key}",
    response_class=Response,
    responses={
        200: {
            "description": "Authorized private proof image",
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
def get_proof(key: str, db: DbDep, user: CurrentUser) -> Response:
    proof = db.get(ProofObject, key)
    if not proof:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Evidence not found."})
    authorize_proof(db, proof, user)
    try:
        content = storage().read(proof.key)
    except FileNotFoundError:
        raise HTTPException(
            404, detail={"code": "NOT_FOUND", "message": "Evidence not found."}
        ) from None
    return Response(
        content,
        media_type=proof.content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/api/v1/evidence/{key}/download-url",
    response_model=DownloadResult,
    response_model_exclude_unset=True,
)
def download_url(key: str, db: DbDep, user: CurrentUser) -> DownloadResult:
    from app.infrastructure.storage.proofs import S3ProofStorage

    proof = db.get(ProofObject, key)
    if not proof:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Evidence not found."})
    authorize_proof(db, proof, user)
    adapter = storage()
    if not isinstance(adapter, S3ProofStorage):
        return TypeAdapter(DownloadResult).validate_python(
            {"url": "/uploads/" + key, "expires_in": 0, "requires_authorization": True}
        )
    url = adapter.client.generate_presigned_url(
        "get_object", Params={"Bucket": adapter.bucket, "Key": "proofs/" + proof.key}, ExpiresIn=60
    )
    return TypeAdapter(DownloadResult).validate_python(
        {"url": url, "expires_in": 60, "requires_authorization": False}
    )

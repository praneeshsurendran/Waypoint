from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
import os
from pathlib import Path
from app.core.config import get_settings
from waypoint_messaging import aws_client


class LocalProofStorage:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        if not key or Path(key).name != key or key in (".", ".."):
            raise ValueError("invalid object key")
        return self.directory / key

    def put(self, key: str, content: bytes, content_type: str) -> None:
        with self.path(key).open("xb") as file:
            file.write(content)

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()


class S3ProofStorage:
    def __init__(self, client: "S3Client | None" = None) -> None:
        self.client = client or aws_client("s3")
        self.bucket = os.environ["POD_BUCKET"]

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key="proofs/" + key,
            Body=content,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            IfNoneMatch="*",
        )

    def read(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key="proofs/" + key)["Body"].read()


def storage() -> LocalProofStorage | S3ProofStorage:
    return (
        S3ProofStorage()
        if os.getenv("STORAGE_BACKEND") == "s3"
        else LocalProofStorage(get_settings().upload_dir)
    )

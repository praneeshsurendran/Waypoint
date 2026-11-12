import os
from pathlib import Path
from app.core.config import get_settings
from waypoint_messaging import aws_client


class LocalProofStorage:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        if not key or Path(key).name != key or key in (".", ".."):
            raise ValueError("invalid object key")
        return self.directory / key

    def put(self, key, content, content_type):
        with self.path(key).open("xb") as file:
            file.write(content)

    def read(self, key):
        return self.path(key).read_bytes()


class S3ProofStorage:
    def __init__(self, client=None):
        self.client = client or aws_client("s3")
        self.bucket = os.environ["POD_BUCKET"]

    def put(self, key, content, content_type):
        self.client.put_object(
            Bucket=self.bucket,
            Key="proofs/" + key,
            Body=content,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            IfNoneMatch="*",
        )

    def read(self, key):
        return self.client.get_object(Bucket=self.bucket, Key="proofs/" + key)["Body"].read()


def storage():
    return (
        S3ProofStorage()
        if os.getenv("STORAGE_BACKEND") == "s3"
        else LocalProofStorage(get_settings().upload_dir)
    )

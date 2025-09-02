from s3.main import s3, S3_BUCKET, PRESIGN_TTL
from botocore.exceptions import ClientError
import os
import tempfile
from uuid import uuid4

def ensure_bucket(bucket: str):
    """Create bucket if it doesn't exist (idempotent)."""
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = int(e.response.get("ResponseMetadata",
                   {}).get("HTTPStatusCode", 0))
        if code == 404:
            s3.create_bucket(Bucket=bucket)
        elif code == 301:
            # Wrong region or not found; try create
            s3.create_bucket(Bucket=bucket)
        else:
            raise


def upload_bytes_and_get_key(prefix: str, filename: str, data: bytes, content_type: str):
    ensure_bucket(S3_BUCKET)
    key = f"{prefix}/{uuid4().hex}/{filename}"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)
    return key

def presign_get_url(key: str, ttl: int = PRESIGN_TTL) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=ttl,
    )


def download_to_tmp(bucket: str, key: str) -> str:
    suffix = os.path.splitext(key)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    s3.download_file(bucket, key, tmp.name)
    return tmp.name

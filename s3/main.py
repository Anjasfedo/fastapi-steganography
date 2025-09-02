import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# ----- S3 / MinIO config -----
S3_ENDPOINT   = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET     = os.getenv("S3_BUCKET", "fastapi")
PRESIGN_TTL   = int(os.getenv("S3_PRESIGN_TTL", "3600"))

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

def ensure_bucket(bucket: str):
    """Create bucket if it doesn't exist (idempotent)."""
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = int(e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
        if code == 404:
            s3.create_bucket(Bucket=bucket)
        elif code == 301:
            # Wrong region or not found; try create
            s3.create_bucket(Bucket=bucket)
        else:
            raise

def upload_and_presign(local_path: str, key: str, content_type: str = "application/octet-stream"):
    ensure_bucket(S3_BUCKET)
    s3.upload_file(local_path, S3_BUCKET, key, ExtraArgs={"ContentType": content_type})
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_TTL,
    )
    return url
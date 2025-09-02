import os

import boto3
from botocore.config import Config

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


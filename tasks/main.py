import os
import tempfile
import boto3
from botocore.config import Config
from celery_app import celery
from steganography.lsb import LeastSignificantBit
from helpers.message_bit import bit_to_message
from steganography.metrics import StegoMetrics
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from s3.main import S3_BUCKET, PRESIGN_TTL
from helpers.message_bit import message_to_bit
from uuid import uuid4


@celery.task(name="tasks.main.embed_task", bind=True)
def embed_task(self, *, cover_key: str, message: str, k_val: int, original_filename: str = "cover.png"):
    """
    Downloads cover image from S3, embeds message, uploads stego PNG to S3,
    returns { stego_key, url, k_val }.
    """
    if not (1 <= k_val <= 8):
        raise ValueError("k_val must be between 1 and 8")

    cover_path = stego_out_path = None
    try:
        # 1) Download cover to temp
        cover_path = download_to_tmp(S3_BUCKET, cover_key)

        # 2) Prepare output temp PNG
        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        # 3) Embed
        lsb = LeastSignificantBit(k_val=k_val)
        msg_bits = message_to_bit(message)
        lsb.embed_message(cover_path, stego_out_path, msg_bits)

        # 4) Upload stego to S3
        base = os.path.splitext(original_filename)[0]
        stego_name = f"{base}_lsb_{uuid4().hex}.png"

        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()

        stego_key = upload_bytes_and_get_key(
            "stego/embedded",
            stego_name,
            stego_bytes,
            "image/png",
        )

        # 5) Presign for convenience
        url = presign_get_url(stego_key, ttl=PRESIGN_TTL)

        return {
            "stego_key": stego_key,
            "url": url,
            "expires_in": PRESIGN_TTL,
            "k_val": k_val,
            "note": "Use this k_val when extracting.",
        }
    finally:
        for p in (cover_path, stego_out_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


@celery.task(name="tasks.main.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int):
    """
    Downloads images from S3, runs extraction + metrics, returns JSON-safe dict.
    """
    stego_path = original_path = None
    try:
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)

        lsb = LeastSignificantBit(k_val=k_val)
        bits = lsb.extract_message(stego_path)
        message = bit_to_message(bits)

        metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)

        return {
            "message": message,
            "metrics": {
                "mse": float(mse),
                "psnr": float(psnr) if psnr != float("inf") else "inf",
                "ssim": float(ssim),
            },
            "k_val": k_val,
            "stego_key": stego_key,
            "original_key": original_key,
        }
    finally:
        for p in (stego_path, original_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

import os
import tempfile
from main_celery import celery
from methods.steganography.lsb import LeastSignificantBit
from helpers.message_bit import message_to_bit, bit_to_message
from methods.steganography.metrics import StegoMetrics
from s3.main import S3_BUCKET, PRESIGN_TTL
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url

@celery.task(name="tasks.steganography.lsb.embed_task", bind=True)
def embed_task(self, *, cover_key: str, message: str, k_val: int, original_filename: str = "cover.png", job_id: str | None = None):
    self.update_state(state="STARTED", meta={"stage": "downloading", "progress": 5})
    cover_path = stego_out_path = None
    try:
        cover_path = download_to_tmp(S3_BUCKET, cover_key)

        self.update_state(meta={"stage": "embedding", "progress": 35})
        lsb = LeastSignificantBit(k_val=k_val)
        fd, stego_out_path = tempfile.mkstemp(suffix=".png"); os.close(fd)
        msg_bits = message_to_bit(message)
        lsb.embed_message(cover_path, stego_out_path, msg_bits)

        self.update_state(meta={"stage": "uploading", "progress": 75})
        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()

        folder_prefix = cover_key.rsplit("/", 1)[0] if "/" in cover_key else "steganography"
        base = os.path.splitext(original_filename)[0]
        stego_name = f"stego-{base}.png"

        stego_key = upload_bytes_and_get_key(
            folder_prefix,
            stego_name,
            stego_bytes,
            "image/png",
        )

        url = presign_get_url(stego_key, ttl=PRESIGN_TTL)
        self.update_state(meta={"stage": "finalizing", "progress": 95})

        return {
            "stego_key": stego_key,
            "url": url,
            "expires_in": PRESIGN_TTL,
            "k_val": k_val,
            "note": "Use this k_val when extracting.",
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e
    finally:
        for p in (cover_path, stego_out_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except:
                pass


@celery.task(name="tasks.steganography.lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int):
    self.update_state(state="STARTED", meta={"stage": "downloading", "progress": 5})
    stego_path = original_path = None
    try:
        stego_path    = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)

        self.update_state(meta={"stage": "extracting", "progress": 40})
        lsb = LeastSignificantBit(k_val=k_val)
        bits = lsb.extract_message(stego_path)
        message = bit_to_message(bits)

        self.update_state(meta={"stage": "metrics", "progress": 70})
        metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)

        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "message": message,
            "metrics": {
                "mse": float(mse)  if mse != float("inf") else "inf",
                "psnr": float(psnr) if psnr != float("inf") else "inf",
                "ssim": float(ssim)  if ssim != float("inf") else "inf",
            },
            "k_val": k_val,
            "stego_key": stego_key,
            "original_key": original_key,
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e
    finally:
        for p in (stego_path, original_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except:
                pass

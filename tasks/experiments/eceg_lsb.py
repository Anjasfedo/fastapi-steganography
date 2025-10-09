import os
import tempfile
import json
from main_celery import celery
from typing import Optional
from methods.steganography.lsb import LeastSignificantBit
# Asumsi kelas ECEG sudah ada
from methods.cryptography.eceg import EllipticCurveElGamal
from s3.main import S3_BUCKET
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from helpers.message_bit import message_to_bit, bit_to_message
from methods.steganography.metrics import StegoMetrics
from methods.lossless_compression.metrics import CompressionMetrics



eceg = EllipticCurveElGamal()




@celery.task(name="tasks.experiments.eceg_lsb.embed_task", bind=True)
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, plaintext: str):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        # Generate new ECEG key pair for this embed operation
        self.update_state(meta={"stage": "Generating Keys", "progress": 10})
        private_key, new_public_key = eceg.generate_keys(as_int=True)

        # Plaintext processing
        self.update_state(meta={"stage": "Processing Plaintext", "progress": 20})
        padded_plaintext = plaintext
        self.update_state(meta={"stage": "Plaintext Ready", "progress": 35})

        # Encrypt the message
        ciphertext = eceg.encrypt_message(padded_plaintext, new_public_key)
        self.update_state(meta={"stage": "Message Encrypted", "progress": 60})

        msg_bits = message_to_bit(ciphertext)

        cover_path = download_to_tmp(S3_BUCKET, cover_key)
        lsb = LeastSignificantBit(k_val=k_val)

        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        lsb.embed_message(cover_path, stego_out_path, msg_bits)
        self.update_state(meta={"stage": "LSB Embedding", "progress": 75})

        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()
        folder_prefix = cover_key.rsplit("/", 1)[0]
        stego_name = f"stego-eceg-lsb-{os.path.splitext(original_filename)[0]}.png"
        stego_key = upload_bytes_and_get_key(
            folder_prefix, stego_name, stego_bytes, "image/png")
        url = presign_get_url(stego_key)

        return {
            "stego_key": stego_key, "stego_url": url, "k_val": k_val,
            "private_key": private_key, "public_key": new_public_key
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
                          "exc_type": type(e).__name__, "exc_message": str(e)})
        raise e
    finally:
        for p in (cover_path, stego_out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass


@celery.task(name="tasks.experiments.eceg_lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: Optional[str], k_val: int, private_key: int):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 10})
    stego_path = original_path = None
    try:
        # Ekstrak pesan mentah (berisi ciphertext dalam format JSON)
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        if original_key:
            original_path = download_to_tmp(S3_BUCKET, original_key)
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)

        self.update_state(
            meta={"stage": "Raw Message Extracted", "progress": 40})

        # --- LANGKAH BARU: Dekripsi ECEG ---
        raw_ciphertext = bit_to_message(extracted_bits)

        decrypted_padded_message = eceg.decrypt_message(
            raw_ciphertext, private_key)

        self.update_state(meta={"stage": "ECEG Decrypted", "progress": 60})

        # Processing plaintext
        self.update_state(meta={"stage": "Processing plaintext", "progress": 60})
        record = decrypted_padded_message
        self.update_state(meta={"stage": "Plaintext Ready", "progress": 80})

        # Hitung metrik hanya jika original image ada
        metrics_dict = {}
        if original_path:
            metrics_calc = StegoMetrics(ori_image=original_path)
            mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)

            original_size = len(decrypted_padded_message) * 8
            compressed_size = len(raw_ciphertext)

            metrics_calculator = CompressionMetrics(
                original_size_bytes=original_size)
            cr, ss = metrics_calculator.calculate_all_metrics(
                compressed_size_bytes=compressed_size)

            metrics_dict = {
                "mse": float(mse) if mse != float("inf") else "inf",
                "psnr": float(psnr) if psnr != float("inf") else "inf",
                "ssim": float(ssim) if ssim != float("inf") else "inf",
                "cr": float(cr) if cr != float("inf") else "inf",
                "ss": float(ss) if ss != float("inf") else "inf"
            }

        # Add security level metric (2^8 for ECEG methods)
        metrics_dict["sl"] = 256  # 2^8

        # Mengembalikan satu objek dengan record yang sesuai
        return {
            "record": record,
            "metrics": metrics_dict
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
                          "exc_type": type(e).__name__, "exc_message": str(e)})
        raise e
    finally:
        for p in (stego_path, original_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

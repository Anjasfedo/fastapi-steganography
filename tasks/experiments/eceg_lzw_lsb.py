import os
import tempfile
import json
import math
from typing import Optional
from main_celery import celery
from methods.steganography.lsb import LeastSignificantBit
from methods.cryptography.eceg import EllipticCurveElGamal
from methods.lossless_compression.lzw import LZW
from s3.main import S3_BUCKET
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from methods.preprocess.data_serialization import serialize_record, deserialize_padded_record
from methods.preprocess.padding_data import pad_message_to_capacity
from helpers.message_bit import message_to_bit, bit_to_message
from methods.steganography.metrics import StegoMetrics
from methods.lossless_compression.metrics import CompressionMetrics

KTP_FIELD_ORDER = [
    'NIK', 'Nama', 'Tempat_Tgl_Lahir', 'Jenis_Kelamin', 'Gol_Darah', 'Alamat',
    'RT_RW', 'Kel_Desa', 'Kecamatan', 'Agama', 'Status_Perkawinan',
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku_Hingga'
]

eceg = EllipticCurveElGamal()
lzw = LZW()


@celery.task(name="tasks.cryptography.eceg_lzw_lsb.generate_keys_task", bind=True)
def generate_keys_task(self):
    """Generate and return ElGamal private and public keys."""
    try:
        private_key, public_key = eceg.generate_keys(
            as_int=True)  # Generate keys
        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "private_key": private_key,
            "public_key": public_key
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__,
            "exc_message": str(e),
            "progress": 100
        })
        raise e


@celery.task(name="tasks.experiments.eceg_lzw_lsb.embed_task", bind=True)
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, public_key: int, max_chars: Optional[int] = None,
               ktp_data: Optional[dict] = None,
               plaintext: Optional[str] = None):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        # Validate input parameters
        if ktp_data is None and plaintext is None:
            raise ValueError("Either ktp_data or plaintext must be provided")
        if ktp_data is not None and plaintext is not None:
            raise ValueError("Cannot provide both ktp_data and plaintext")

        # Process message based on input type
        if ktp_data is not None:
            # KTP data processing
            self.update_state(meta={"stage": "Processing KTP Data", "progress": 10})
            message_block = serialize_record(ktp_data, KTP_FIELD_ORDER)
            self.update_state(meta={"stage": "KTP Data Serialized", "progress": 15})

            # Apply padding if max_chars is specified
            if max_chars is not None and max_chars > 0:
                padded_plaintext = pad_message_to_capacity(message_block, max_chars)
                self.update_state(meta={"stage": "Message Padded", "progress": 20})
            else:
                padded_plaintext = message_block
                self.update_state(meta={"stage": "Padding Skipped", "progress": 20})
        else:
            # Plaintext processing (skip serialization and padding)
            self.update_state(meta={"stage": "Processing Plaintext", "progress": 10})
            padded_plaintext = plaintext
            self.update_state(meta={"stage": "Plaintext Ready", "progress": 20})

        ciphertext = eceg.encrypt_message(padded_plaintext, public_key)
        self.update_state(meta={"stage": "Encrypted", "progress": 40})

        # 4. Compress
        compressed_bits, bit_width = lzw.compress(ciphertext)
        self.update_state(meta={"stage": "Compressed", "progress": 60})

        # 5. Embed
        cover_path = download_to_tmp(S3_BUCKET, cover_key)
        lsb = LeastSignificantBit(k_val=k_val)

        # Di sinilah error 'Message too long!' kemungkinan besar akan terjadi
        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        lsb.embed_message(cover_path, stego_out_path, compressed_bits)
        self.update_state(meta={"stage": "Embedded", "progress": 80})

        # Unggah hasil
        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()
        folder_prefix = cover_key.rsplit("/", 1)[0]
        stego_name = f"stego-full-{os.path.splitext(original_filename)[0]}.png"
        stego_key = upload_bytes_and_get_key(
            folder_prefix, stego_name, stego_bytes, "image/png")
        url = presign_get_url(stego_key)

        return {"stego_key": stego_key, "url": url, "k_val": k_val, 'bit_width': bit_width}
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


@celery.task(name="tasks.experiments.eceg_lzw_lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int, private_key: int, bit_width: int, type: str = "ktp"):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 10})
    stego_path = original_path = None
    try:
        # 1. Extract
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)
        self.update_state(meta={"stage": "Extracted", "progress": 30})

        decompressed_ciphertext = lzw.decompress(extracted_bits, bit_width)
        self.update_state(meta={"stage": "Decompressed", "progress": 50})

        # 3. Decrypt
        decompressed_message_block = eceg.decrypt_message(
            decompressed_ciphertext, private_key)
        self.update_state(meta={"stage": "Decrypted", "progress": 70})

        # Process extracted message based on type
        if type == "ktp":
            self.update_state(meta={"stage": "Deserializing KTP data", "progress": 60})
            record = deserialize_padded_record(decompressed_message_block, KTP_FIELD_ORDER)
            self.update_state(meta={"stage": "KTP Record Deserialized", "progress": 80})
        else:
            self.update_state(meta={"stage": "Processing plaintext", "progress": 60})
            record = decompressed_message_block.strip()
            self.update_state(meta={"stage": "Plaintext Ready", "progress": 80})

        # 5. Metrics
        metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)

        original_size_bytes = len(decompressed_message_block) * 8
        compressed_size_bytes = len(extracted_bits)

        comp_metrics_calc = CompressionMetrics(
            original_size_bytes=original_size_bytes)
        compression_ratio, space_saving_percentage = comp_metrics_calc.calculate_all_metrics(
            compressed_size_bytes=compressed_size_bytes)

        metrics_dict = {
            "mse": float(mse) if mse != float("inf") else "inf",
            "psnr": float(psnr) if psnr != float("inf") else "inf",
            "ssim": float(ssim) if ssim != float("inf") else "inf",
            "compression_ratio": float(compression_ratio) if compression_ratio != float("inf") else "inf",
            "space_saving_percentage": float(space_saving_percentage) if space_saving_percentage != float("inf") else "inf"
        }

        # Mengembalikan satu objek dengan record yang sesuai
        return {
            "record": record,
            "type": type,
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

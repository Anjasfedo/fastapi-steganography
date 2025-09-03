import os
import tempfile
import json
import math
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
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku Hingga'
]

eceg = EllipticCurveElGamal()
lzw = LZW()


@celery.task(name="tasks.cryptography.eceg_lsb.generate_keys_task", bind=True)
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
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, public_key: int, max_chars: int,
               NIK: str,
               Nama: str,
               Tempat_Tgl_Lahir: str,
               Jenis_Kelamin: str,
               Gol_Darah: str,
               Alamat: str,
               RT_RW: str,
               Kel_Desa: str,
               Kecamatan: str,
               Agama: str,
               Status_Perkawinan: str,
               Pekerjaan: str,
               Kewarganegaraan: str,
               Berlaku_Hingga: str):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        ktp_data = {
            "NIK": NIK,
            "Nama": Nama,
            "Tempat_Tgl_Lahir": Tempat_Tgl_Lahir,
            "Jenis_Kelamin": Jenis_Kelamin,
            "Gol_Darah": Gol_Darah,
            "Alamat": Alamat,
            "RT_RW": RT_RW,
            "Kel_Desa": Kel_Desa,
            "Kecamatan": Kecamatan,
            "Agama": Agama,
            "Status_Perkawinan": Status_Perkawinan,
            "Pekerjaan": Pekerjaan,
            "Kewarganegaraan": Kewarganegaraan,
            "Berlaku Hingga": Berlaku_Hingga,
        }

        message_block = serialize_record(ktp_data, KTP_FIELD_ORDER)
        self.update_state(meta={"stage": "Data Serialized", "progress": 15})
        padded_plaintext = pad_message_to_capacity(message_block, max_chars)

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
def extract_task(self, *, stego_key: str, original_key: str, k_val: int, private_key: int, bit_width: int):
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

        # 4. Deserialize (dengan potensi masalah pemotongan padding)
        ktp_record = deserialize_padded_record(
            decompressed_message_block, KTP_FIELD_ORDER)
        self.update_state(meta={"stage": "Deserialized", "progress": 85})

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

        return {
            "ktp_record": ktp_record,
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

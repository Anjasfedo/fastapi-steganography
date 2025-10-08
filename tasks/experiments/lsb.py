import os
import tempfile
import json
from main_celery import celery
from methods.steganography.lsb import LeastSignificantBit
from s3.main import S3_BUCKET
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from methods.preprocess.data_serialization import serialize_record, deserialize_record
from methods.preprocess.padding_data import pad_message_to_capacity
from helpers.message_bit import message_to_bit, bit_to_message
from typing import Optional
from methods.steganography.metrics import StegoMetrics
from methods.lossless_compression.metrics import CompressionMetrics

KTP_FIELD_ORDER = [
    'NIK', 'Nama', 'Tempat_Tgl_Lahir', 'Jenis_Kelamin', 'Gol_Darah', 'Alamat',
    'RT_RW', 'Kel_Desa', 'Kecamatan', 'Agama', 'Status_Perkawinan',
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku_Hingga'
]


@celery.task(name="tasks.experiments.lsb.embed_task", bind=True)
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, max_chars: Optional[int] = None,
               plaintext: str
               ):
    """Alur kerja untuk menyisipkan plaintext ke dalam gambar."""
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        # Plaintext processing (already preprocessed)
        self.update_state(meta={"stage": "Processing Plaintext", "progress": 10})
        final_message = plaintext
        self.update_state(meta={"stage": "Plaintext Ready", "progress": 60})

        # --- PERUBAHAN UTAMA: Hapus Kalkulasi Kapasitas ---
        # Langkah menghitung max_chars sekarang dilakukan di sisi klien/API.
        # Kita hanya perlu mengunduh gambar untuk proses embed.
        cover_path = download_to_tmp(S3_BUCKET, cover_key)
        lsb = LeastSignificantBit(k_val=k_val)
        self.update_state(meta={"stage": "Cover Downloaded", "progress": 15})

        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        msg_bits = message_to_bit(final_message)
        lsb.embed_message(cover_path, stego_out_path, msg_bits)
        self.update_state(meta={"stage": "Embedding Message", "progress": 75})

        # ... (sisa logika untuk unggah hasil dan cleanup tetap sama)
        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()

        folder_prefix = cover_key.rsplit("/", 1)[0]
        base = os.path.splitext(original_filename)[0]
        stego_name = f"stego-lsb-{base}.png"
        stego_key = upload_bytes_and_get_key(
            folder_prefix, stego_name, stego_bytes, "image/png")
        url = presign_get_url(stego_key)

        return {"stego_key": stego_key, "url": url, "k_val": k_val}

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


@celery.task(name="tasks.experiments.lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int):
    """
    Mengekstrak plaintext dari stego image dan menghitung metrik.
    """
    self.update_state(state="STARTED", meta={
                      "stage": "Downloading images", "progress": 10})
    stego_path = original_path = None
    try:
        # --- LANGKAH 1: Unduh Gambar Stego & Asli ---
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)
        self.update_state(
            meta={"stage": "Extracting raw message", "progress": 30})

        # --- LANGKAH 2: Ekstrak Pesan Mentah ---
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)
        record = bit_to_message(extracted_bits).strip()

        self.update_state(meta={"stage": "Plaintext Extracted", "progress": 80})

        # --- Sisa langkah (Menghitung Metrik) tetap sama ---
        metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)
        original_size = len(extracted_bits)
        compressed_size = len(extracted_bits)

        metrics_calculator = CompressionMetrics(
            original_size_bytes=original_size)
        compression_ratio, space_saving_percentage = metrics_calculator.calculate_all_metrics(
            compressed_size_bytes=compressed_size)

        metrics_dict = {
            "mse": float(mse) if mse != float("inf") else "inf",
            "psnr": float(psnr) if psnr != float("inf") else "inf",
            "ssim": float(ssim) if ssim != float("inf") else "inf",
            "compression_ratio": float(compression_ratio) if compression_ratio != float("inf") else "inf",
            "space_saving_percentage": float(space_saving_percentage) if space_saving_percentage != float("inf") else "inf"
        }

        # Mengembalikan satu objek dengan record
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

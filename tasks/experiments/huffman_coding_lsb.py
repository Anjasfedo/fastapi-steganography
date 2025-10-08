import os
import tempfile
import json
import math
from typing import Optional
from main_celery import celery
from methods.steganography.lsb import LeastSignificantBit
from methods.lossless_compression.huffman_coding import HuffmanCoding
from s3.main import S3_BUCKET
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from methods.preprocess.data_serialization import serialize_record, deserialize_record
from helpers.message_bit import message_to_bit, bit_to_message
from methods.steganography.metrics import StegoMetrics
from methods.lossless_compression.metrics import CompressionMetrics
from methods.preprocess.padding_data import pad_message_to_capacity


KTP_FIELD_ORDER = [
    'NIK', 'Nama', 'Tempat_Tgl_Lahir', 'Jenis_Kelamin', 'Gol_Darah', 'Alamat',
    'RT_RW', 'Kel_Desa', 'Kecamatan', 'Agama', 'Status_Perkawinan',
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku_Hingga'
]


@celery.task(name="tasks.experiments.huffman_coding_lsb.embed_task", bind=True)
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, max_chars: Optional[int] = None,
               plaintext: str):
    """Alur kerja untuk menyisipkan plaintext ke dalam gambar dengan kompresi Huffman."""
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        # Plaintext processing (already preprocessed)
        self.update_state(meta={"stage": "Processing Plaintext", "progress": 10})
        final_message = plaintext
        self.update_state(meta={"stage": "Plaintext Ready", "progress": 60})

        # 2. Kompresi dengan Huffman Coding
        encoded_bits, _, codebook = HuffmanCoding.build_huffman(final_message)
        self.update_state(meta={"stage": "Huffman Compressed", "progress": 40})

        # 3. Unggah Codebook ke S3 di folder yang sama dengan cover image
        folder_prefix = cover_key.rsplit("/", 1)[0]
        codebook_bytes = json.dumps(codebook).encode('utf-8')
        codebook_key = upload_bytes_and_get_key(
            folder_prefix, f"huffman-codes_{os.urandom(4).hex()}.json", codebook_bytes, "application/json"
        )
        codebook_url = presign_get_url(codebook_key)
        self.update_state(meta={"stage": "Codebook Uploaded", "progress": 50})

        # 4. Unduh Gambar & Sisipkan Pesan Terkompresi
        cover_path = download_to_tmp(S3_BUCKET, cover_key)
        lsb = LeastSignificantBit(k_val=k_val)
        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        lsb.embed_message(cover_path, stego_out_path, encoded_bits)
        self.update_state(meta={"stage": "LSB Embedding", "progress": 75})

        # 5. Unggah Hasil
        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()
        stego_name = f"stego-huffman-{os.path.splitext(original_filename)[0]}.png"
        stego_key = upload_bytes_and_get_key(
            folder_prefix, stego_name, stego_bytes, "image/png")
        url = presign_get_url(stego_key)

        return {"stego_key": stego_key, "stego_url": url, "k_val": k_val, "codebook_key": codebook_key, "codebook_url": codebook_url}
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


@celery.task(name="tasks.experiments.huffman_coding_lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int, codebook_key: str):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 10})
    stego_path = original_path = codebook_path = None
    try:
        # 1. Unduh semua file yang dibutuhkan
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)
        codebook_path = download_to_tmp(S3_BUCKET, codebook_key)
        self.update_state(meta={"stage": "Files Downloaded", "progress": 30})

        # 2. Ekstrak Bit Terkompresi dari gambar
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)
        self.update_state(
            meta={"stage": "Compressed Bits Extracted", "progress": 50})

        # 3. Dekompresi Huffman menggunakan Codebook
        with open(codebook_path, 'r') as f:
            codebook = json.load(f)
        huffman_tree = HuffmanCoding.build_huffman_tree_from_codebook(codebook)
        record = HuffmanCoding.decode(extracted_bits, huffman_tree)
        self.update_state(
            meta={"stage": "Huffman Decompressed", "progress": 70})

        # 5. Hitung Metrik
        stego_metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = stego_metrics_calc.calculate_metrics(stego_path)

        original_size_bytes = len(record) * 8
        compressed_size_bytes = len(extracted_bits)

        comp_metrics_calc = CompressionMetrics(
            original_size_bytes=original_size_bytes)
        cr, ss = comp_metrics_calc.calculate_all_metrics(
            compressed_size_bytes=compressed_size_bytes)

        metrics_dict = {
            "mse": float(mse) if mse != float("inf") else "inf",
            "psnr": float(psnr) if psnr != float("inf") else "inf",
            "ssim": float(ssim) if ssim != float("inf") else "inf",
            "cr": float(cr) if cr != float("inf") else "inf",
            "ss": float(ss) if ss != float("inf") else "inf"
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
        for p in (stego_path, original_path, codebook_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

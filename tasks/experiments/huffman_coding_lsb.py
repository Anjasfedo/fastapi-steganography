import os
import tempfile
import json
import math
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
def embed_task(self, *, cover_key: str, k_val: int, original_filename: str, max_chars: int,
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
               Berlaku_Hingga: str
               ):
    """Alur kerja untuk menyisipkan satu data KTP ke dalam gambar."""
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 5})
    cover_path = stego_out_path = None
    try:
        # 1. Susun kembali dictionary dari parameter individual
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
            "Berlaku_Hingga": Berlaku_Hingga,
        }
        # --- Sisa alur kerja menggunakan max_chars dari parameter ---
        message_block = serialize_record(ktp_data, KTP_FIELD_ORDER)
        self.update_state(meta={"stage": "Data Serialized", "progress": 45})

        final_message = pad_message_to_capacity(message_block, max_chars)
        self.update_state(meta={"stage": "Message Padded", "progress": 60})

        # 2. Kompresi dengan Huffman Coding
        encoded_bits, _, codebook = HuffmanCoding.build_huffman(final_message)
        self.update_state(meta={"stage": "Huffman Compressed", "progress": 40})

        # 3. Unggah Codebook ke S3 di folder yang sama dengan cover image
        folder_prefix = cover_key.rsplit("/", 1)[0]
        codebook_bytes = json.dumps(codebook).encode('utf-8')
        codebook_key = upload_bytes_and_get_key(
            folder_prefix, f"huffman-codes_{os.urandom(4).hex()}.json", codebook_bytes, "application/json"
        )
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

        return {"stego_key": stego_key, "url": url, "k_val": k_val, "codebook_key": codebook_key}
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
        decompressed_message_block = HuffmanCoding.decode(
            extracted_bits, huffman_tree)
        self.update_state(
            meta={"stage": "Huffman Decompressed", "progress": 70})

        # 4. Deserialisasi Data KTP
        ktp_record = deserialize_record(
            decompressed_message_block, KTP_FIELD_ORDER)

        # 5. Hitung Metrik
        stego_metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = stego_metrics_calc.calculate_metrics(stego_path)

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
        for p in (stego_path, original_path, codebook_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

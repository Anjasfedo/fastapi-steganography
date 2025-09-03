import os
import tempfile
import json
import math
from main_celery import celery
from methods.steganography.lsb import LeastSignificantBit
from methods.cryptography.eceg import EllipticCurveElGamal
from methods.lossless_compression.huffman_coding import HuffmanCoding
from s3.main import S3_BUCKET
from s3.utils import download_to_tmp, upload_bytes_and_get_key, presign_get_url
from methods.preprocess.data_serialization import serialize_record, deserialize_record
from methods.preprocess.bit_padding import encode_with_padding_info, decode_with_padding_info
from helpers.message_bit import message_to_bit, bit_to_message
from methods.preprocess.padding_data import pad_message_to_capacity
from methods.steganography.metrics import StegoMetrics
from methods.lossless_compression.metrics import CompressionMetrics

KTP_FIELD_ORDER = [
    'NIK', 'Nama', 'Tempat/Tgl Lahir', 'Jenis Kelamin', 'Gol Darah', 'Alamat',
    'RT/RW', 'Kel/Desa', 'Kecamatan', 'Agama', 'Status Perkawinan',
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku Hingga'
]

eceg = EllipticCurveElGamal()


@celery.task(name="tasks.cryptography.huffman_coding_eceg_lsb.generate_keys_task", bind=True)
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


@celery.task(name="tasks.experiments.huffman_coding_eceg_lsb.embed_task", bind=True)
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
        self.update_state(meta={"stage": "Message Padded", "progress": 30})

        # 2. Compress with Huffman
        compressed_bit, _, codebook = HuffmanCoding.build_huffman(
            padded_plaintext)
        self.update_state(meta={"stage": "Huffman Compressed", "progress": 30})

        # 3. Bit Padding
        ascii_safe_bits = encode_with_padding_info(compressed_bit)
        self.update_state(meta={"stage": "Bit Padded", "progress": 45})

        # 4. Encrypt
        ciphertext = eceg.encrypt_message(ascii_safe_bits, public_key)
        self.update_state(meta={"stage": "Encrypted", "progress": 60})

        # 5. Upload Codebook & Embed
        folder_prefix = cover_key.rsplit("/", 1)[0]
        codebook_bytes = json.dumps(codebook).encode('utf-8')
        codebook_key = upload_bytes_and_get_key(
            folder_prefix, f"huffman-codes_{os.urandom(4).hex()}.json", codebook_bytes, "application/json"
        )

        cover_path = download_to_tmp(S3_BUCKET, cover_key)
        lsb = LeastSignificantBit(k_val=k_val)
        final_bits_to_embed = message_to_bit(ciphertext)

        fd, stego_out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        lsb.embed_message(cover_path, stego_out_path, final_bits_to_embed)
        self.update_state(meta={"stage": "Embedded", "progress": 80})

        # Unggah hasil
        with open(stego_out_path, "rb") as f:
            stego_bytes = f.read()
        stego_name = f"stego-huffman-eceg-{os.path.splitext(original_filename)[0]}.png"
        stego_key = upload_bytes_and_get_key(
            folder_prefix, stego_name, stego_bytes, "image/png")
        url = presign_get_url(stego_key)

        return {
            "stego_key": stego_key, "url": url, "k_val": k_val, "codebook_key": codebook_key
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


@celery.task(name="tasks.experiments.huffman_coding_eceg_lsb.extract_task", bind=True)
def extract_task(self, *, stego_key: str, original_key: str, k_val: int, private_key: int, codebook_key: str):
    self.update_state(state="STARTED", meta={
                      "stage": "Initializing", "progress": 10})
    stego_path = original_path = codebook_path = None
    try:
        # 1. Download
        stego_path = download_to_tmp(S3_BUCKET, stego_key)
        original_path = download_to_tmp(S3_BUCKET, original_key)
        codebook_path = download_to_tmp(S3_BUCKET, codebook_key)
        self.update_state(meta={"stage": "Downloaded", "progress": 25})

        # 2. Extract
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)
        ciphertext = bit_to_message(extracted_bits)
        self.update_state(meta={"stage": "Extracted", "progress": 40})

        # 3. Decrypt
        decrypted_ascii_safe = eceg.decrypt_message(
            ciphertext, private_key)
        self.update_state(meta={"stage": "Decrypted", "progress": 55})

        # 4. Bit Un-padding
        decrypted_ascii_safe = decode_with_padding_info(
            decrypted_ascii_safe)
        self.update_state(meta={"stage": "Bit Un-padded", "progress": 70})

        # 5. Decompress
        with open(codebook_path, 'r') as f:
            codebook = json.load(f)
        huffman_tree = HuffmanCoding.build_huffman_tree_from_codebook(codebook)
        decompressed_message_block = HuffmanCoding.decode(
            decrypted_ascii_safe, huffman_tree)
        self.update_state(meta={"stage": "Decompressed", "progress": 85})

        # 6. Deserialize & Metrics
        ktp_record = deserialize_record(decompressed_message_block, KTP_FIELD_ORDER)
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
        for p in (stego_path, original_path, codebook_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

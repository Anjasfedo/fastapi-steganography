import json
import os
from tempfile import NamedTemporaryFile
from main_celery import celery
from s3.utils import upload_bytes_and_get_key, presign_get_url, download_to_tmp
from s3.main import S3_BUCKET
from helpers.response_wrapper import api_response
# Assuming HuffmanCoding class is already defined
from methods.lossless_compression.huffman_coding import HuffmanCoding
from methods.lossless_compression.metrics import CompressionMetrics

# Create an instance of HuffmanCoding
huffman_coding = HuffmanCoding()


@celery.task(name="tasks.lossless_compression.huffman_coding.compress_task", bind=True)
def compress_task(self, *, input_string: str):
    """Compress a string using Huffman Coding and return the file with Huffman codes."""
    self.update_state(state="STARTED", meta={"progress": 10})

    try:
        # Apply Huffman coding to the input string
        encoded_bits, huffman_tree, codebook = HuffmanCoding.build_huffman(
            input_string)

        # Save the Huffman codebook to a file
        with NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            # Generate a random name for the file
            file_name = f"huffman_codes_{os.urandom(4).hex()}.json"
            json.dump(codebook, temp_file)
            temp_file_path = temp_file.name

        # Upload the file to S3
        file_key = upload_bytes_and_get_key("huffman_codes", file_name, open(
            temp_file_path, 'rb').read(), "application/json")

        # Generate URL to access the file
        # Presign for 1 hour, adjust as needed
        url = presign_get_url(file_key, ttl=3600)

        # Return the URL for the uploaded file
        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "file_key": file_key,
            "url": url,
            # Optionally, you can also return the encoded text
            "huffman_encoded_text": encoded_bits
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__,
            "exc_message": str(e),
            "progress": 100
        })
        raise e
    finally:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)  # Clean up temporary file
        except:
            pass


@celery.task(name="tasks.lossless_compression.huffman_coding.decompress_task", bind=True)
def decompress_task(self, *, file_key: str, encoded_bits: str):
    """Decompress a string using the Huffman Coding and the codebook from S3."""
    self.update_state(state="STARTED", meta={"progress": 10})

    try:
        # Step 1: Download the Huffman codebook file from S3
        codebook_path = download_to_tmp(S3_BUCKET, file_key)

        with open(codebook_path, 'r') as file:
            codebook = json.load(file)

        # Step 2: Rebuild the Huffman tree from the codebook
        huffman_tree = HuffmanCoding.build_huffman_tree_from_codebook(codebook)

        # Step 3: Decode the bitstring using the Huffman tree
        decoded_message = HuffmanCoding.decode(encoded_bits, huffman_tree)

        original_size = len(decoded_message) * 8
        compressed_size = len(encoded_bits)

        # Panggil kelas metrik dengan nilai BYTES yang benar
        metrics_calculator = CompressionMetrics(
            original_size_bytes=original_size)
        cr, ss = metrics_calculator.calculate_all_metrics(
            compressed_size_bytes=compressed_size)

        self.update_state(meta={"stage": "metrics", "progress": 70})

        # Step 4: Return the decoded message
        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "decoded_message": decoded_message,
            "metrics": {
                "cr": float(cr) if cr != float("inf") else "inf",
                "ss": float(ss) if ss != float("inf") else "inf",
            },
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__,
            "exc_message": str(e),
            "progress": 100
        })
        raise e
    finally:
        try:
            if os.path.exists(codebook_path):
                os.remove(codebook_path)  # Clean up downloaded file
        except:
            pass

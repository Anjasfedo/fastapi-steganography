from main_celery import celery
from helpers.response_wrapper import api_response
from methods.lossless_compression.lzw import LZW  # Assuming LZW class is in the same directory or another module

# Create an LZW instance
lzw = LZW()

@celery.task(name="tasks.lossless_compression.lzw.compress_task", bind=True)
def compress_task(self, *, input_string: str):
    """Compress a string using LZW algorithm and return the compressed bit string."""
    self.update_state(state="STARTED", meta={"progress": 10})
    try:
        compressed_data = lzw.compress(input_string)

        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "compressed_data": compressed_data
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e

@celery.task(name="tasks.lossless_compression.lzw.decompress_task", bind=True)
def decompress_task(self, *, compressed_bits: str):
    """Decompress a LZW compressed bit string back into the original message."""
    self.update_state(state="STARTED", meta={"progress": 10})
    try:
        decompressed_data = lzw.decompress(compressed_bits)

        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "decompressed_data": decompressed_data
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e

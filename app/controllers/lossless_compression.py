from fastapi import APIRouter, File, UploadFile, Form
from pydantic import BaseModel
from tasks.lossless_compression.lzw import compress_task as lzw_compress_task, decompress_task as lzw_decompress_task
from tasks.lossless_compression.huffman_coding import compress_task as huffman_coding_compress_task, decompress_task as huffman_coding_decompress_task
from helpers.response_wrapper import api_response
from uuid import uuid4
from s3.utils import upload_bytes_and_get_key

router = APIRouter()

class CompressionRequest(BaseModel):
    input_string: str

class DecompressionRequest(BaseModel):
    compressed_bits: str


@router.post("/lzw/compress")
async def compress(request: CompressionRequest):
    try:
        # Enqueue Celery compress task
        task = lzw_compress_task.delay(input_string=request.input_string)

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(status=False, message="Compression failed", error=str(e))

@router.post("/lzw/decompress")
async def decompress(request: DecompressionRequest):
    try:
        # Enqueue Celery decompress task
        task = lzw_decompress_task.delay(compressed_bits=request.compressed_bits)

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(status=False, message="Decompression failed", error=str(e))

@router.post("/huffman-coding/compress")
async def compress(request: CompressionRequest):
    try:
        # Enqueue Celery compress task
        task = huffman_coding_compress_task.delay(input_string=request.input_string)

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(status=False, message="Compression failed", error=str(e))
    


@router.post("/huffman-coding/decompress")
async def decompress(encoded_bits: str = Form(..., description="Encoded bits"), codebook_file: UploadFile = File(..., description="Codebook file")):
    try:
        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"
                
        job_id = uuid4().hex
        prefix = f"lossless-compression/huffman-coding/{job_id}"

        # Upload codebook image to S3
        codebook_key = upload_bytes_and_get_key(
            prefix,
            f"codebook-{codebook_name}",
            codebook_bytes,
            codebook_file.content_type or "application/json",
        )

        # Enqueue Celery decompress task
        task = huffman_coding_decompress_task.delay(file_key=codebook_key, encoded_bits=encoded_bits)

        # Return task info to track status
        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(status=False, message="Decompression failed", error=str(e))
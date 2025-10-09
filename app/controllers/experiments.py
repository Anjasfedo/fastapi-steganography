from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from uuid import uuid4
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.experiments.lsb import embed_task as lsb_embed_task, extract_task as lsb_extract_task
from tasks.experiments.eceg_lsb import embed_task as eceg_lsb_embed_task, extract_task as eceg_lsb_extract_task
from tasks.experiments.lzw_lsb import embed_task as lzw_lsb_embed_task, extract_task as lzw_lsb_extract_task
from tasks.experiments.huffman_coding_lsb import embed_task as huffman_coding_lsb_embed_task, extract_task as huffman_coding_lsb_extract_task
from tasks.experiments.eceg_lzw_lsb import embed_task as eceg_lzw_lsb_embed_task, extract_task as eceg_lzw_lsb_extract_task
from tasks.experiments.eceg_huffman_coding_lsb import embed_task as eceg_huffman_coding_lsb_embed_task, extract_task as eceg_huffman_coding_lsb_extract_task
from tasks.experiments.lzw_eceg_lsb import embed_task as lzw_eceg_lsb_embed_task, extract_task as lzw_eceg_lsb_extract_task
from tasks.experiments.huffman_coding_eceg_lsb import embed_task as huffman_coding_eceg_lsb_embed_task, extract_task as huffman_coding_eceg_lsb_extract_task
import os




router = APIRouter()


@router.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):
    """
    Menyisipkan pesan final ke dalam cover image dan memulai background task.
    """

    temp_file_path = None
    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        # Call task with plaintext
        task = lsb_embed_task.delay(
            cover_key=cover_key,
            k_val=k_val,
            original_filename=cover_name,
            plaintext=plaintext
        )

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "job_id": job_id,
            "cover_key": cover_key,
            "notes": "Gunakan WebSocket atau /tasks/{id} untuk mendapatkan stego key & URL."
        })
    except Exception as e:
        return api_response(status=False, message="Embedding failed", error=str(e), status_code=500)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/lsb/extract")
async def lsb_extract(
    stego_image: UploadFile = File(..., description="Stego image (PNG/JPG/PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                description="Original cover image (PNG/JPG/PNG) - optional, required for steganography metrics"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    )
):
    if not (1 <= k_val <= 8):
        raise HTTPException(
            status_code=422, detail="k_val must be between 1 and 8")

    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        # Generate unique job_id for tracking
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        # Upload stego image to S3
        stego_key = upload_bytes_and_get_key(
            prefix,
            f"stego-{stego_name}",
            stego_bytes,
            stego_image.content_type or "image/png",
        )

        # Handle optional original image
        orig_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            orig_key = upload_bytes_and_get_key(
                prefix,
                f"cover-{orig_name}",
                orig_bytes,
                original_image.content_type or "image/png",
            )

        # Enqueue Celery extract task
        task = lsb_extract_task.delay(
            stego_key=stego_key, original_key=orig_key, k_val=k_val)

        response_data = {
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "job_id": job_id,
            "stego_key": stego_key,
        }

        if orig_key:
            response_data["original_key"] = orig_key
            response_data["notes"] = "Use WebSocket or /tasks/{id} until SUCCESS to get message + metrics."
        else:
            response_data["notes"] = "Use WebSocket or /tasks/{id} until SUCCESS to get message only (no steganography metrics)."

        return api_response(data=response_data)

    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )

# --- Endpoint Embed ECEG+LSB ---




@router.post("/eceg-lsb/embed")
async def eceg_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        task = eceg_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-lsb/extract")
async def eceg_lsb_extract(
    stego_image: UploadFile = File(..., description="File stego image (PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                     description="File cover image asli (PNG) - optional, required for steganography metrics"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(..., description="Kunci privat ECEG (integer)")
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"

        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png"
        )

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png"
            )

        task = eceg_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB extract", error=str(e), status_code=500)


@router.post("/lzw-lsb/embed")
async def lzw_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = lzw_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-LSB embed", error=str(e), status_code=500)

# --- Endpoint Extract LZW+LSB ---


@router.post("/lzw-lsb/extract")
async def lzw_lsb_extract(
    stego_image: UploadFile = File(..., description="File stego image (PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                     description="File cover image asli (PNG) - optional, required for steganography metrics"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    bit_width: int = Form(
        ...,
        description="Lebar bit (misal: 12) yang digunakan oleh LZW untuk dekompresi, diperoleh dari hasil kompresi."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"

        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        task = lzw_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, bit_width=bit_width)

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-LSB extract", error=str(e), status_code=500)


@router.post("/huffman-coding-lsb/embed")
async def huffman_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = huffman_coding_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-LSB embed", error=str(e), status_code=500)


@router.post("/huffman-coding-lsb/extract")
async def huffman_lsb_extract(
    stego_image: UploadFile = File(..., description="File stego image (PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                     description="File cover image asli (PNG) - optional, required for steganography metrics"),
    codebook_file: UploadFile = File(...,
                                     description="File huffman codebook (.json)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = huffman_coding_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, codebook_key=codebook_key
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-LSB extract", error=str(e), status_code=500)




@router.post("/eceg-lzw-lsb/embed")
async def eceg_lzw_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(4, ge=1, le=8, description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = eceg_lzw_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LZW-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-lzw-lsb/extract")
async def eceg_lzw_lsb_extract(
    stego_image: UploadFile = File(
        ...,
        description="File gambar stego (format PNG) yang berisi data tersembunyi."
    ),
    original_image: Optional[UploadFile] = File(
        None,
        description="File gambar cover asli (format PNG) untuk perbandingan metrik kualitas - optional, required for steganography metrics."
    ),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(
        ...,
        description="Kunci privat ECEG (integer) yang diperlukan untuk mendekripsi pesan."
    ),
    bit_width: int = Form(
        ...,
        description="Lebar bit (misal: 12) yang digunakan oleh LZW untuk dekompresi, diperoleh dari hasil kompresi."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        task = eceg_lzw_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, bit_width=bit_width
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LZW-LSB extract", error=str(e), status_code=500)




@router.post("/eceg-huffman-coding-lsb/embed")
async def eceg_huffman_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = eceg_huffman_coding_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-Huffman-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-huffman-coding-lsb/extract")
async def eceg_huffman_lsb_extract(
    stego_image: UploadFile = File(..., description="File stego image (PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                     description="File cover image asli (PNG) - optional, required for steganography metrics"),
    codebook_file: UploadFile = File(...,
                                     description="File huffman codebook (.json)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(
        ...,
        description="Kunci privat ECEG (integer) yang diperlukan untuk mendekripsi pesan."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = eceg_huffman_coding_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, codebook_key=codebook_key
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-Huffman-LSB extract", error=str(e), status_code=500)




@router.post("/lzw-eceg-lsb/embed")
async def lzw_eceg_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = lzw_eceg_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/lzw-eceg-lsb/extract")
async def lzw_eceg_lsb_extract(
    stego_image: UploadFile = File(
        ...,
        description="File gambar stego (format PNG) yang berisi data tersembunyi."
    ),
    original_image: Optional[UploadFile] = File(
        None,
        description="File gambar cover asli (format PNG) untuk perbandingan metrik kualitas - optional, required for steganography metrics."
    ),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(
        ...,
        description="Kunci privat ECEG (integer) yang diperlukan untuk mendekripsi pesan."
    ),
    bit_width: int = Form(
        ...,
        description="Lebar bit (misal: 12) yang digunakan oleh LZW untuk dekompresi, diperoleh dari hasil kompresi."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        task = lzw_eceg_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val,
            private_key=private_key, bit_width=bit_width
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-ECEG-LSB extract", error=str(e), status_code=500)




@router.post("/huffman-coding-eceg-lsb/embed")
async def huffman_eceg_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    plaintext: str = Form(..., description="Plain text message to embed")
):

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        task = huffman_coding_eceg_lsb_embed_task.delay(
            cover_key=cover_key, k_val=k_val, original_filename=cover_name,
            plaintext=plaintext
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/huffman-coding-eceg-lsb/extract")
async def huffman_eceg_lsb_extract(
    stego_image: UploadFile = File(..., description="File stego image (PNG)"),
    original_image: Optional[UploadFile] = File(None,
                                     description="File cover image asli (PNG) - optional, required for steganography metrics"),
    codebook_file: UploadFile = File(...,
                                     description="File huffman codebook (.json)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(
        ...,
        description="Kunci privat ECEG (integer) yang diperlukan untuk mendekripsi pesan."
    )
):
    try:
        stego_bytes = await stego_image.read()
        stego_name = stego_image.filename or "stego.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_image.content_type or "image/png")

        # Handle optional original image
        original_key = None
        if original_image:
            orig_bytes = await original_image.read()
            orig_name = original_image.filename or "original.png"
            original_key = upload_bytes_and_get_key(
                prefix, f"cover-{orig_name}", orig_bytes, original_image.content_type or "image/png")

        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = huffman_coding_eceg_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, codebook_key=codebook_key
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-ECEG-LSB extract", error=str(e), status_code=500)

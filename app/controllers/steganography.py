from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from uuid import uuid4
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.steganography.lsb import embed_task, extract_task
import tempfile
import os
from methods.steganography.lsb import LeastSignificantBit
from helpers.human_readable import number_to_words_id

router = APIRouter()


@router.post("/lsb/calculate-capacity")
async def lsb_calculate_capacity(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(4, ge=1, le=8, description="Number of LSBs to use (1-8)")
):
    """
    Menghitung kapasitas maksimum penyisipan pesan (dalam karakter) untuk sebuah gambar.
    """
    temp_file_path = None
    try:
        # Simpan file sementara untuk dianalisis
        file_extension = os.path.splitext(file.filename or ".png")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Hitung kapasitas
        lsb = LeastSignificantBit(k_val=k_val)
        max_chars, max_bits, width, height = lsb.calculate_max_message_size(
            temp_file_path)

        max_chars_in_words = number_to_words_id(max_chars)

        # 3. Format angka dengan pemisah ribuan (titik) untuk keterbacaan
        formatted_max_chars = f"{max_chars:,}".replace(',', '.')

        # 4. Buat string 'notes' yang sudah diperbarui
        notes_string = f"Gambar ini dapat menampung hingga {formatted_max_chars} ({max_chars_in_words}) karakter."

        return api_response(data={
            "max_chars": max_chars,
            "max_bits": max_bits,
            "k_val": k_val,
            "notes": notes_string,
            "dimensions": {
                "width": width,
                "height": height
            },
        })

    except Exception as e:
        return api_response(status=False, message="Failed to calculate capacity", error=str(e), status_code=500)
    finally:
        # Selalu hapus file sementara
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    message: str = Form(...,
                        description="Pesan final yang akan disembunyikan"),
    k_val: int = Form(4, ge=1, le=8, description="Number of LSBs to use (1-8)")
):
    """
    Menyisipkan pesan final ke dalam cover image dan memulai background task.
    """
    temp_file_path = None
    try:
        cover_bytes = await file.read()

        # Validasi server-side tetap PENTING sebagai pengaman
        file_extension = os.path.splitext(file.filename or ".png")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(cover_bytes)
            temp_file_path = temp_file.name

        lsb = LeastSignificantBit(k_val=k_val)
        max_chars, _ = lsb.calculate_max_message_size(temp_file_path)

        if len(message) > max_chars:
            error_detail = f"Ukuran pesan ({len(message)} karakter) melebihi kapasitas maksimum gambar ({max_chars} karakter)."
            return api_response(status=False, message="Payload Too Large", error=error_detail, status_code=413)

        # Proses unggah ke S3 dan panggil Celery seperti sebelumnya
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        task = embed_task.delay(
            cover_key=cover_key,
            message=message,  # Langsung gunakan pesan dari input
            k_val=k_val,
            original_filename=cover_name,
            job_id=job_id,
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
    file: UploadFile = File(..., description="Stego image (PNG/JPG/PNG)"),
    original: UploadFile = File(...,
                                description="Original cover image (PNG/JPG/PNG)"),
    k_val: int = Form(
        4, description="Number of LSBs used (must match embedding)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(
            status_code=422, detail="k_val must be between 1 and 8")

    try:
        stego_bytes = await file.read()
        orig_bytes = await original.read()

        stego_name = file.filename or "stego.png"
        orig_name = original.filename or "original.png"

        # Generate unique job_id for tracking
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        # Upload stego and original cover images to S3
        stego_key = upload_bytes_and_get_key(
            prefix,
            f"stego-{stego_name}",
            stego_bytes,
            file.content_type or "image/png",
        )
        orig_key = upload_bytes_and_get_key(
            prefix,
            f"cover-{orig_name}",
            orig_bytes,
            original.content_type or "image/png",
        )

        # Enqueue Celery extract task
        task = extract_task.delay(
            stego_key=stego_key, original_key=orig_key, k_val=k_val)

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "job_id": job_id,
            "stego_key": stego_key,
            "original_key": orig_key,
            "notes": "Use WebSocket or /tasks/{id} until SUCCESS to get message + metrics."
        })

    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )

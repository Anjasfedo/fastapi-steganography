from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from uuid import uuid4
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.steganography.lsb import embed_task, extract_task
import tempfile
import os
from methods.steganography.lsb import LeastSignificantBit # <-- Impor kelas LSB Anda
from methods.preprocess.padding_data import pad_message_to_capacity


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
        max_chars, max_bits = lsb.calculate_max_message_size(temp_file_path)
        
        return api_response(data={
            "max_characters": max_chars,
            "max_bits_payload": max_bits,
            "k_val": k_val,
            "notes": f"Gambar ini dapat menampung hingga {max_chars} karakter."
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
    message: str = Form(..., description="Message to hide"),
    k_val: int = Form(4, ge=1, le=8, description="Number of LSBs to use (1-8)"),
    fill_max_capacity: bool = Query(
        default=False, 
        description="Ulangi pesan untuk mengisi kapasitas maksimum gambar."
    )
):
    temp_file_path = None
    try:
        cover_bytes = await file.read()
        
        # 1. Simpan file sementara untuk menghitung kapasitas
        # Mendapatkan ekstensi file asli untuk file sementara
        file_extension = os.path.splitext(file.filename or ".png")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(cover_bytes)
            temp_file_path = temp_file.name

        # 2. Hitung kapasitas maksimum gambar
        lsb = LeastSignificantBit(k_val=k_val)
        max_chars, _ = lsb.calculate_max_message_size(temp_file_path)
        
        message_to_embed = message

        if fill_max_capacity:
            try:
                # 2. Panggil fungsi helper untuk melakukan padding
                message_to_embed = pad_message_to_capacity(message, max_chars)
            except ValueError as e:
                # 3. Tangkap error jika pesan kosong dan kembalikan respons API
                return api_response(
                    status=False,
                    message="Validation Error",
                    error=str(e),
                    status_code=422
                )

        # 4. Validasi ukuran pesan sebelum mengirim ke task
        if len(message_to_embed) > max_chars:
            error_detail = f"Ukuran pesan ({len(message_to_embed)} karakter) melebihi kapasitas maksimum gambar ({max_chars} karakter) untuk k_val={k_val}."
            return api_response(
                status=False,
                message="Payload Too Large",
                error=error_detail,
                status_code=413  # Payload Too Large
            )

        # Proses unggah ke S3 dan panggil Celery seperti sebelumnya
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        task = embed_task.delay(
            cover_key=cover_key,
            message=message_to_embed, # Gunakan pesan yang sudah diolah
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
        return api_response(
            status=False, 
            message="An unexpected server error occurred", 
            error=str(e),
            status_code=500 # Internal Server Error
        )
    finally:
        # 5. Pastikan file sementara selalu dihapus
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/lsb/extract")
async def lsb_extract(
    file: UploadFile = File(..., description="Stego image (PNG/JPG/PNG)"),
    original: UploadFile = File(..., description="Original cover image (PNG/JPG/PNG)"),
    k_val: int = Form(4, description="Number of LSBs used (must match embedding)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(status_code=422, detail="k_val must be between 1 and 8")

    try:
        stego_bytes = await file.read()
        orig_bytes  = await original.read()

        stego_name = file.filename or "stego.png"
        orig_name  = original.filename or "original.png"

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
        task = extract_task.delay(stego_key=stego_key, original_key=orig_key, k_val=k_val)

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
            status_code=500 # Internal Server Error
        )
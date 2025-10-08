from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from uuid import uuid4
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.experiments.lsb import embed_task as lsb_embed_task, extract_task as lsb_extract_task
from tasks.experiments.eceg_lsb import embed_task as eceg_lsb_embed_task, extract_task as eceg_lsb_extract_task, generate_keys_task as eceg_lsb_generate_keys_task
from tasks.experiments.lzw_lsb import embed_task as lzw_lsb_embed_task, extract_task as lzw_lsb_extract_task
from tasks.experiments.huffman_coding_lsb import embed_task as huffman_coding_lsb_embed_task, extract_task as huffman_coding_lsb_extract_task
from tasks.experiments.eceg_lzw_lsb import generate_keys_task as eceg_lzw_lsb_generate_keys_task, embed_task as eceg_lzw_lsb_embed_task, extract_task as eceg_lzw_lsb_extract_task
from tasks.experiments.eceg_huffman_coding_lsb import generate_keys_task as eceg_huffman_coding_lsb_generate_keys_task, embed_task as eceg_huffman_coding_lsb_embed_task, extract_task as eceg_huffman_coding_lsb_extract_task
from tasks.experiments.lzw_eceg_lsb import generate_keys_task as lzw_eceg_lsb_generate_keys_task, embed_task as lzw_eceg_lsb_embed_task, extract_task as lzw_eceg_lsb_extract_task
from tasks.experiments.huffman_coding_eceg_lsb import generate_keys_task as huffman_coding_eceg_lsb_generate_keys_task, embed_task as huffman_coding_eceg_lsb_embed_task, extract_task as huffman_coding_eceg_lsb_extract_task
import os


class KTPData(BaseModel):
    """KTP data model with validation"""
    NIK: str = Field("1771010101900001", description="Nomor Induk Kependudukan", min_length=16, max_length=16)
    Nama: str = Field("BUDI MARTAMI", description="Nama Lengkap", min_length=3, max_length=100)
    Tempat_Tgl_Lahir: str = Field("BENGKULU, 01-01-1990", alias="Tempat_Tgl_Lahir", description="Contoh: BENGKULU, 01-01-1990", min_length=10, max_length=100)
    Jenis_Kelamin: str = Field("LAKI-LAKI", alias="Jenis_Kelamin", description="LAKI-LAKI atau PEREMPUAN")
    Gol_Darah: str = Field("O", alias="Gol. Darah", description="A, B, AB, atau O")
    Alamat: str = Field("JL. JEND. SUDIRMAN NO. 1", description="Alamat lengkap", min_length=5, max_length=200)
    RT_RW: str = Field("001/001", alias="RT_RW", description="Contoh: 001/002", min_length=5, max_length=10)
    Kel_Desa: str = Field("ANGGUT ATAS", alias="Kel_Desa", description="Nama Kelurahan atau Desa", min_length=3, max_length=100)
    Kecamatan: str = Field("RATU SAMBAN", description="Nama Kecamatan", min_length=3, max_length=100)
    Agama: str = Field("ISLAM", description="Agama", min_length=3, max_length=50)
    Status_Perkawinan: str = Field("BELUM KAWIN", alias="Status_Perkawinan", description="KAWIN/BELUM KAWIN")
    Pekerjaan: str = Field("PELAJAR/MAHASISWA", description="Jenis Pekerjaan", min_length=3, max_length=100)
    Kewarganegaraan: str = Field("WNI", description="Kewarganegaraan", min_length=2, max_length=10)
    Berlaku_Hingga: str = Field("SEUMUR HIDUP", alias="Berlaku_Hingga", description="Berlaku_Hingga", min_length=3, max_length=50)

    @field_validator('NIK')
    @classmethod
    def validate_nik(cls, v):
        if not v.isdigit():
            raise ValueError('NIK must be numeric')
        return v

    @field_validator('Jenis_Kelamin')
    @classmethod
    def validate_jenis_kelamin(cls, v):
        allowed = ['LAKI-LAKI', 'PEREMPUAN']
        if v.upper() not in allowed:
            raise ValueError(f'Jenis Kelamin must be one of: {allowed}')
        return v.upper()

    @field_validator('Gol_Darah')
    @classmethod
    def validate_gol_darah(cls, v):
        allowed = ['A', 'B', 'AB', 'O']
        if v.upper() not in allowed:
            raise ValueError(f'Golongan Darah must be one of: {allowed}')
        return v.upper()

    @field_validator('Status_Perkawinan')
    @classmethod
    def validate_status_perkawinan(cls, v):
        allowed = ['KAWIN', 'BELUM KAWIN']
        if v.upper() not in allowed:
            raise ValueError(f'Status Perkawinan must be one of: {allowed}')
        return v.upper()

    @field_validator('Kewarganegaraan')
    @classmethod
    def validate_kewarganegaraan(cls, v):
        allowed = ['WNI', 'WNA']
        if v.upper() not in allowed:
            raise ValueError(f'Kewarganegaraan must be one of: {allowed}')
        return v.upper()

    @field_validator('RT_RW')
    @classmethod
    def validate_rt_rw(cls, v):
        if '/' not in v:
            raise ValueError('RT_RW format must be: RT/RW')
        return v


router = APIRouter()


@router.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),
    ktp_data: Optional[KTPData] = Form(
        None, description="KTP data as JSON (required when type='ktp')")
):
    """
    Menyisipkan pesan final ke dalam cover image dan memulai background task.
    """
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    temp_file_path = None
    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        # Call task based on input type
        if type == "ktp":
            # Pass KTP data as object
            task = lsb_embed_task.delay(
                cover_key=cover_key,
                k_val=k_val,
                original_filename=cover_name,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            # Pass plaintext directly
            task = lsb_embed_task.delay(
                cover_key=cover_key,
                k_val=k_val,
                original_filename=cover_name,
                max_chars=None,  # Not needed for plaintext
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
    file: UploadFile = File(..., description="Stego image (PNG/JPG/PNG)"),
    original: UploadFile = File(...,
                                description="Original cover image (PNG/JPG/PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
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
        task = lsb_extract_task.delay(
            stego_key=stego_key, original_key=orig_key, k_val=k_val, type=type)

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

# --- Endpoint Embed ECEG+LSB ---


@router.post("/eceg-lsb/generate-keys")
async def eceg_lsb_generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = eceg_lsb_generate_keys_task.apply_async()

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )


@router.post("/eceg-lsb/embed")
async def eceg_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),
    ktp_data: Optional[KTPData] = Form(
        None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png"
        )

        if type == "ktp":
            task = eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key, max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key, max_chars=None,
                plaintext=plaintext
            )

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-lsb/extract")
async def eceg_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    private_key: int = Form(..., description="Kunci privat ECEG (integer)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"
        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"

        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png"
        )

        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png"
        )

        task = eceg_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB extract", error=str(e), status_code=500)


@router.post("/lzw-lsb/embed")
async def lzw_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = lzw_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = lzw_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                max_chars=None,
                plaintext=plaintext
            )

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-LSB embed", error=str(e), status_code=500)

# --- Endpoint Extract LZW+LSB ---


@router.post("/lzw-lsb/extract")
async def lzw_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    bit_width: int = Form(
        ...,
        description="Lebar bit (misal: 12) yang digunakan oleh LZW untuk dekompresi, diperoleh dari hasil kompresi."
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        # ... (logika upload stego_file dan original_file untuk mendapatkan stego_key dan original_key)
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"
        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"

        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")

        task = lzw_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, bit_width=bit_width, type=type)

        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-LSB extract", error=str(e), status_code=500)


@router.post("/huffman-coding-lsb/embed")
async def huffman_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = huffman_coding_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = huffman_coding_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                max_chars=None,
                plaintext=plaintext
            )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-LSB embed", error=str(e), status_code=500)


@router.post("/huffman-coding-lsb/extract")
async def huffman_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
    codebook_file: UploadFile = File(...,
                                     description="File huffman codebook (.json)"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        # ... (logika upload stego_file dan original_file untuk mendapatkan stego_key dan original_key)
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"

        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")
        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = huffman_coding_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, codebook_key=codebook_key, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-LSB extract", error=str(e), status_code=500)


@router.post("/eceg-lzw-lsb/generate-keys")
async def eceg_huffman_coding_lsb_generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = eceg_huffman_coding_lsb_generate_keys_task.apply_async()

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )


@router.post("/eceg-lzw-lsb/embed")
async def eceg_lzw_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(4, ge=1, le=8),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = eceg_lzw_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = eceg_lzw_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=None,
                plaintext=plaintext
            )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LZW-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-lzw-lsb/extract")
async def eceg_lzw_lsb_extract(
    stego_file: UploadFile = File(
        ...,
        description="File gambar stego (format PNG) yang berisi data tersembunyi."
    ),
    original_file: UploadFile = File(
        ...,
        description="File gambar cover asli (format PNG) untuk perbandingan metrik kualitas."
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
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"

        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")

        task = eceg_lzw_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, bit_width=bit_width, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LZW-LSB extract", error=str(e), status_code=500)


@router.post("/eceg-huffman-coding-lsb/generate-keys")
async def eceg_lzw_lsb_generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = eceg_lzw_lsb_generate_keys_task.apply_async()

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )


@router.post("/eceg-huffman-coding-lsb/embed")
async def eceg_huffman_lsb_embed(
    file: UploadFile = File(...),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = eceg_huffman_coding_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = eceg_huffman_coding_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=None,
                plaintext=plaintext
            )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-Huffman-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-huffman-coding-lsb/extract")
async def eceg_huffman_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
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
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"

        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")
        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = eceg_huffman_coding_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, codebook_key=codebook_key, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-Huffman-LSB extract", error=str(e), status_code=500)


@router.post("/lzw-eceg-lsb/generate-keys")
async def lzw_eceg_lsb_generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = lzw_eceg_lsb_generate_keys_task.apply_async()

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )


@router.post("/lzw-eceg-lsb/embed")
async def lzw_eceg_lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = lzw_eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = lzw_eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=None,
                plaintext=plaintext
            )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/lzw-eceg-lsb/extract")
async def lzw_eceg_lsb_extract(
    stego_file: UploadFile = File(
        ...,
        description="File gambar stego (format PNG) yang berisi data tersembunyi."
    ),
    original_file: UploadFile = File(
        ...,
        description="File gambar cover asli (format PNG) untuk perbandingan metrik kualitas."
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
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"

        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")

        task = lzw_eceg_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val,
            private_key=private_key, bit_width=bit_width, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start LZW-ECEG-LSB extract", error=str(e), status_code=500)


@router.post("/huffman-coding-eceg-lsb/generate-keys")
async def lzw_eceg_lsb_generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = huffman_coding_eceg_lsb_generate_keys_task.apply_async()

        return api_response(data={
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
        })
    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )


@router.post("/huffman-coding-eceg-lsb/embed")
async def huffman_eceg_lsb_embed(
    file: UploadFile = File(...),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text"),
    k_val: int = Form(
        4,
        ge=1,
        le=8,
        description="Jumlah bit LSB yang digunakan (1-8). Harus sama dengan nilai saat proses embed."
    ),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: Optional[int] = Form(
        None, description="Opsional. Kapasitas karakter maksimum untuk padding. Jika tidak diisi, pesan tidak akan di-padding."),
    plaintext: Optional[str] = Form(
        None, description="Plain text message (required when type='plain')"),

  ktp_data: Optional[KTPData] = Form(None, description="KTP data as JSON (required when type='ktp')")
):
    # Validate input type
    if type not in ["ktp", "plain"]:
        return api_response(status=False, message="Invalid type. Must be 'ktp' or 'plain'", status_code=400)

    # Validate required fields based on type
    if type == "plain" and not plaintext:
        return api_response(status=False, message="plaintext is required when type='plain'", status_code=400)

    if type == "ktp" and not ktp_data:
        return api_response(status=False, message="ktp_data is required when type='ktp'", status_code=400)

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"
        job_id = uuid4().hex
        prefix = f"experiments/{job_id}"
        cover_key = upload_bytes_and_get_key(
            prefix, f"cover-{cover_name}", cover_bytes, file.content_type or "image/png")

        if type == "ktp":
            task = huffman_coding_eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=max_chars,
                ktp_data=ktp_data.model_dump()
            )
        else:
            task = huffman_coding_eceg_lsb_embed_task.delay(
                cover_key=cover_key, k_val=k_val, original_filename=cover_name,
                public_key=public_key,
                max_chars=None,
                plaintext=plaintext
            )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/huffman-coding-eceg-lsb/extract")
async def huffman_eceg_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
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
    ),
    type: str = Query("ktp", description="Input type: 'ktp' for KTP data or 'plain' for plain text")
):
    try:
        stego_bytes = await stego_file.read()
        stego_name = stego_file.filename or "stego.png"

        orig_bytes = await original_file.read()
        orig_name = original_file.filename or "original.png"

        codebook_bytes = await codebook_file.read()
        codebook_name = codebook_file.filename or "codebook.json"

        job_id = uuid4().hex
        prefix = f"experiments/{job_id}/extract"
        stego_key = upload_bytes_and_get_key(
            prefix, f"stego-{stego_name}", stego_bytes, stego_file.content_type or "image/png")
        original_key = upload_bytes_and_get_key(
            prefix, f"cover-{orig_name}", orig_bytes, original_file.content_type or "image/png")
        codebook_key = upload_bytes_and_get_key(
            prefix, f"codebook-{codebook_name}", codebook_bytes, codebook_file.content_type or "application/json"
        )

        task = eceg_huffman_coding_lsb_extract_task.delay(
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key, codebook_key=codebook_key, type=type
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start Huffman-ECEG-LSB extract", error=str(e), status_code=500)

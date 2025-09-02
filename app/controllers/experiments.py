from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from uuid import uuid4
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.experiments.lsb import embed_task as lsb_embed_task, extract_task as lsb_extract_task
from tasks.experiments.eceg_lsb import embed_task as eceg_lsb_embed_task, extract_task as eceg_lsb_extract_task, generate_keys_task as eceg_lsb_generate_keys_task
import os


router = APIRouter()


@router.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG)"),
    k_val: int = Form(
        4, ge=1, le=8, description="Number of LSBs to use (1-8)"),
    max_chars: int = Form(
        ..., description="Kapasitas karakter maksimum untuk padding, didapat dari endpoint /calculate-capacity."),

    NIK: str = Form("1771010101900001",
                    description="Nomor Induk Kependudukan"),
    Nama: str = Form("BUDI MARTAMI", description="Nama Lengkap"),
    Tempat_Tgl_Lahir: str = Form(
        "BENGKULU, 01-01-1990", alias="Tempat/Tgl Lahir", description="Contoh: BENGKULU, 01-01-1990"),
    Jenis_Kelamin: str = Form(
        "LAKI-LAKI", alias="Jenis Kelamin", description="LAKI-LAKI atau PEREMPUAN"),
    Gol_Darah: str = Form("O", alias="Gol. Darah",
                          description="A, B, AB, atau O"),
    Alamat: str = Form("JL. JEND. SUDIRMAN NO. 1",
                       description="Alamat lengkap"),
    RT_RW: str = Form("001/001", alias="RT/RW", description="Contoh: 001/002"),
    Kel_Desa: str = Form("ANGGUT ATAS", alias="Kel/Desa",
                         description="Nama Kelurahan atau Desa"),
    Kecamatan: str = Form("RATU SAMBAN", description="Nama Kecamatan"),
    Agama: str = Form("ISLAM", description="Agama"),
    Status_Perkawinan: str = Form(
        "BELUM KAWIN", alias="Status Perkawinan", description="KAWIN/BELUM KAWIN"),
    Pekerjaan: str = Form("PELAJAR/MAHASISWA", description="Jenis Pekerjaan"),
    Kewarganegaraan: str = Form("WNI", description="Kewarganegaraan"),
    Berlaku_Hingga: str = Form(
        "SEUMUR HIDUP", alias="Berlaku Hingga", description="Berlaku Hingga")
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

        # 2. Panggil task dengan semua field KTP sebagai keyword arguments
        task = lsb_embed_task.delay(
            cover_key=cover_key,
            k_val=k_val,
            original_filename=cover_name,
            max_chars=max_chars,
            NIK=NIK,
            Nama=Nama,
            Tempat_Tgl_Lahir=Tempat_Tgl_Lahir,
            Jenis_Kelamin=Jenis_Kelamin,
            Gol_Darah=Gol_Darah,
            Alamat=Alamat,
            RT_RW=RT_RW,
            Kel_Desa=Kel_Desa,
            Kecamatan=Kecamatan,
            Agama=Agama,
            Status_Perkawinan=Status_Perkawinan,
            Pekerjaan=Pekerjaan,
            Kewarganegaraan=Kewarganegaraan,
            Berlaku_Hingga=Berlaku_Hingga
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
        task = lsb_extract_task.delay(
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

# --- Endpoint Embed ECEG+LSB ---


@router.post("/eceg-lsb/generate-keys")
async def generate_keys():
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
    k_val: int = Form(4, ge=1, le=8),
    public_key: int = Form(..., description="Kunci publik ECEG (integer)"),
    max_chars: int = Form(
        ..., description="Kapasitas karakter maksimum untuk padding, didapat dari endpoint /calculate-capacity."),

    NIK: str = Form("1771010101900001",
                    description="Nomor Induk Kependudukan"),
    Nama: str = Form("BUDI MARTAMI", description="Nama Lengkap"),
    Tempat_Tgl_Lahir: str = Form(
        "BENGKULU, 01-01-1990", alias="Tempat/Tgl Lahir", description="Contoh: BENGKULU, 01-01-1990"),
    Jenis_Kelamin: str = Form(
        "LAKI-LAKI", alias="Jenis Kelamin", description="LAKI-LAKI atau PEREMPUAN"),
    Gol_Darah: str = Form("O", alias="Gol. Darah",
                          description="A, B, AB, atau O"),
    Alamat: str = Form("JL. JEND. SUDIRMAN NO. 1",
                       description="Alamat lengkap"),
    RT_RW: str = Form("001/001", alias="RT/RW", description="Contoh: 001/002"),
    Kel_Desa: str = Form("ANGGUT ATAS", alias="Kel/Desa",
                         description="Nama Kelurahan atau Desa"),
    Kecamatan: str = Form("RATU SAMBAN", description="Nama Kecamatan"),
    Agama: str = Form("ISLAM", description="Agama"),
    Status_Perkawinan: str = Form(
        "BELUM KAWIN", alias="Status Perkawinan", description="KAWIN/BELUM KAWIN"),
    Pekerjaan: str = Form("PELAJAR/MAHASISWA", description="Jenis Pekerjaan"),
    Kewarganegaraan: str = Form("WNI", description="Kewarganegaraan"),
    Berlaku_Hingga: str = Form(
        "SEUMUR HIDUP", alias="Berlaku Hingga", description="Berlaku Hingga")
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
            cover_key=cover_key, k_val=k_val, original_filename=cover_name, public_key=public_key, max_chars=max_chars,
            NIK=NIK, Nama=Nama, Tempat_Tgl_Lahir=Tempat_Tgl_Lahir, Jenis_Kelamin=Jenis_Kelamin,
            Gol_Darah=Gol_Darah, Alamat=Alamat, RT_RW=RT_RW, Kel_Desa=Kel_Desa, Kecamatan=Kecamatan,
            Agama=Agama, Status_Perkawinan=Status_Perkawinan, Pekerjaan=Pekerjaan,
            Kewarganegaraan=Kewarganegaraan, Berlaku_Hingga=Berlaku_Hingga
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB embed", error=str(e), status_code=500)


@router.post("/eceg-lsb/extract")
async def eceg_lsb_extract(
    stego_file: UploadFile = File(..., description="File stego image (PNG)"),
    original_file: UploadFile = File(...,
                                     description="File cover image asli (PNG)"),
    k_val: int = Form(..., ge=1, le=8),
    private_key: int = Form(..., description="Kunci privat ECEG (integer)")
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
            stego_key=stego_key, original_key=original_key, k_val=k_val, private_key=private_key
        )
        return api_response(data={"task_id": task.id, "status": "PENDING"})
    except Exception as e:
        return api_response(status=False, message="Failed to start ECEG-LSB extract", error=str(e), status_code=500)

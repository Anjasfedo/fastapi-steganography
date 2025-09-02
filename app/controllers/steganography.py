from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from uuid import uuid4
from helpers.response_wrapper import api_response
from s3.utils import upload_bytes_and_get_key
from tasks.steganography.lsb import embed_task, extract_task

router = APIRouter()

@router.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG/JPG)"),
    message: str = Form(..., description="Message to hide"),
    k_val: int = Form(4, description="Number of LSBs to use (1-8)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(status_code=422, detail="k_val must be between 1 and 8")

    try:
        cover_bytes = await file.read()
        cover_name = file.filename or "cover.png"

        # Generate unique job_id for tracking
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        # Upload cover image to S3
        cover_key = upload_bytes_and_get_key(
            prefix,
            f"cover-{cover_name}",
            cover_bytes,
            file.content_type or "image/png",
        )

        # Enqueue Celery embed task with the uploaded cover image and message
        task = embed_task.delay(
            cover_key=cover_key,
            message=message,
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
            "notes": "Use the WebSocket or /tasks/{id} to get the stego key & URL when ready."
        })

    except Exception as e:
        return api_response(status=False, message="Embedding failed", error=str(e))


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
        return api_response(status=False, message="Extraction failed", error=str(e))
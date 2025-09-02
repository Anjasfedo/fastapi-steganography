from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from steganography.lsb import LeastSignificantBit
from helpers.message_bit import message_to_bit, bit_to_message
import os
import tempfile
from fastapi.responses import JSONResponse
from uuid import uuid4
from s3.main import PRESIGN_TTL, S3_BUCKET
from s3.utils import upload_bytes_and_get_key
from steganography.metrics import StegoMetrics
from tasks.main import extract_task, embed_task
from celery_app import celery

app = FastAPI()


@app.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG/JPG)"),
    message: str = Form(..., description="Message to hide"),
    k_val: int = Form(4, description="Number of LSBs to use (1-8)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(status_code=422, detail="k_val must be between 1 and 8")

    try:
        cover_bytes = await file.read()
        cover_name  = (file.filename or "cover.png").rsplit("/", 1)[-1]

        # 1) Upload cover to S3 so worker can read it
        cover_key = upload_bytes_and_get_key(
            "stego/cover",
            cover_name,
            cover_bytes,
            file.content_type or "image/png",
        )

        # 2) Enqueue Celery embed task
        task = embed_task.delay(
            cover_key=cover_key,
            message=message,
            k_val=k_val,
            original_filename=cover_name,   # for nicer stego filename
        )

        # 3) Immediate response with task id
        return JSONResponse({
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "cover_key": cover_key,
            "notes": "Poll the status URL until state is SUCCESS to get the stego S3 key and URL."
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/lsb/extract")
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

        # Upload both to S3 so workers can read them
        stego_name = (file.filename or "stego.png").rsplit("/", 1)[-1]
        orig_name  = (original.filename or "original.png").rsplit("/", 1)[-1]

        stego_key = upload_bytes_and_get_key("stego/incoming", stego_name, stego_bytes, file.content_type or "image/png")
        orig_key  = upload_bytes_and_get_key("stego/original",  orig_name,  orig_bytes,  original.content_type or "image/png")

        # Enqueue Celery task
        task = extract_task.delay(stego_key=stego_key, original_key=orig_key, k_val=k_val)

        return JSONResponse({
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "stego_key": stego_key,
            "original_key": orig_key,
            "notes": "Poll the status URL until state is SUCCESS to retrieve message + metrics."
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    result = celery.AsyncResult(task_id)
    state = result.state  # PENDING, STARTED, RETRY, FAILURE, SUCCESS
    payload = {"task_id": task_id, "status": state}

    if state == "SUCCESS":
        payload["result"] = result.get()  # contains message + metrics
    elif state == "FAILURE":
        payload["error"] = str(result.info)  # exception info

    return JSONResponse(payload)
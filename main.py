from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from helpers.message_bit import message_to_bit, bit_to_message
from fastapi.responses import JSONResponse
from uuid import uuid4
from s3.main import PRESIGN_TTL, S3_BUCKET
from s3.utils import upload_bytes_and_get_key, safe_name
from steganography.metrics import StegoMetrics
from tasks.main import extract_task, embed_task
from celery_app import celery
import asyncio


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
        cover_name  = safe_name(file.filename or "cover.png")

        # Use a single job_id for all artifacts of this request
        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        # 1) Upload cover to S3 so worker can read it
        cover_key = upload_bytes_and_get_key(
            prefix,
            f"cover-{cover_name}",
            cover_bytes,
            file.content_type or "image/png",
        )

        # 2) Enqueue Celery embed task (pass job_id so worker can keep same prefix)
        task = embed_task.delay(
            cover_key=cover_key,
            message=message,
            k_val=k_val,
            original_filename=cover_name,
            job_id=job_id,
        )

        # 3) Immediate response with task id
        return JSONResponse({
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "job_id": job_id,
            "cover_key": cover_key,
            "notes": "Use the WebSocket or /tasks/{id} to get the stego key & URL when ready."
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

        stego_name = safe_name(file.filename or "stego.png")
        orig_name  = safe_name(original.filename or "original.png")

        job_id = uuid4().hex
        prefix = f"steganography/{job_id}"

        # Store both under the same job folder with required names
        stego_key = upload_bytes_and_get_key(
            prefix,
            f"stego-{stego_name}",
            stego_bytes,
            file.content_type or "image/png",
        )
        orig_key  = upload_bytes_and_get_key(
            prefix,
            f"cover-{orig_name}",
            orig_bytes,
            original.content_type or "image/png",
        )

        task = extract_task.delay(stego_key=stego_key, original_key=orig_key, k_val=k_val)

        return JSONResponse({
            "task_id": task.id,
            "status": "PENDING",
            "check": f"/tasks/{task.id}",
            "job_id": job_id,
            "stego_key": stego_key,
            "original_key": orig_key,
            "notes": "Use WebSocket or /tasks/{id} until SUCCESS to get message + metrics."
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    result = celery.AsyncResult(task_id)
    state = result.state
    payload = {"task_id": task_id, "status": state}

    if state == "SUCCESS":
        payload["result"] = result.get()
    elif state == "FAILURE":
        payload["error"] = str(result.info)

    return JSONResponse(payload)


@app.websocket("/ws/tasks/{task_id}")
async def task_status_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        result = celery.AsyncResult(task_id)
        await websocket.send_json({
            "task_id": task_id,
            "status": result.state,
            "progress": result.info.get("progress") if isinstance(result.info, dict) else None,
        })

        last_state = None
        last_progress = None

        while True:
            await asyncio.sleep(1.0)

            ar = celery.AsyncResult(task_id)
            state = ar.state
            info = ar.info if isinstance(ar.info, dict) else {}
            progress = info.get("progress") if isinstance(info, dict) else None

            if state != last_state or progress != last_progress:
                payload = {"task_id": task_id, "status": state}
                if progress is not None:
                    payload["progress"] = progress

                if state == "SUCCESS":
                    payload["result"] = ar.get()
                    await websocket.send_json(payload)
                    await websocket.close(code=1000)
                    break
                elif state == "FAILURE":
                    payload["error"] = str(ar.info)
                    await websocket.send_json(payload)
                    await websocket.close(code=1011)
                    break
                else:
                    await websocket.send_json(payload)

                last_state, last_progress = state, progress

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_json({"task_id": task_id, "status": "ERROR", "error": str(e)})
        finally:
            await websocket.close(code=1011)
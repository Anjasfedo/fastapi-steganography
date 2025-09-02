from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from helpers.message_bit import message_to_bit, bit_to_message
from fastapi.responses import JSONResponse
from main_celery import celery
import asyncio
from helpers.response_wrapper import api_response

router = APIRouter()

@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    Retrieves the status and result of a Celery task.
    """
    result = celery.AsyncResult(task_id)
    state = result.state

    response_data = {
        "task_id": task_id,
        "status": state
    }

    if state == "FAILURE":
        # Jika task gagal, kita ambil informasi error-nya.
        # result.info berisi exception object, dan result.traceback berisi jejak error.
        response_data["error"] = {
            "type": type(result.info).__name__,
            "message": str(result.info),
            "traceback": result.traceback,
        }
    elif state == "SUCCESS":
        # Jika berhasil, kita panggil .get() untuk mengambil hasilnya.
        # Aman untuk dipanggil di sini karena kita sudah tahu statusnya SUCCESS.
        response_data["result"] = result.get()
    elif state != "PENDING":
        # Untuk status lain (misalnya STARTED, RETRY), 
        # result.info sering kali berisi metadata kustom (seperti progress).
        response_data["info"] = result.info

    return api_response(data=response_data)



@router.websocket("/{task_id}/ws")
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
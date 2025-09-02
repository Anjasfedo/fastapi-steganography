from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from helpers.message_bit import message_to_bit, bit_to_message
from fastapi.responses import JSONResponse
from celery_app import celery
import asyncio
from helpers.response_wrapper import api_response

router = APIRouter()

@router.get("/{task_id}")
async def get_task_status(task_id: str):
    result = celery.AsyncResult(task_id)
    print(result.get())
    state = result.state
    payload = {"task_id": task_id, "status": state}

    if state == "SUCCESS":
        # Include the actual result (encrypted message or decrypted message)
        payload["result"] = result.get()  # This fetches the task result
    elif state == "FAILURE":
        payload["error"] = str(result.info)  # Failure details

    return api_response(data=payload)



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
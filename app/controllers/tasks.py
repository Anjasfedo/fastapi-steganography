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



async def task_status_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        # --- Kirim status awal dengan lebih lengkap ---
        result = celery.AsyncResult(task_id)
        initial_info = result.info if isinstance(result.info, dict) else {}
        await websocket.send_json({
            "task_id": task_id,
            "status": result.state,
            **initial_info  # ## <<< PERUBAHAN 1: Kirim 'info' awal
        })

        last_state = result.state
        last_info = initial_info  # ## <<< PERUBAHAN 2: Lacak seluruh 'info', bukan hanya progress

        while True:
            await asyncio.sleep(1.0) # Polling setiap 1 detik

            ar = celery.AsyncResult(task_id)
            state = ar.state
            info = ar.info if isinstance(ar.info, dict) else {}

            # ## <<< PERUBAHAN 3: Deteksi perubahan pada state ATAU info
            if state != last_state or info != last_info:
                # Siapkan payload dasar
                payload = {"task_id": task_id, "status": state}
                # ## <<< PERUBAHAN 4: Gabungkan semua data dari 'info'
                payload.update(info) 

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
                    # Kirim pembaruan progress/stage
                    await websocket.send_json(payload)

                # Perbarui state terakhir yang diketahui
                last_state, last_info = state, info

    except WebSocketDisconnect:
        # Klien menutup koneksi, tidak perlu melakukan apa-apa
        return
    except Exception as e:
        # Tangani error tak terduga
        try:
            await websocket.send_json({"task_id": task_id, "status": "ERROR", "error": str(e)})
        finally:
            await websocket.close(code=1011)
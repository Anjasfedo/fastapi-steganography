from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tasks.cryptography.eceg import encrypt_task, decrypt_task, generate_keys_task
from helpers.response_wrapper import api_response

router = APIRouter()

class EncryptionRequest(BaseModel):
    message: str
    public_key: int

class DecryptionRequest(BaseModel):
    ciphertext: str
    private_key: int

@router.post("/generate-keys")
async def generate_keys():
    try:
        # Enqueue Celery generate keys task
        task = generate_keys_task.apply_async()

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
            status_code=500 # Internal Server Error
        )

@router.post("/encrypt")
async def encrypt_message(request: EncryptionRequest):
    try:
        # Enqueue Celery encrypt task
        task = encrypt_task.delay(message=request.message, public_key=request.public_key)

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
            status_code=500 # Internal Server Error
        )

@router.post("/decrypt")
async def decrypt_message(request: DecryptionRequest):
    try:
        # Enqueue Celery decrypt task
        task = decrypt_task.delay(ciphertext=request.ciphertext, private_key=request.private_key)

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
            status_code=500 # Internal Server Error
        )

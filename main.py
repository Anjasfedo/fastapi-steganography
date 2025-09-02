from fastapi import FastAPI
from app.controllers.cryptography import router as cryptography_router
from app.controllers.steganography import router as steganography_router
from app.controllers.tasks import router as tasks_router

app = FastAPI()

app.include_router(cryptography_router, prefix='/api/v1/cryptography', tags=["Cryptography"])
app.include_router(steganography_router, prefix='/api/v1/steganography', tags=["Steganography"])
app.include_router(tasks_router, prefix='/api/v1/tasks', tags=["Tasks"])


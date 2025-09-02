from fastapi import FastAPI
from app.controllers.cryptography import router as cryptography_router
from app.controllers.steganography import router as steganography_router
from app.controllers.lossless_compression import router as lossless_compression_router
from app.controllers.ktp_generator import router as ktp_router
from app.controllers.tasks import router as tasks_router
from app.controllers.preprocess import router as preprocess_router
from app.controllers.experiments import router as experiments_router


app = FastAPI()

app.include_router(experiments_router, prefix='/api/v1/experiments', tags=["Experiments"])
app.include_router(cryptography_router, prefix='/api/v1/cryptography', tags=["Cryptography"])
app.include_router(steganography_router, prefix='/api/v1/steganography', tags=["Steganography"])
app.include_router(lossless_compression_router, prefix='/api/v1/lossless-compression', tags=["Lossless Compression"])
app.include_router(preprocess_router, prefix='/api/v1/preprocess', tags=["Preprocessing"])
app.include_router(ktp_router, prefix='/api/v1/ktp', tags=["KTP Tools"])

app.include_router(tasks_router, prefix='/api/v1/tasks', tags=["Tasks"])


# celery_app.py
import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "stego",
    broker=REDIS_URL,
    backend=REDIS_URL,  # store results in Redis so API can fetch them
)

celery.conf.imports = (
    "tasks.steganography.lsb", 
    "tasks.cryptography.eceg", 
    "tasks.lossless_compression.lzw",
    "tasks.lossless_compression.huffman_coding",
    
    "tasks.experiments.lsb",
    "tasks.experiments.eceg_lsb",
    )

# Reasonable defaults
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
)
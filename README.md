fastapi dev main.py
fastapi dev main.py --port 5000
source venv/bin/activate
uvicorn main:app --reload --port 5000
celery -A celery_app.celery worker --loglevel=INFO -Q celery

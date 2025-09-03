`fastapi dev main.py --port 5000`
`source venv/bin/activate`
`uvicorn main:app --reload --port 5000`
`celery -A main_celery.celery worker --loglevel=INFO -Q celery`
```
services:
  api:
    build: .
    command: uvicorn main:app --host 0.0.0.0 --port 5000 --reload
    volumes:
      - .:/app
    ports:
      - "5000:5000"
    env_file:
      - .env

  worker:
    build: .
    command: celery -A main_celery.celery worker --loglevel=INFO
    volumes:
      - .:/app
    env_file:
      - .env
```

```
sudo docker build -t stego-api-image .
```

```
sudo docker run -d -p 5000:5000 --name stego-app-container --env-file .env -v "$(pwd):/app" stego-api-image
```

```
sudo docker stop stego-app-container
```

```
sudo docker rm stego-app-container
```
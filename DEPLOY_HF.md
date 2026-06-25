# Deploy to Hugging Face Spaces (Free Tier)

Step-by-step guide to deploy this FastAPI steganography service to a Hugging Face Docker Space.

> **Architecture on HF:** One Docker container running `supervisord`, which boots **redis** + **uvicorn** (FastAPI on port 7860) + **celery** worker. Storage is external **Cloudflare R2** (S3-compatible).

---

## Prerequisites

- A Hugging Face account: <https://huggingface.co>
- A Cloudflare R2 bucket (already created: `steganography`, APAC) with an API token
- Git installed locally

---

## 1. Create the Space

1. Go to <https://huggingface.co> → click **+** (top-right) → **New Space**
2. **Owner**: your account
3. **Space name**: e.g. `steganography-api`
4. **SDK**: select **Docker** → **Blank** template
5. **Hardware**: `CPU basic` (free)
6. **Visibility**: `Public` (required for free tier)
7. Click **Create Space**

You now have a git repo at:

```
https://huggingface.co/spaces/<your-username>/steganography-api
```

---

## 2. Set Secrets (do this BEFORE the first push)

Space → **Settings** → **Variables and secrets** → add each as a **Secret** (not a public variable):

| Key | Value |
|-----|-------|
| `S3_ENDPOINT` | `https://12fffe880a74c98d38b84c79fd7de03e.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` | *(your **rotated** R2 access key)* |
| `S3_SECRET_KEY` | *(your **rotated** R2 secret key)* |
| `S3_BUCKET` | `steganography` |
| `S3_REGION` | `auto` |
| `S3_PRESIGN_TTL` | `3600` |
| `REDIS_URL` | `redis://localhost:6379/0` |

> ⚠️ **Rotate your R2 token first.** Any key previously shared in plain text must be considered compromised. Generate a fresh R2 API token in Cloudflare and use that here.
>
> The local `.env` file is **not** pushed (it is git-ignored). That is why these values must be set as Space Secrets instead.

---

## 3. Push the Code

The HF Space is a git repo. Add it as a remote and push.

```bash
git remote add hf https://huggingface.co/spaces/<your-username>/steganography-api
git add -A
git commit -m "deploy: HF Spaces docker config"
git push hf main
```

**Authentication when prompted:**
- Username = your HF username
- Password = an **HF access token** with **write** scope
  (huggingface.co → Settings → Access Tokens → New token → role: `write`)

---

## 4. Watch the Build

- Open the Space **Logs** tab
- Docker build runs (~3–6 min — image includes OpenCV / scikit-image)
- `supervisord` then starts: **redis** → **uvicorn (port 7860)** → **celery worker**
- When status turns green **Running**, the app is live

---

## 5. Test the Live App

- Swagger UI: `https://<your-username>-steganography-api.hf.space/docs`
- Example flow:
  1. `POST /api/v1/steganography/lsb/embed` → returns a `task_id`
  2. Poll `GET /api/v1/tasks/{task_id}` until `SUCCESS`
  3. Result contains the stego image URL (presigned R2 link)
- WebSocket progress: `wss://<your-username>-steganography-api.hf.space/api/v1/tasks/{task_id}/ws`

---

## Notes & Gotchas

- 🟡 **Cold starts:** the free Space sleeps after ~48h idle. Next request triggers a ~1–2 min cold start.
- 🟡 **Ephemeral state:** in-memory redis + container disk reset on restart → any in-flight task is lost. Fine for demos; persistent results live in R2.
- 🟡 **First push is large** (repo + history). If it stalls, just retry.
- 🔴 **Never commit `.env`.** It is git-ignored (and in `.dockerignore`) — keep it that way.
- 🟢 WebSockets are supported on HF Spaces (the upgrade handshake works).

---

## What Was Changed for Deployment

| File | Change |
|------|--------|
| `supervisord.conf` | Added `redis` program; FastAPI port `5000` → `7860` |
| `Dockerfile` | Installs `redis-server`; `EXPOSE 7860`; fixed supervisord config path |
| `main.py` | CORS `allow_credentials` → `False` (required with wildcard origin) |
| `s3/main.py` | Added `region_name` (defaults to `auto` for R2) |
| `README.md` | Prepended HF Spaces YAML frontmatter (`sdk: docker`, `app_port: 7860`) |
| `.dockerignore` | Excludes `.env`, `.git`, `.codegraph` from the image |

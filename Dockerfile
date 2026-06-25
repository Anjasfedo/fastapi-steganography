# Gunakan base image python standar yang lebih lengkap
FROM python:3.12

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# --- PERBAIKAN UTAMA DI SINI ---
# Install supervisor DAN dependensi sistem yang dibutuhkan oleh OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    redis-server \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set direktori kerja
WORKDIR /app

# Install dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Salin semua kode proyek
COPY . .

# Salin file konfigurasi supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port FastAPI (HF Spaces requires 7860)
EXPOSE 7860

# Perintah default untuk menjalankan supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
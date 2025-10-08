# Steganography API

A comprehensive steganography API with various embedding and extraction techniques including LSB, ECEG, LZW compression, and Huffman coding.

## 📝 Changelog - `vibing` Branch

### 🔧 **Recent Changes**

#### **1. KTP Generator Improvements**
- **Fixed JSON Response Bug**: Resolved `'list' object has no attribute 'get'` error in target-based KTP generation
- **Simplified Output Format**: Removed `output_format` parameter from KTP generator endpoints - now always returns merged format
- **Enhanced Error Handling**: Improved serialization logic for target-based generation

#### **2. Standardized Extract Endpoint Parameters**
- **Consistent Parameter Naming**: All extract endpoints now use standardized parameter names:
  - `stego_image` (was `stego_file`, `file`, etc.)
  - `original_image` (was `original_file`, `original`, etc.)
- **Updated Endpoints**:
  - `/lsb/extract`
  - `/eceg-lsb/extract`
  - `/lzw-lsb/extract`
  - `/huffman-coding-lsb/extract`
  - `/eceg-lzw-lsb/extract`
  - `/eceg-huffman-coding-lsb/extract`
  - `/lzw-eceg-lsb/extract`
  - `/huffman-coding-eceg-lsb/extract`

#### **3. Enhanced WebSocket Metadata Support**
- **Complete Metadata Forwarding**: WebSocket now returns all metadata sent by tasks via `update_state()`
- **Better Progress Tracking**: Includes processing stages, progress percentages, and custom metadata
- **Example Response**:
  ```json
  {
    "task_id": "abc123",
    "status": "STARTED",
    "stage": "Processing Plaintext",
    "progress": 25
  }
  ```

#### **4. Files Modified**
- `app/controllers/ktp_generator.py` - Fixed KTP generation bugs and simplified output format
- `fakers/main.py` - Fixed merge_ktp_data method to properly handle dictionary serialization
- `app/controllers/experiments.py` - Standardized all extract endpoint parameter names
- `app/controllers/tasks.py` - Enhanced WebSocket to forward complete task metadata

## 🚀 Quick Start
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
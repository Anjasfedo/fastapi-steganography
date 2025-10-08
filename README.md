# Steganography API

A comprehensive steganography API with various embedding and extraction techniques including LSB, ECEG, LZW compression, and Huffman coding.

## 📝 Changelog - `vibing` Branch

### 🔧 **Recent Major Changes**

#### **1. KTP Generator Improvements**
- **Fixed JSON Response Bug**: Resolved `'list' object has no attribute 'get'` error in target-based KTP generation
- **Simplified Output Format**: Removed `output_format` parameter - now always returns merged format
- **Parameter Simplification**: Removed unused `max_chars` parameter, now only uses `max_bits` for target-based generation
- **Enhanced Error Handling**: Improved serialization logic for target-based generation

#### **2. ECEG Workflow Simplification**
- **Internal Key Generation**: ECEG embed tasks now generate key pairs internally instead of requiring separate key generation
- **Removed Key Generation Endpoints**: Eliminated 5 separate key generation endpoints for cleaner API
- **Parameter Cleanup**: Removed `public_key` and `max_chars` parameters from all ECEG embed endpoints
- **Standardized Return Values**: All embed tasks now return `stego_url` instead of `url` and include generated keys

#### **3. Standardized Extract Endpoint Parameters**
- **Consistent Parameter Naming**: All extract endpoints now use standardized parameter names:
  - `stego_image` (was `stego_file`, `file`, etc.)
  - `original_image` (was `original_file`, `original`, etc.)
- **Updated Endpoints**: All 8 extract endpoints standardized

#### **4. Enhanced WebSocket Metadata Support**
- **Complete Metadata Forwarding**: WebSocket now returns all metadata sent by tasks via `update_state()`
- **Better Progress Tracking**: Includes processing stages, progress percentages, and custom metadata
- **Real-time Updates**: Enhanced task monitoring with detailed progress information

#### **5. Code Cleanup**
- **Removed .strip() Calls**: Eliminated unnecessary .strip() operations from all extract tasks
- **Import Cleanup**: Removed unused imports after endpoint simplification
- **Streamlined Task Functions**: Simplified parameter passing across all ECEG methods

## 📚 API Documentation

### 🔑 Base URL
```
http://localhost:5000/api/v1
```

### 📋 Task Status & WebSocket Monitoring

#### **Get Task Status**
```http
GET /tasks/{task_id}
```

**Response:**
```json
{
  "status": true,
  "message": "Success",
  "data": {
    "task_id": "abc123",
    "status": "SUCCESS",
    "result": {
      "record": "extracted_message",
      "metrics": {
        "mse": 0.001,
        "psnr": 85.2,
        "ssim": 0.999,
        "cr": 0.7,
        "ss": 30.0
      }
    }
  }
}
```

#### **WebSocket Task Monitoring**
```javascript
const ws = new WebSocket(`ws://localhost:5000/api/v1/tasks/${taskId}/ws`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  // {
  //   "task_id": "abc123",
  //   "status": "STARTED",
  //   "stage": "Processing Plaintext",
  //   "progress": 25
  // }
};
```

### 🎯 KTP Generator

#### **Generate KTP Data**
```http
GET /ktp/generator?generation_type=unique&max_bits=3145696&additional_length=0
```

**Parameters:**
- `generation_type`: `'unique'` or `'repeat'` (default: `'unique'`)
- `max_bits`: Maximum bit size for target-based generation (optional)
- `additional_length`: Additional bits to extend max_bits (default: `0`)

**Response:**
```json
{
  "status": true,
  "message": "Successfully generated KTP data with target bit size 3145696",
  "data": "1612061105735870#KH._Cagak_Halim,_S.I.Kom#Bau-Bau,_01-08-1962#Laki-Laki#..."
}
```

### 🔐 Steganography LSB

#### **Calculate LSB Capacity**
```http
POST /steganography/lsb/calculate-capacity
Content-Type: multipart/form-data

file: [PNG image]
k_val: 4
```

**Response:**
```json
{
  "status": true,
  "message": "Success",
  "data": {
    "max_chars": 393212,
    "max_bits": 3145696,
    "k_val": 4,
    "notes": "Gambar ini dapat menampung hingga 393.212 (tiga ratus sembilan puluh dua ribu dua ratus dua belas) karakter.",
    "dimensions": {
      "width": 1920,
      "height": 1080
    }
  }
}
```

#### **LSB Embed**
```http
POST /steganography/lsb/embed
Content-Type: multipart/form-data

file: [PNG cover image]
message: "Secret message to hide"
k_val: 4
```

**Response:**
```json
{
  "status": true,
  "message": "Success",
  "data": {
    "task_id": "abc123",
    "status": "PENDING",
    "check": "/tasks/abc123",
    "job_id": "def456",
    "cover_key": "steganography/def456/cover-image.png",
    "notes": "Gunakan WebSocket atau /tasks/{id} untuk mendapatkan stego key & URL."
  }
}
```

#### **LSB Extract**
```http
POST /steganography/lsb/extract
Content-Type: multipart/form-data

file: [PNG stego image]
original: [PNG original image]
k_val: 4
```

**Response:**
```json
{
  "status": true,
  "message": "Success",
  "data": {
    "task_id": "abc123",
    "status": "PENDING",
    "check": "/tasks/abc123",
    "job_id": "def456",
    "stego_key": "steganography/def456/stego-image.png",
    "original_key": "steganography/def456/cover-image.png",
    "notes": "Use WebSocket or /tasks/{id} until SUCCESS to get message + metrics."
  }
}
```

### 🧪 Experiment Endpoints

All experiment endpoints follow the same pattern for embedding and extraction:

#### **ECEG + LSB Embed Example**
```http
POST /experiments/eceg-lsb/embed
Content-Type: multipart/form-data

file: [PNG cover image]
k_val: 4
plaintext: "Secret message for ECEG encryption"
```

**Response:**
```json
{
  "status": true,
  "message": "Success",
  "data": {
    "task_id": "abc123",
    "status": "PENDING"
  }
}
```

**Task Success Response:**
```json
{
  "task_id": "abc123",
  "status": "SUCCESS",
  "result": {
    "stego_key": "experiments/def456/stego-eceg-lsb-image.png",
    "stego_url": "https://s3.amazonaws.com/...",
    "k_val": 4,
    "private_key": 12345,
    "public_key": 67890
  }
}
```

#### **ECEG + LSB Extract Example**
```http
POST /experiments/eceg-lsb/extract
Content-Type: multipart/form-data

stego_image: [PNG stego image]
original_image: [PNG original image]
k_val: 4
private_key: 12345
```

**Task Success Response:**
```json
{
  "task_id": "abc123",
  "status": "SUCCESS",
  "result": {
    "record": "Decrypted secret message",
    "metrics": {
      "mse": 0.001,
      "psnr": 85.2,
      "ssim": 0.999,
      "cr": "inf",
      "ss": "inf"
    }
  }
}
```

### 🔄 Available Experiment Methods

1. **ECEG + LSB**: `/experiments/eceg-lsb/embed`, `/experiments/eceg-lsb/extract`
2. **ECEG + LZW + LSB**: `/experiments/eceg-lzw-lsb/embed`, `/experiments/eceg-lzw-lsb/extract`
3. **ECEG + Huffman + LSB**: `/experiments/eceg-huffman-coding-lsb/embed`, `/experiments/eceg-huffman-coding-lsb/extract`
4. **LZW + ECEG + LSB**: `/experiments/lzw-eceg-lsb/embed`, `/experiments/lzw-eceg-lsb/extract`
5. **Huffman + ECEG + LSB**: `/experiments/huffman-coding-eceg-lsb/embed`, `/experiments/huffman-coding-eceg-lsb/extract`

Each method has different parameters:
- **Compression methods** (LZW, Huffman) return additional compression metrics
- **ECEG methods** always generate and return `private_key` and `public_key`
- **Extract methods** require `private_key` for ECEG decryption

#### **4. Files Modified**
- `app/controllers/ktp_generator.py` - Fixed KTP generation bugs and simplified output format
- `app/controllers/steganography.py` - LSB steganography endpoints
- `app/controllers/experiments.py` - Standardized all extract endpoint parameter names and simplified ECEG workflow
- `app/controllers/tasks.py` - Enhanced WebSocket to forward complete task metadata
- `tasks/experiments/` - Updated all 8 experiment task files with parameter simplification

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
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from steganography.lsb import LeastSignificantBit
from helpers.message_bit import message_to_bit, bit_to_message
import os
import tempfile
from fastapi.responses import FileResponse, JSONResponse
from uuid import uuid4
from s3.main import upload_and_presign, PRESIGN_TTL, S3_BUCKET
from steganography.metrics import StegoMetrics 

app = FastAPI()


@app.post("/lsb/embed")
async def lsb_embed(
    file: UploadFile = File(..., description="Cover image (PNG/JPG)"),
    message: str = Form(..., description="Message to hide"),
    k_val: int = Form(4, description="Number of LSBs to use (1-8)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(status_code=422, detail="k_val must be between 1 and 8")

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        suffix = ".png"

    input_path = output_path = None
    try:
        # Save input
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(await file.read())
            input_path = tmp_in.name

        # Stego output (always PNG)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_out:
            output_path = tmp_out.name

        # Embed
        lsb = LeastSignificantBit(k_val=k_val)
        msg_bits = message_to_bit(message)  # text -> raw bits
        lsb.embed_message(input_path, output_path, msg_bits)

        # Upload to S3
        key = f"stego-lsb/{os.path.splitext(file.filename or 'stego')[0]}_{uuid4().hex}.png"
        url = upload_and_presign(output_path, key, content_type="image/png")

        return JSONResponse(
            {
                "bucket": S3_BUCKET,
                "key": key,
                "url": url,
                "expires_in": PRESIGN_TTL,
                "k_val": k_val,
                "note": "Save the message and k_val; you need the same k_val to extract."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        for p in (input_path, output_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

@app.post("/lsb/extract")
async def lsb_extract(
    file: UploadFile = File(..., description="Stego image (PNG/JPG)"),
    original: UploadFile = File(..., description="Original cover image (PNG/JPG)"),  # required for your metrics
    k_val: int = Form(4, description="Number of LSBs used (must match embedding)")
):
    if not (1 <= k_val <= 8):
        raise HTTPException(status_code=422, detail="k_val must be between 1 and 8")

    stego_path = None
    original_path = None
    try:
        # Save stego
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_stego:
            tmp_stego.write(await file.read())
            stego_path = tmp_stego.name

        # Save original (needed by StegoMetrics)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_orig:
            tmp_orig.write(await original.read())
            original_path = tmp_orig.name

        # 1) extract hidden message
        lsb = LeastSignificantBit(k_val=k_val)
        extracted_bits = lsb.extract_message(stego_path)
        message = bit_to_message(extracted_bits)

        # 2) compute metrics (MSE, PSNR, SSIM)
        metrics_calc = StegoMetrics(ori_image=original_path)
        mse, psnr, ssim = metrics_calc.calculate_metrics(stego_path)

        return JSONResponse({
            "message": message,
            "metrics": {
                "mse": float(mse),
                "psnr": float(psnr) if psnr != float("inf") else "inf",
                "ssim": float(ssim)
            }
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # cleanup
        for p in (stego_path, original_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
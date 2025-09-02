from fastapi import APIRouter
from pydantic import BaseModel
from helpers.response_wrapper import api_response
from methods.preprocess.bit_padding import encode_with_padding_info, decode_with_padding_info

# Buat instance router
router = APIRouter()

# --- Pydantic Models for Request Bodies ---
class BitPaddingEncodeRequest(BaseModel):
    bits: str

class BitPaddingDecodeRequest(BaseModel):
    encoded_string: str

# --- Endpoints ---
@router.post("/bit-padding/encode")
async def bit_padding_encode(request: BitPaddingEncodeRequest):
    """
    Mengubah string biner menjadi string ASCII yang aman 
    dengan informasi padding yang disematkan.
    """
    try:
        # Validasi input untuk memastikan hanya berisi '0' dan '1'
        if not request.bits.isdigit() or not all(c in '01' for c in request.bits):
            return api_response(
                status=False,
                message="Invalid Input",
                error="Parameter 'bits' harus berupa string yang hanya berisi '0' dan '1'.",
                status_code=422
            )
        
        encoded_result = encode_with_padding_info(request.bits)
        return api_response(data={"encoded_string": encoded_result})

    except Exception as e:
        return api_response(status=False, message="Encoding failed", error=str(e), status_code=500)


@router.post("/bit-padding/decode")
async def bit_padding_decode(request: BitPaddingDecodeRequest):
    """
    Mengubah kembali string ASCII yang di-encode menjadi string biner aslinya.
    """
    try:
        decoded_result = decode_with_padding_info(request.encoded_string)
        return api_response(data={"decoded_bits": decoded_result})
        
    except Exception as e:
        # Menangkap error jika input tidak valid (misalnya karakter non-ASCII)
        return api_response(
            status=False, 
            message="Decoding failed, possibly due to invalid input string.", 
            error=str(e), 
            status_code=422
        )
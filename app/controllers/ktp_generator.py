from fastapi import APIRouter, Query
from helpers.response_wrapper import api_response
from fakers.main import DummyKTPGenerator
from typing import Literal

# Buat instance router
router = APIRouter()

# Buat satu instance generator untuk digunakan kembali, ini lebih efisien
ktp_generator = DummyKTPGenerator()

@router.get("/generator")
async def generate_dummy_ktp(
    count: int = Query(
        default=1, 
        ge=1, 
        le=100, 
        description="Jumlah data KTP yang ingin dibuat (antara 1 dan 100)."
    ),
    output_format: Literal['json', 'merged'] = Query(
        default='json',
        description="Format output: 'json' (data lengkap) atau 'merged' (string ringkas)."
    )
):
    """
    Menghasilkan data KTP palsu yang konsisten secara logis.
    """
    try:
        # Hasilkan data KTP sebanyak 'count'
        ktp_list = [ktp_generator.generate_ktp() for _ in range(count)]

        if output_format == 'merged':
            # Jika formatnya 'merged', proses data menjadi string ringkas
            result_data = ktp_generator.merge_multiple_ktps(ktp_list)
        else:
            # Jika tidak, kembalikan sebagai list of dictionaries (JSON)
            result_data = ktp_list

        return api_response(data=result_data, message=f"Successfully generated {len(result_data)} KTP records.")

    except Exception as e:
        return api_response(
            status=False, 
            message="An unexpected server error occurred", 
            error=str(e),
            status_code=500 # Internal Server Error
        )
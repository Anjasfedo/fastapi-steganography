from fastapi import APIRouter, Query
from helpers.response_wrapper import api_response
from fakers.main import DummyKTPGenerator, KTP_FIELD_ORDER
from typing import Literal
from methods.preprocess.data_serialization import serialize_record

# Buat instance router
router = APIRouter()

# Buat satu instance generator untuk digunakan kembali, ini lebih efisien
ktp_generator = DummyKTPGenerator()


@router.get("/generator")
async def generate_dummy_ktp(
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
        ktp_data = ktp_generator.generate_ktp()

        if output_format == 'merged':
            # 2. Panggil fungsi serialisasi dengan benar di sini
            result_data = serialize_record(ktp_data, KTP_FIELD_ORDER)
        else:
            # Jika tidak, kembalikan sebagai list of dictionaries (JSON)
            result_data = ktp_data

        return api_response(data=result_data, message=f"Successfully generated {len(result_data)} KTP records.")

    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )

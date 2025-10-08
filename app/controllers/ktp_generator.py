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
    generation_type: Literal['unique', 'repeat'] = Query(
        default='unique',
        description="Generation type: 'unique' (generate different KTPs) atau 'repeat' (repeat same KTP)."
    ),
    max_bits: int = Query(
        default=None,
        description="Maximum bit size for target-based generation"
    ),
    additional_length: int = Query(
        default=0,
        description="Additional length to extend max_bits"
    )
):
    """
    Menghasilkan data KTP palsu yang konsisten secara logis.
    """
    try:
        # Check if target-based generation is requested
        if max_bits is not None:
            # Generate based on target length
            result_data = ktp_generator.generate_ktp_based_on_target_length(
                max_bits=max_bits,
                additional_length=additional_length,
                generation_type=generation_type
            )
            message = f"Successfully generated KTP data with target bit size {max_bits}"
        else:
            # Generate single KTP
            if generation_type == 'repeat':
                ktp_data = [ktp_generator.generate_ktp()]  # Generate once and put in list
            else:
                ktp_data = ktp_generator.generate_ktp()  # Generate single KTP

            # Always serialize to merged format
            if isinstance(ktp_data, list):
                result_data = [serialize_record(ktp, KTP_FIELD_ORDER) for ktp in ktp_data]
            else:
                result_data = serialize_record(ktp_data, KTP_FIELD_ORDER)

            message = f"Successfully generated {len(result_data) if isinstance(result_data, list) else 1} KTP records"

        print(ktp_data if 'ktp_data' in locals() else result_data)

        return api_response(data=result_data, message=message)

    except Exception as e:
        return api_response(
            status=False,
            message="An unexpected server error occurred",
            error=str(e),
            status_code=500  # Internal Server Error
        )

from fastapi.responses import JSONResponse

def api_response(data=None, message="Success", status=True, error=None, status_code: int = 200):
    """
    Menstandardisasi format respons untuk API.

    Args: 
    - data: Data utama yang akan dikembalikan.
    - message: Pesan yang mendeskripsikan hasil.
    - status: Boolean yang menunjukkan keberhasilan atau kegagalan.
    - error: Pesan error opsional.
    - status_code: Kode status HTTP untuk respons (default: 200).
    
    Returns:
    - JSONResponse: Respons JSON yang terstandardisasi.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "message": message,
            "data": data,
            "error": error,
        }
    )
from fastapi.responses import JSONResponse

def api_response(data=None, message="Success", status=True, error=None):
    """
    Standardizes the response format for the API.

    Args:
    - data: The main data to return (default: None).
    - message: A message describing the result (default: "Success").
    - status: Boolean indicating success or failure (default: True).
    - error: Optional error message (default: None).
    
    Returns:
    - JSONResponse: A standardized JSON response.
    """
    return JSONResponse({
        "status": status,
        "message": message,
        "data": data,
        "error": error,
    })

from fastapi.responses import JSONResponse


ERRORS = {
    "invalid_json": (400, "Invalid JSON."),
    "unauthorized": (401, "Valid API key required."),
    "not_found": (404, "Resource not found."),
    "method_not_allowed": (405, "Method not allowed."),
    "payload_too_large": (413, "Request body too large."),
    "unsupported_media_type": (415, "Unsupported request format."),
    "validation_error": (422, "Request validation failed."),
    "batch_conflict": (409, "Batch identity conflict."),
    "event_conflict": (409, "Event identity conflict."),
    "metric_limit": (409, "Run metric limit reached."),
    "cursor_exhausted": (409, "Run sequence limit reached."),
    "cursor_ahead": (409, "Cursor exceeds committed sequence."),
    "temporarily_unavailable": (503, "Service temporarily unavailable."),
    "internal_error": (500, "Internal server error."),
}


class APIError(Exception):
    def __init__(self, code: str):
        self.code = code


def error_response(code: str) -> JSONResponse:
    status, message = ERRORS[code]
    headers = {}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 503:
        headers["Retry-After"] = "1"
    return JSONResponse({"error": {"code": code, "message": message}}, status, headers)

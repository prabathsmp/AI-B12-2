from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error rendered as {"error": CODE, "message": "..."} (matches the PRD contract)."""

    def __init__(self, status_code: int, error: str, message: str):
        self.status_code = status_code
        self.error = error
        self.message = message


async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error, "message": exc.message})


async def validation_error_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query"))
    msg = first.get("msg", "Invalid input")
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "message": f"{field}: {msg}" if field else msg, "details": exc.errors()},
    )

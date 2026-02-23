from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from deployment_mapper.domain.models import ValidationError

logger = logging.getLogger("deployment_mapper.api")


def _request_id(request: Request) -> str:
    context = getattr(request.state, "request_context", None)
    request_id = getattr(context, "request_id", None)
    return str(request_id) if request_id else "unknown"


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[str] | dict[str, object] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "code": code,
        "message": message,
        "details": details or [],
        "request_id": _request_id(request),
    }
    response = JSONResponse(status_code=status_code, content=body)
    response.headers["X-Request-ID"] = _request_id(request)
    return response


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Input validation failed.",
        details=[str(exc)],
    )


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}" for error in exc.errors()]
    return error_response(
        request=request,
        status_code=422,
        code="REQUEST_VALIDATION_ERROR",
        message="Request payload is invalid.",
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", extra={"request_id": _request_id(request)})
    return error_response(
        request=request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="An internal error occurred.",
        details=["Contact support with the request_id for correlation."],
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    details: list[str] | dict[str, object]
    if isinstance(exc.detail, list):
        details = [str(item) for item in exc.detail]
    elif isinstance(exc.detail, dict):
        details = {str(k): v for k, v in exc.detail.items()}
    elif exc.detail is None:
        details = []
    else:
        details = [str(exc.detail)]

    status_code = int(exc.status_code)
    code = "AUTH_ERROR" if status_code in {401, 403} else "HTTP_ERROR"
    message = "Request failed." if status_code < 500 else "An internal error occurred."
    response = error_response(
        request=request,
        status_code=status_code,
        code=code,
        message=message,
        details=details,
    )
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response


async def payload_parsing_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Input validation failed.",
        details=[str(exc)],
    )

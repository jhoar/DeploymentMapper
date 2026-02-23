from __future__ import annotations

from importlib import metadata

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from deployment_mapper.api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
    request_validation_error_handler,
)
from deployment_mapper.api.observability import RequestContextMiddleware, metrics_response
from deployment_mapper.api.routers.diagrams import router as diagrams_router
from deployment_mapper.api.routers.schemas import router as schemas_router
from deployment_mapper.domain.models import ValidationError


app = FastAPI(title="DeploymentMapper API")
app.add_middleware(RequestContextMiddleware)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(schemas_router)
app.include_router(diagrams_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    try:
        value = metadata.version("deployment_mapper")
    except metadata.PackageNotFoundError:
        value = "0.0.0"
    return {"version": value}


@app.get("/metrics", include_in_schema=False)
def metrics() -> object:
    return metrics_response()

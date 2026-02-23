from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Callable

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "deployment_mapper_http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status_code"],
)
REQUEST_ERRORS = Counter(
    "deployment_mapper_http_request_errors_total",
    "Total HTTP error responses.",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "deployment_mapper_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)

logger = logging.getLogger("deployment_mapper.api")


@dataclass(slots=True)
class RequestContext:
    request_id: str


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    if route and getattr(route, "path", None):
        return str(route.path)
    return request.url.path


def _request_id_from_headers(request: Request) -> str:
    provided = request.headers.get("X-Request-ID")
    if provided and provided.strip():
        return provided.strip()
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        request_id = _request_id_from_headers(request)
        request.state.request_context = RequestContext(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = _route_label(request)
        status_code = str(response.status_code)

        REQUEST_COUNT.labels(method=request.method, path=path, status_code=status_code).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(elapsed)
        if response.status_code >= 400:
            REQUEST_ERRORS.labels(method=request.method, path=path, status_code=status_code).inc()

        log_record = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed * 1000, 3),
            "client": request.client.host if request.client else None,
        }
        logger.info(json.dumps(log_record, separators=(",", ":")))
        response.headers["X-Request-ID"] = request_id
        return response


def metrics_response() -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

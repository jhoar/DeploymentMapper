from __future__ import annotations

from importlib import metadata

from fastapi import FastAPI

from deployment_mapper.api.routers.diagrams import router as diagrams_router
from deployment_mapper.api.routers.schemas import router as schemas_router


app = FastAPI(title="DeploymentMapper API")
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

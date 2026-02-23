from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from deployment_mapper.api.security import AuthContext, require_role
from deployment_mapper.artifacts import LocalArtifactStore
from deployment_mapper.domain.json_loader import load_schema_from_dict
from deployment_mapper.domain.uml_demo import generate_plantuml

router = APIRouter(prefix="/diagrams", tags=["diagrams"])
artifact_store = LocalArtifactStore(base_dir=os.getenv("DEPLOYMENT_MAPPER_ARTIFACT_PATH", "deployment_mapper/artifacts"))


def _request_id(payload: dict[str, object]) -> str:
    request_id = payload.get("request_id")
    return str(request_id) if request_id else "default-request"


@router.post("/plantuml")
def build_plantuml(
    payload: dict[str, object],
    _: AuthContext = Depends(require_role("editor")),
) -> dict[str, object]:
    """Generate PlantUML text for a validated schema payload."""
    schema = load_schema_from_dict(payload)

    puml = generate_plantuml(schema)
    stored_artifact = artifact_store.write_text(
        request_id=_request_id(payload),
        schema_payload=payload,
        content=puml,
        content_type="text/plantuml",
    )
    return {
        "valid": True,
        "errors": [],
        "puml": puml,
        "artifact_path": str(stored_artifact.path),
        "artifact_metadata": {
            "created_at": stored_artifact.metadata.created_at,
            "content_type": stored_artifact.metadata.content_type,
            "source_schema_id": stored_artifact.metadata.source_schema_id,
            "source_schema_version": stored_artifact.metadata.source_schema_version,
        },
    }


@router.post("/render")
def render_diagram(
    payload: dict[str, object],
    _: AuthContext = Depends(require_role("editor")),
) -> dict[str, object]:
    """Stub endpoint for future rendering support."""
    load_schema_from_dict(payload)

    stored_artifact = artifact_store.write_text(
        request_id=_request_id(payload),
        schema_payload=payload,
        content="Rendering is not enabled in this build.",
        content_type="text/plain",
    )
    return {
        "valid": True,
        "errors": [],
        "rendered": False,
        "message": "Rendering is not enabled in this build.",
        "output_path": str(stored_artifact.path),
        "artifact_metadata": {
            "created_at": stored_artifact.metadata.created_at,
            "content_type": stored_artifact.metadata.content_type,
            "source_schema_id": stored_artifact.metadata.source_schema_id,
            "source_schema_version": stored_artifact.metadata.source_schema_version,
        },
    }


@router.get("/artifacts")
def list_artifacts(
    request_id: str | None = Query(default=None),
    _: AuthContext = Depends(require_role("reader")),
) -> dict[str, object]:
    artifacts = artifact_store.list_artifacts(request_id=request_id)
    return {
        "count": len(artifacts),
        "artifacts": [
            {
                "path": str(item.path),
                "request_id": item.metadata.request_id,
                "schema_hash": item.metadata.schema_hash,
                "content_type": item.metadata.content_type,
                "created_at": item.metadata.created_at,
            }
            for item in artifacts
        ],
    }


@router.get("/artifacts/{request_id}/{artifact_name}")
def read_artifact(
    request_id: str,
    artifact_name: str,
    _: AuthContext = Depends(require_role("reader")),
) -> dict[str, object]:
    try:
        stored_artifact = artifact_store.read_text(request_id=request_id, artifact_name=artifact_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "path": str(stored_artifact.path),
        "content": stored_artifact.path.read_text(encoding="utf-8"),
        "metadata": {
            "created_at": stored_artifact.metadata.created_at,
            "content_type": stored_artifact.metadata.content_type,
            "source_schema_id": stored_artifact.metadata.source_schema_id,
            "source_schema_version": stored_artifact.metadata.source_schema_version,
            "request_id": stored_artifact.metadata.request_id,
            "schema_hash": stored_artifact.metadata.schema_hash,
        },
    }


@router.get("/admin/config")
def get_artifact_config(
    _: AuthContext = Depends(require_role("admin")),
) -> dict[str, object]:
    return {
        "base_dir": str(Path(artifact_store.base_dir)),
        "ttl_seconds": artifact_store.ttl_seconds,
        "max_count": artifact_store.max_count,
    }


@router.post("/admin/cleanup")
def cleanup_artifacts(
    _: AuthContext = Depends(require_role("admin")),
) -> dict[str, object]:
    deleted = artifact_store.cleanup()
    return {"deleted": deleted}

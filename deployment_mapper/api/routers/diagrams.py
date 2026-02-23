from __future__ import annotations

from deployment_mapper.artifacts import LocalArtifactStore
from fastapi import APIRouter

from deployment_mapper.domain.json_loader import load_schema_from_dict
from deployment_mapper.domain.models import ValidationError
from deployment_mapper.domain.uml_demo import generate_plantuml

router = APIRouter(prefix="/diagrams", tags=["diagrams"])
artifact_store = LocalArtifactStore()


def _request_id(payload: dict[str, object]) -> str:
    request_id = payload.get("request_id")
    return str(request_id) if request_id else "default-request"


@router.post("/plantuml")
def build_plantuml(payload: dict[str, object]) -> dict[str, object]:
    """Generate PlantUML text for a validated schema payload."""
    try:
        schema = load_schema_from_dict(payload)
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

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
def render_diagram(payload: dict[str, object]) -> dict[str, object]:
    """Stub endpoint for future rendering support."""
    try:
        load_schema_from_dict(payload)
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

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

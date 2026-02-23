from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from deployment_mapper.domain.json_loader import parse_schema_payload
from deployment_mapper.domain.models import ValidationError
from deployment_mapper.domain.uml_demo import generate_plantuml

router = APIRouter(prefix="/diagrams", tags=["diagrams"])


@router.post("/plantuml")
def build_plantuml(payload: dict[str, object]) -> dict[str, object]:
    """Generate PlantUML text for a validated schema payload."""
    try:
        schema = parse_schema_payload(payload)
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

    puml = generate_plantuml(schema)
    return {"valid": True, "errors": [], "puml": puml}


@router.post("/render")
def render_diagram(payload: dict[str, object]) -> dict[str, object]:
    """Stub endpoint for future rendering support."""
    try:
        parse_schema_payload(payload)
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

    output_path = Path("artifacts") / "diagram-output.png"
    return {
        "valid": True,
        "errors": [],
        "rendered": False,
        "message": "Rendering is not enabled in this build.",
        "output_path": str(output_path),
    }

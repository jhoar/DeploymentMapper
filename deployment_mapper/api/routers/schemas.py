from __future__ import annotations

from fastapi import APIRouter, Depends

from deployment_mapper.api.security import AuthContext, require_role
from deployment_mapper.domain.json_loader import load_schema_from_dict

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.post("/validate")
def validate_schema(
    payload: dict[str, object],
    _: AuthContext = Depends(require_role("editor")),
) -> dict[str, object]:
    """Validate deployment schema JSON payloads."""
    schema = load_schema_from_dict(payload)

    return {
        "valid": True,
        "errors": [],
        "counts": {
            "subnets": len(schema.subnets),
            "hardware_nodes": len(schema.hardware_nodes),
            "kubernetes_clusters": len(schema.kubernetes_clusters),
            "virtual_machines": len(schema.virtual_machines),
            "storage_servers": len(schema.storage_servers),
            "network_switches": len(schema.network_switches),
            "software_systems": len(schema.software_systems),
            "deployment_instances": len(schema.deployment_instances),
        },
    }

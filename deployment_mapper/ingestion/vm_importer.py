from __future__ import annotations

from typing import Any

from deployment_mapper.domain.models import DeploymentSchema, VirtualMachine
from deployment_mapper.ingestion.diagnostics import DiagnosticLevel, ImportDiagnostics


def import_vm_mappings(
    payload: dict[str, Any],
    *,
    known_host_ids: set[str],
    known_subnet_ids: set[str],
) -> tuple[DeploymentSchema, ImportDiagnostics]:
    diagnostics = ImportDiagnostics()
    schema = DeploymentSchema()

    for vm_payload in payload.get("virtual_machines", []):
        subnet_id = vm_payload.get("subnet_id")
        if subnet_id not in known_subnet_ids:
            diagnostics.add(
                "missing_reference",
                "VM references unknown subnet.",
                level=DiagnosticLevel.ERROR,
                entity="virtual_machine",
                entity_id=vm_payload.get("id"),
                field="subnet_id",
                missing_id=subnet_id,
            )
            continue

        host_node_id = vm_payload.get("host_node_id")
        if host_node_id not in known_host_ids:
            diagnostics.add(
                "missing_reference",
                "VM host mapping references unknown hardware node.",
                level=DiagnosticLevel.ERROR,
                entity="virtual_machine",
                entity_id=vm_payload.get("id"),
                field="host_node_id",
                missing_id=host_node_id,
            )
            continue

        schema.virtual_machines.append(
            VirtualMachine(
                id=vm_payload["id"],
                hostname=vm_payload["hostname"],
                ip_address=vm_payload["ip_address"],
                subnet_id=subnet_id,
                host_node_id=host_node_id,
            )
        )

    return schema, diagnostics

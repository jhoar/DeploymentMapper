from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ValidationError,
    DeploymentInstance,
    DeploymentSchema,
    DeploymentTargetKind,
    HardwareNode,
    KubernetesCluster,
    NetworkSwitch,
    NodeKind,
    SoftwareSystem,
    StorageServer,
    Subnet,
    VirtualMachine,
)


def load_schema_from_dict(payload: dict[str, object]) -> DeploymentSchema:
    """Load a validated DeploymentSchema from a JSON-like dictionary payload."""

    try:
        schema = DeploymentSchema(
            subnets=[Subnet(**item) for item in payload.get("subnets", [])],
            hardware_nodes=[
                HardwareNode(
                    id=item["id"],
                    hostname=item["hostname"],
                    ip_address=item["ip_address"],
                    subnet_id=item["subnet_id"],
                    kind=NodeKind(item.get("kind", NodeKind.PHYSICAL.value)),
                )
                for item in payload.get("hardware_nodes", [])
            ],
            kubernetes_clusters=[KubernetesCluster(**item) for item in payload.get("kubernetes_clusters", [])],
            virtual_machines=[VirtualMachine(**item) for item in payload.get("virtual_machines", [])],
            storage_servers=[StorageServer(**item) for item in payload.get("storage_servers", [])],
            network_switches=[NetworkSwitch(**item) for item in payload.get("network_switches", [])],
            software_systems=[SoftwareSystem(**item) for item in payload.get("software_systems", [])],
            deployment_instances=[
                DeploymentInstance(
                    id=item["id"],
                    system_id=item["system_id"],
                    target_kind=DeploymentTargetKind(item["target_kind"]),
                    target_node_id=item.get("target_node_id"),
                    target_cluster_id=item.get("target_cluster_id"),
                    component_id=item.get("component_id"),
                    namespace=item.get("namespace"),
                )
                for item in payload.get("deployment_instances", [])
            ],
        )
        schema.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc

    return schema


def load_schema_from_json_file(path: str | Path) -> DeploymentSchema:
    """Read a JSON file and load it into a validated DeploymentSchema."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return load_schema_from_dict(payload)


# Backward compatible alias.
parse_schema_payload = load_schema_from_dict

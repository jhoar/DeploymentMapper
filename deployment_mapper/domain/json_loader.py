from __future__ import annotations

from .models import (
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


def parse_schema_payload(payload: dict[str, object]) -> DeploymentSchema:
    """Parse JSON-like payload data into a validated DeploymentSchema."""

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
    return schema


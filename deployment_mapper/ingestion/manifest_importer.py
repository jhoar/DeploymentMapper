from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deployment_mapper.domain.models import (
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
from deployment_mapper.ingestion.diagnostics import DiagnosticLevel, ImportDiagnostics
from deployment_mapper.validation import validate_schema_for_import


def import_manifest_file(path: str | Path) -> tuple[DeploymentSchema, ImportDiagnostics]:
    file_path = Path(path)
    raw = file_path.read_text(encoding="utf-8")
    return import_manifest(raw, source_name=str(file_path))


def import_manifest(raw: str | bytes | dict[str, Any], *, source_name: str = "manifest") -> tuple[DeploymentSchema, ImportDiagnostics]:
    payload = _parse_manifest(raw)
    diagnostics = ImportDiagnostics()

    schema = DeploymentSchema()

    subnet_ids: set[str] = set()
    for item in payload.get("subnets", []):
        subnet = Subnet(id=item["id"], cidr=item["cidr"], name=item["name"])
        schema.subnets.append(subnet)
        subnet_ids.add(subnet.id)

    hardware_ids: set[str] = set()
    for item in payload.get("hardware_nodes", []):
        if item["subnet_id"] not in subnet_ids:
            diagnostics.add(
                "missing_reference",
                "Hardware node references unknown subnet.",
                source=source_name,
                entity="hardware_node",
                entity_id=item.get("id"),
                field="subnet_id",
                missing_id=item.get("subnet_id"),
            )
            continue
        node = HardwareNode(
            id=item["id"],
            hostname=item["hostname"],
            ip_address=item["ip_address"],
            subnet_id=item["subnet_id"],
            kind=NodeKind(item.get("kind", NodeKind.PHYSICAL.value)),
        )
        schema.hardware_nodes.append(node)
        hardware_ids.add(node.id)

    for item in payload.get("virtual_machines", []):
        missing_field: str | None = None
        if item["subnet_id"] not in subnet_ids:
            missing_field = "subnet_id"
        elif item["host_node_id"] not in hardware_ids:
            missing_field = "host_node_id"
        if missing_field:
            diagnostics.add(
                "missing_reference",
                "Virtual machine references unknown object.",
                source=source_name,
                entity="virtual_machine",
                entity_id=item.get("id"),
                field=missing_field,
                missing_id=item.get(missing_field),
            )
            continue
        schema.virtual_machines.append(
            VirtualMachine(
                id=item["id"],
                hostname=item["hostname"],
                ip_address=item["ip_address"],
                subnet_id=item["subnet_id"],
                host_node_id=item["host_node_id"],
            )
        )

    cluster_ids: set[str] = set()
    for item in payload.get("kubernetes_clusters", []):
        if item["subnet_id"] not in subnet_ids:
            diagnostics.add(
                "missing_reference",
                "Kubernetes cluster references unknown subnet.",
                source=source_name,
                entity="kubernetes_cluster",
                entity_id=item.get("id"),
                field="subnet_id",
                missing_id=item.get("subnet_id"),
            )
            continue

        node_ids = []
        for node_id in item.get("node_ids", []):
            if node_id not in hardware_ids:
                diagnostics.add(
                    "missing_reference",
                    "Kubernetes cluster node assignment references unknown hardware node.",
                    source=source_name,
                    entity="kubernetes_cluster",
                    entity_id=item.get("id"),
                    field="node_ids",
                    missing_id=node_id,
                )
                continue
            node_ids.append(node_id)

        cluster = KubernetesCluster(
            id=item["id"],
            name=item["name"],
            subnet_id=item["subnet_id"],
            node_ids=node_ids,
        )
        schema.kubernetes_clusters.append(cluster)
        cluster_ids.add(cluster.id)

    for item in payload.get("storage_servers", []):
        if item["subnet_id"] not in subnet_ids:
            diagnostics.add(
                "missing_reference",
                "Storage server references unknown subnet.",
                source=source_name,
                entity="storage_server",
                entity_id=item.get("id"),
                field="subnet_id",
                missing_id=item.get("subnet_id"),
            )
            continue
        schema.storage_servers.append(
            StorageServer(
                id=item["id"],
                hostname=item["hostname"],
                ip_address=item["ip_address"],
                subnet_id=item["subnet_id"],
            )
        )

    for item in payload.get("network_switches", []):
        if item["subnet_id"] not in subnet_ids:
            diagnostics.add(
                "missing_reference",
                "Network switch references unknown subnet.",
                source=source_name,
                entity="network_switch",
                entity_id=item.get("id"),
                field="subnet_id",
                missing_id=item.get("subnet_id"),
            )
            continue
        schema.network_switches.append(
            NetworkSwitch(
                id=item["id"],
                hostname=item["hostname"],
                management_ip=item["management_ip"],
                subnet_id=item["subnet_id"],
            )
        )

    system_ids: set[str] = set()
    for item in payload.get("software_systems", []):
        system = SoftwareSystem(id=item["id"], name=item["name"], version=item.get("version"))
        schema.software_systems.append(system)
        system_ids.add(system.id)

    vm_ids = {vm.id for vm in schema.virtual_machines}
    for item in payload.get("deployment_instances", []):
        try:
            target_kind = DeploymentTargetKind(item["target_kind"])
        except ValueError as exc:
            raise ValidationError(
                f"deployment_instance '{item.get('id', '<missing>')}' uses unsupported target_kind '{item.get('target_kind')}'. "
                f"Supported target kinds: {', '.join(kind.value for kind in DeploymentTargetKind)}. "
                "Suggested fix: update target_kind to a supported value."
            ) from exc
        missing_field: str | None = None

        if item["system_id"] not in system_ids:
            missing_field = "system_id"
        elif target_kind in (DeploymentTargetKind.HOST, DeploymentTargetKind.VM):
            target_node_id = item.get("target_node_id")
            allowed_ids = hardware_ids if target_kind is DeploymentTargetKind.HOST else vm_ids
            if target_node_id not in allowed_ids:
                missing_field = "target_node_id"
        elif target_kind in (DeploymentTargetKind.CLUSTER, DeploymentTargetKind.K8S_NAMESPACE):
            if item.get("target_cluster_id") not in cluster_ids:
                missing_field = "target_cluster_id"

        if missing_field:
            diagnostics.add(
                "missing_reference",
                "Deployment instance references unknown object.",
                level=DiagnosticLevel.ERROR,
                source=source_name,
                entity="deployment_instance",
                entity_id=item.get("id"),
                field=missing_field,
                missing_id=item.get(missing_field),
            )
            continue

        schema.deployment_instances.append(
            DeploymentInstance(
                id=item["id"],
                system_id=item["system_id"],
                target_kind=target_kind,
                target_node_id=item.get("target_node_id"),
                target_cluster_id=item.get("target_cluster_id"),
                component_id=item.get("component_id"),
                namespace=item.get("namespace"),
            )
        )

    validate_schema_for_import(schema)
    return schema, diagnostics


def _parse_manifest(raw: str | bytes | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(text)

    yaml_module = _load_yaml_module()
    if yaml_module is None:
        raise ValueError("YAML import requires PyYAML to be installed")
    parsed = yaml_module.safe_load(text)
    if not isinstance(parsed, dict):
        raise ValueError("Manifest content must deserialize into an object")
    return parsed


def _load_yaml_module() -> Any | None:
    try:
        import yaml
    except ImportError:
        return None
    return yaml

from __future__ import annotations

import re

from deployment_mapper.artifacts import LocalArtifactStore

from .demo_dataset import DEMO_DATASET_NAME, build_demo_schema
from .models import DeploymentSchema, DeploymentTargetKind


def _alias(prefix: str, raw_id: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_]", "_", raw_id)
    if normalized and normalized[0].isdigit():
        normalized = f"id_{normalized}"
    return f"{prefix}_{normalized}"


def generate_plantuml(schema: DeploymentSchema, title: str = "DeploymentMapper Demo") -> str:
    """Generate a PlantUML deployment diagram from a DeploymentSchema."""

    lines: list[str] = [
        "@startuml",
        f"title {title}",
        "skinparam componentStyle rectangle",
        "",
    ]

    subnet_alias = {s.id: _alias("subnet", s.id) for s in schema.subnets}
    hw_alias = {n.id: _alias("hw", n.id) for n in schema.hardware_nodes}
    vm_alias = {v.id: _alias("vm", v.id) for v in schema.virtual_machines}
    st_alias = {s.id: _alias("st", s.id) for s in schema.storage_servers}
    sw_alias = {s.id: _alias("sw", s.id) for s in schema.network_switches}
    k8s_alias = {c.id: _alias("k8s", c.id) for c in schema.kubernetes_clusters}
    sys_alias = {s.id: _alias("sys", s.id) for s in schema.software_systems}
    dep_alias = {d.id: _alias("dep", d.id) for d in schema.deployment_instances}

    for subnet in schema.subnets:
        lines.append(f'node "Subnet: {subnet.name}\\n{subnet.cidr}" as {subnet_alias[subnet.id]} {{')

        for node in [n for n in schema.hardware_nodes if n.subnet_id == subnet.id]:
            lines.append(
                f'  node "HW: {node.hostname}\\n{node.ip_address}\\n[{node.kind.value}]" as {hw_alias[node.id]}'
            )

        for vm in [v for v in schema.virtual_machines if v.subnet_id == subnet.id]:
            lines.append(f'  node "VM: {vm.hostname}\\n{vm.ip_address}" as {vm_alias[vm.id]}')

        for storage in [s for s in schema.storage_servers if s.subnet_id == subnet.id]:
            lines.append(f'  database "Storage: {storage.hostname}\\n{storage.ip_address}" as {st_alias[storage.id]}')

        for switch in [s for s in schema.network_switches if s.subnet_id == subnet.id]:
            lines.append(
                f'  node "Switch: {switch.hostname}\\n{switch.management_ip}" as {sw_alias[switch.id]}'
            )

        for cluster in [c for c in schema.kubernetes_clusters if c.subnet_id == subnet.id]:
            lines.append(f'  cloud "K8S Cluster: {cluster.name}" as {k8s_alias[cluster.id]}')

        lines.append("}")
        lines.append("")

    for vm in schema.virtual_machines:
        lines.append(f"{hw_alias[vm.host_node_id]} --> {vm_alias[vm.id]} : hosts")

    for cluster in schema.kubernetes_clusters:
        for node_id in cluster.node_ids:
            lines.append(f"{k8s_alias[cluster.id]} --> {hw_alias[node_id]} : worker")

    lines.append("")

    for system in schema.software_systems:
        lines.append(f'component "System: {system.name}\\n{system.id}" as {sys_alias[system.id]}')

    for instance in schema.deployment_instances:
        component_part = f"\\ncomponent={instance.component_id}" if instance.component_id else ""
        lines.append(f'artifact "Deployment: {instance.id}{component_part}" as {dep_alias[instance.id]}')

    lines.append("")

    for instance in schema.deployment_instances:
        component_edge = f" ({instance.component_id})" if instance.component_id else ""
        lines.append(
            f"{sys_alias[instance.system_id]} --> {dep_alias[instance.id]} : deploys{component_edge}"
        )

        if instance.target_kind is DeploymentTargetKind.HOST and instance.target_node_id:
            lines.append(f"{dep_alias[instance.id]} --> {hw_alias[instance.target_node_id]} : HOST")
        elif instance.target_kind is DeploymentTargetKind.VM and instance.target_node_id:
            lines.append(f"{dep_alias[instance.id]} --> {vm_alias[instance.target_node_id]} : VM")
        elif instance.target_kind is DeploymentTargetKind.CLUSTER and instance.target_cluster_id:
            lines.append(f"{dep_alias[instance.id]} --> {k8s_alias[instance.target_cluster_id]} : CLUSTER")
        elif instance.target_kind is DeploymentTargetKind.K8S_NAMESPACE and instance.target_cluster_id:
            lines.append(
                f"{dep_alias[instance.id]} --> {k8s_alias[instance.target_cluster_id]} : NAMESPACE/{instance.namespace}"
            )

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def main() -> None:
    """Generate a .puml deployment diagram file from the demo dataset."""

    schema = build_demo_schema()
    content = generate_plantuml(schema, title=f"{DEMO_DATASET_NAME} deployment")

    artifact_store = LocalArtifactStore(base_dir="examples")
    stored_artifact = artifact_store.write_text(
        request_id="demo_deployment_diagram",
        schema_payload={"schema_id": DEMO_DATASET_NAME, "schema_version": "1"},
        content=content,
        content_type="text/plantuml",
    )

    print(f"Wrote PlantUML diagram: {stored_artifact.path}")


if __name__ == "__main__":
    main()

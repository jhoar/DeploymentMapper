from __future__ import annotations

from pathlib import Path

from .demo_dataset import DEMO_DATASET_NAME, build_demo_schema
from .models import DeploymentSchema, DeploymentTargetKind


def generate_plantuml(schema: DeploymentSchema, title: str = "DeploymentMapper Demo") -> str:
    """Generate a PlantUML deployment diagram from a DeploymentSchema."""

    lines: list[str] = [
        "@startuml",
        f"title {title}",
        "skinparam componentStyle rectangle",
        "",
    ]

    # Subnets and infrastructure
    for subnet in schema.subnets:
        lines.append(f'node "Subnet: {subnet.name}\\n{subnet.cidr}" as subnet_{subnet.id} {{')

        for node in [n for n in schema.hardware_nodes if n.subnet_id == subnet.id]:
            lines.append(
                f'  node "HW: {node.hostname}\\n{node.ip_address}\\n[{node.kind.value}]" as hw_{node.id}'
            )

        for vm in [v for v in schema.virtual_machines if v.subnet_id == subnet.id]:
            lines.append(f'  node "VM: {vm.hostname}\\n{vm.ip_address}" as vm_{vm.id}')

        for storage in [s for s in schema.storage_servers if s.subnet_id == subnet.id]:
            lines.append(f'  database "Storage: {storage.hostname}\\n{storage.ip_address}" as st_{storage.id}')

        for switch in [s for s in schema.network_switches if s.subnet_id == subnet.id]:
            lines.append(
                f'  node "Switch: {switch.hostname}\\n{switch.management_ip}" as sw_{switch.id}'
            )

        for cluster in [c for c in schema.kubernetes_clusters if c.subnet_id == subnet.id]:
            lines.append(f'  cloud "K8S Cluster: {cluster.name}" as k8s_{cluster.id}')

        lines.append("}")
        lines.append("")

    # Structural relations
    for vm in schema.virtual_machines:
        lines.append(f"hw_{vm.host_node_id} --> vm_{vm.id} : hosts")

    for cluster in schema.kubernetes_clusters:
        for node_id in cluster.node_ids:
            lines.append(f"k8s_{cluster.id} --> hw_{node_id} : worker")

    lines.append("")

    # Software and deployment relations
    for system in schema.software_systems:
        lines.append(f'component "System: {system.name}\\n{system.id}" as sys_{system.id}')

    lines.append("")

    for instance in schema.deployment_instances:
        component_part = f" ({instance.component_id})" if instance.component_id else ""
        lines.append(f"sys_{instance.system_id} --> dep_{instance.id} : deploys{component_part}")

        if instance.target_kind is DeploymentTargetKind.HOST:
            lines.append(f"dep_{instance.id} --> hw_{instance.target_node_id} : HOST")
        elif instance.target_kind is DeploymentTargetKind.VM:
            lines.append(f"dep_{instance.id} --> vm_{instance.target_node_id} : VM")
        elif instance.target_kind is DeploymentTargetKind.CLUSTER:
            lines.append(f"dep_{instance.id} --> k8s_{instance.target_cluster_id} : CLUSTER")
        elif instance.target_kind is DeploymentTargetKind.K8S_NAMESPACE:
            lines.append(
                f"dep_{instance.id} --> k8s_{instance.target_cluster_id} : NAMESPACE/{instance.namespace}"
            )

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def main() -> None:
    """Generate a .puml deployment diagram file from the demo dataset."""

    schema = build_demo_schema()
    content = generate_plantuml(schema, title=f"{DEMO_DATASET_NAME} deployment")

    output = Path("examples/demo_deployment_diagram.puml")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    print(f"Wrote PlantUML diagram: {output}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

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
from .uml_demo import generate_plantuml


def load_schema_from_json_file(path: str | Path) -> DeploymentSchema:
    """Load DeploymentSchema from a JSON payload matching examples/demo_input_dataset.json format."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))

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


def main() -> None:
    """Read the example JSON dataset and write a UML .puml file."""

    input_path = Path("examples/demo_input_dataset.json")
    output_path = Path("examples/demo_input_dataset_diagram.puml")

    schema = load_schema_from_json_file(input_path)
    diagram = generate_plantuml(schema, title="demo_input_dataset deployment")
    output_path.write_text(diagram, encoding="utf-8")

    print(f"Read JSON dataset: {input_path}")
    print(f"Wrote PlantUML diagram: {output_path}")


if __name__ == "__main__":
    main()

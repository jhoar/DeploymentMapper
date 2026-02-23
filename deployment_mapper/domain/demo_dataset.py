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


DEMO_DATASET_NAME = "baseline-demo"


def build_demo_schema() -> DeploymentSchema:
    """Build a valid demonstration input dataset for the domain schema."""

    schema = DeploymentSchema(
        subnets=[
            Subnet(id="subnet-prod", cidr="10.0.0.0/24", name="production"),
            Subnet(id="subnet-mgmt", cidr="10.0.1.0/24", name="management"),
        ],
        hardware_nodes=[
            HardwareNode(
                id="node-baremetal-01",
                hostname="bm-prod-01",
                ip_address="10.0.0.10",
                subnet_id="subnet-prod",
                kind=NodeKind.PHYSICAL,
            ),
            HardwareNode(
                id="node-k8s-worker-01",
                hostname="k8s-worker-01",
                ip_address="10.0.0.11",
                subnet_id="subnet-prod",
                kind=NodeKind.K8S_NODE,
            ),
        ],
        kubernetes_clusters=[
            KubernetesCluster(
                id="cluster-prod-01",
                name="prod-cluster",
                subnet_id="subnet-prod",
                node_ids=["node-k8s-worker-01"],
            )
        ],
        virtual_machines=[
            VirtualMachine(
                id="vm-app-01",
                hostname="vm-app-01",
                ip_address="10.0.0.21",
                subnet_id="subnet-prod",
                host_node_id="node-baremetal-01",
            )
        ],
        storage_servers=[
            StorageServer(
                id="storage-nas-01",
                hostname="nas-01",
                ip_address="10.0.1.30",
                subnet_id="subnet-mgmt",
            )
        ],
        network_switches=[
            NetworkSwitch(
                id="switch-core-01",
                hostname="sw-core-01",
                management_ip="10.0.1.40",
                subnet_id="subnet-mgmt",
            )
        ],
        software_systems=[
            SoftwareSystem(id="sys-payments", name="payments-api", version="2.4.1"),
            SoftwareSystem(id="sys-observability", name="observability-stack", version="1.7.0"),
        ],
        deployment_instances=[
            DeploymentInstance(
                id="deploy-payments-vm",
                system_id="sys-payments",
                target_kind=DeploymentTargetKind.VM,
                target_node_id="vm-app-01",
                component_id="payments-service",
            ),
            DeploymentInstance(
                id="deploy-observability-ns",
                system_id="sys-observability",
                target_kind=DeploymentTargetKind.K8S_NAMESPACE,
                target_cluster_id="cluster-prod-01",
                namespace="monitoring",
                component_id="prometheus",
            ),
        ],
    )

    schema.validate()
    return schema


def main() -> None:
    """CLI entrypoint for running the demo dataset builder as a module."""

    schema = build_demo_schema()
    print(f"Loaded demo: {DEMO_DATASET_NAME}")
    print(f"Subnets: {len(schema.subnets)}")
    print(f"Deployment instances: {len(schema.deployment_instances)}")


if __name__ == "__main__":
    main()

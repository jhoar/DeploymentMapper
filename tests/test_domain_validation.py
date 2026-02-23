from __future__ import annotations

import unittest

from deployment_mapper.domain.models import (
    DeploymentInstance,
    DeploymentSchema,
    DeploymentTargetKind,
    HardwareNode,
    KubernetesCluster,
    SoftwareSystem,
    Subnet,
    ValidationError,
    VirtualMachine,
)


class DomainValidationTests(unittest.TestCase):
    def test_duplicate_subnet_cidr_is_rejected(self) -> None:
        schema = DeploymentSchema(
            subnets=[
                Subnet(id="sn-a", cidr="10.0.0.0/24", name="App"),
                Subnet(id="sn-b", cidr="10.0.0.0/24", name="Duplicate"),
            ]
        )

        with self.assertRaisesRegex(ValidationError, "subnet.cidr"):
            schema.validate()

    def test_vm_target_requires_target_node_id(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-a", cidr="10.0.0.0/24", name="App")],
            kubernetes_clusters=[KubernetesCluster(id="cluster-1", name="k8s", subnet_id="sn-a")],
            software_systems=[SoftwareSystem(id="sys-1", name="Orders")],
            deployment_instances=[
                DeploymentInstance(
                    id="dep-1",
                    system_id="sys-1",
                    target_kind=DeploymentTargetKind.VM,
                )
            ],
        )

        with self.assertRaisesRegex(ValidationError, "target_node_id"):
            schema.validate()

    def test_namespace_target_requires_namespace_value(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-a", cidr="10.0.0.0/24", name="App")],
            hardware_nodes=[
                HardwareNode(
                    id="node-1",
                    hostname="node-1",
                    ip_address="10.0.0.10",
                    subnet_id="sn-a",
                )
            ],
            kubernetes_clusters=[KubernetesCluster(id="cluster-1", name="k8s", subnet_id="sn-a")],
            software_systems=[SoftwareSystem(id="sys-1", name="Orders")],
            deployment_instances=[
                DeploymentInstance(
                    id="dep-1",
                    system_id="sys-1",
                    target_kind=DeploymentTargetKind.K8S_NAMESPACE,
                    target_cluster_id="cluster-1",
                    namespace="",
                )
            ],
        )

        with self.assertRaisesRegex(ValidationError, "namespace"):
            schema.validate()

    def test_duplicate_ip_address_within_subnet_is_rejected(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-a", cidr="10.0.0.0/24", name="App")],
            hardware_nodes=[
                HardwareNode(
                    id="host-1",
                    hostname="host-1",
                    ip_address="10.0.0.10",
                    subnet_id="sn-a",
                )
            ],
            virtual_machines=[
                VirtualMachine(
                    id="vm-1",
                    hostname="vm-1",
                    ip_address="10.0.0.10",
                    subnet_id="sn-a",
                    host_node_id="host-1",
                )
            ],
        )

        with self.assertRaisesRegex(ValidationError, "duplicate"):
            schema.validate()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from deployment_mapper.domain.models import DeploymentSchema, HardwareNode, Subnet, ValidationError, VirtualMachine
from deployment_mapper.ingestion.manifest_importer import import_manifest
from deployment_mapper.validation import validate_schema_for_import, validate_topology_for_diagram


class ValidationModuleTests(unittest.TestCase):
    def test_missing_foreign_key_reference_fails_fast(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-app", cidr="10.0.0.0/24", name="App")],
            virtual_machines=[
                VirtualMachine(
                    id="vm-1",
                    hostname="vm-1",
                    ip_address="10.0.0.20",
                    subnet_id="sn-app",
                    host_node_id="host-missing",
                )
            ],
        )

        with self.assertRaisesRegex(ValidationError, "missing foreign key reference"):
            validate_schema_for_import(schema)

    def test_invalid_subnet_cidr_assignment_fails_fast(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-app", cidr="10.0.0.0/24", name="App")],
            hardware_nodes=[
                HardwareNode(
                    id="host-1",
                    hostname="host-1",
                    ip_address="10.0.1.10",
                    subnet_id="sn-app",
                )
            ],
        )

        with self.assertRaisesRegex(ValidationError, "invalid subnet/CIDR assignment"):
            validate_schema_for_import(schema)

    def test_duplicate_addressing_conflict_fails_fast(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="sn-app", cidr="10.0.0.0/24", name="App")],
            hardware_nodes=[
                HardwareNode(
                    id="host-1",
                    hostname="host-1",
                    ip_address="10.0.0.10",
                    subnet_id="sn-app",
                ),
                HardwareNode(
                    id="host-2",
                    hostname="host-2",
                    ip_address="10.0.0.10",
                    subnet_id="sn-app",
                ),
            ],
        )

        with self.assertRaisesRegex(ValidationError, "duplicate addressing conflict"):
            validate_schema_for_import(schema)

    def test_import_manifest_rejects_unsupported_target_kind(self) -> None:
        payload = {
            "subnets": [{"id": "sn-app", "cidr": "10.0.0.0/24", "name": "App"}],
            "hardware_nodes": [
                {
                    "id": "host-1",
                    "hostname": "host-1",
                    "ip_address": "10.0.0.10",
                    "subnet_id": "sn-app",
                }
            ],
            "software_systems": [{"id": "sys-1", "name": "Orders"}],
            "deployment_instances": [
                {
                    "id": "dep-1",
                    "system_id": "sys-1",
                    "target_kind": "EDGE_RUNTIME",
                    "target_node_id": "host-1",
                }
            ],
        }

        with self.assertRaisesRegex(ValidationError, "unsupported target_kind"):
            import_manifest(payload)

    def test_diagram_validation_rejects_unsupported_target_kind(self) -> None:
        topology = {
            "system": {"id": "sys-1", "name": "Orders"},
            "subnets": [{"id": "sn-app", "cidr": "10.0.0.0/24", "name": "App"}],
            "hardware_nodes": [
                {
                    "id": "host-1",
                    "hostname": "host-1",
                    "ip_address": "10.0.0.10",
                    "subnet_id": "sn-app",
                }
            ],
            "virtual_machines": [],
            "kubernetes_clusters": [],
            "deployments": [
                {
                    "id": "dep-1",
                    "system_id": "sys-1",
                    "target_kind": "EDGE_RUNTIME",
                    "target_node_id": "host-1",
                }
            ],
        }

        with self.assertRaisesRegex(ValidationError, "unsupported target_kind"):
            validate_topology_for_diagram("sys-1", topology)


if __name__ == "__main__":
    unittest.main()

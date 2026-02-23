from __future__ import annotations

import re
import unittest

from deployment_mapper.domain.models import (
    DeploymentInstance,
    DeploymentSchema,
    DeploymentTargetKind,
    HardwareNode,
    SoftwareSystem,
    Subnet,
)
from deployment_mapper.domain.uml_demo import generate_plantuml


class UmlAliasSafetyTests(unittest.TestCase):
    def test_generated_aliases_are_plantuml_safe(self) -> None:
        schema = DeploymentSchema(
            subnets=[Subnet(id="01 subnet/main", cidr="10.0.0.0/24", name="App")],
            hardware_nodes=[
                HardwareNode(
                    id="host-1.prod/main",
                    hostname="host-1",
                    ip_address="10.0.0.10",
                    subnet_id="01 subnet/main",
                )
            ],
            software_systems=[SoftwareSystem(id="sys/orders-service", name="Orders")],
            deployment_instances=[
                DeploymentInstance(
                    id="dep orders@v1",
                    system_id="sys/orders-service",
                    target_kind=DeploymentTargetKind.HOST,
                    target_node_id="host-1.prod/main",
                )
            ],
        )

        puml = generate_plantuml(schema)
        alias_matches = re.findall(r"\bas\s+([A-Za-z0-9_]+)", puml)

        self.assertGreater(len(alias_matches), 0)
        for alias in alias_matches:
            self.assertRegex(alias, r"^[A-Za-z_][A-Za-z0-9_]*$")


if __name__ == "__main__":
    unittest.main()

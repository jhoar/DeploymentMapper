from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from deployment_mapper.domain.json_loader import parse_schema_payload
from deployment_mapper.domain.json_uml_demo import load_schema_from_json_file
from deployment_mapper.domain.models import DeploymentTargetKind, NodeKind, ValidationError


class JsonLoaderTests(unittest.TestCase):
    def test_parse_schema_payload_from_example(self) -> None:
        payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))
        schema = parse_schema_payload(payload)
        self.assertGreater(len(schema.subnets), 0)
        self.assertGreater(len(schema.deployment_instances), 0)

    def test_load_schema_from_json_file_uses_shared_parser(self) -> None:
        payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))
        payload["subnets"][0]["cidr"] = "invalid-cidr"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_schema_from_json_file(path)

    def test_enum_values_are_parsed_into_domain_enums(self) -> None:
        payload = {
            "subnets": [{"id": "sn-a", "cidr": "10.0.0.0/24", "name": "App"}],
            "hardware_nodes": [
                {
                    "id": "host-1",
                    "hostname": "host-1",
                    "ip_address": "10.0.0.10",
                    "subnet_id": "sn-a",
                    "kind": "K8S_NODE",
                }
            ],
            "software_systems": [{"id": "sys-1", "name": "Orders"}],
            "deployment_instances": [
                {
                    "id": "dep-1",
                    "system_id": "sys-1",
                    "target_kind": "HOST",
                    "target_node_id": "host-1",
                }
            ],
        }

        schema = parse_schema_payload(payload)
        self.assertIs(schema.hardware_nodes[0].kind, NodeKind.K8S_NODE)
        self.assertIs(schema.deployment_instances[0].target_kind, DeploymentTargetKind.HOST)

    def test_missing_required_fields_bubble_as_key_errors(self) -> None:
        payload = {
            "subnets": [{"id": "sn-a", "cidr": "10.0.0.0/24", "name": "App"}],
            "hardware_nodes": [
                {
                    "id": "host-1",
                    "hostname": "host-1",
                    "subnet_id": "sn-a",
                }
            ],
        }

        with self.assertRaises(KeyError):
            parse_schema_payload(payload)

    def test_invalid_references_are_rejected_during_schema_validation(self) -> None:
        payload = {
            "subnets": [{"id": "sn-a", "cidr": "10.0.0.0/24", "name": "App"}],
            "hardware_nodes": [
                {
                    "id": "host-1",
                    "hostname": "host-1",
                    "ip_address": "10.0.0.10",
                    "subnet_id": "sn-a",
                }
            ],
            "virtual_machines": [
                {
                    "id": "vm-1",
                    "hostname": "vm-1",
                    "ip_address": "10.0.0.20",
                    "subnet_id": "sn-a",
                    "host_node_id": "host-missing",
                }
            ],
        }

        with self.assertRaisesRegex(ValidationError, "does not reference an existing object"):
            parse_schema_payload(payload)


if __name__ == "__main__":
    unittest.main()

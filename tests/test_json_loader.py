from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from deployment_mapper.domain.json_loader import parse_schema_payload
from deployment_mapper.domain.json_uml_demo import load_schema_from_json_file
from deployment_mapper.domain.models import ValidationError


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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
_HAS_HTTPX = importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(_HAS_FASTAPI and _HAS_HTTPX, "fastapi/httpx not installed")
class ApiValidateEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        from deployment_mapper.api.main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self.payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))

    def test_validate_schema_success(self) -> None:
        response = self.client.post("/schemas/validate", json=self.payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["errors"], [])
        self.assertGreater(data["counts"]["subnets"], 0)

    def test_validate_schema_invalid_payload(self) -> None:
        invalid_payload = dict(self.payload)
        invalid_payload["subnets"] = [{"id": "sn-a", "cidr": "bad-cidr", "name": "App"}]

        response = self.client.post("/schemas/validate", json=invalid_payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertGreater(len(data["errors"]), 0)


if __name__ == "__main__":
    unittest.main()

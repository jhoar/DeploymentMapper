from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
_HAS_HTTPX = importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(_HAS_FASTAPI and _HAS_HTTPX, "fastapi/httpx not installed")
class ApiObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        from deployment_mapper.api.main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self.payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))

    def test_metrics_endpoint_exposes_prometheus_counters(self) -> None:
        self.client.get("/healthz")
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("deployment_mapper_http_requests_total", response.text)
        self.assertIn("deployment_mapper_http_request_duration_seconds", response.text)
        self.assertIn("deployment_mapper_http_request_errors_total", response.text)

    def test_metrics_error_counter_increments(self) -> None:
        invalid_payload = dict(self.payload)
        invalid_payload["subnets"] = [{"id": "sn-a", "cidr": "bad-cidr", "name": "App"}]
        self.client.post("/schemas/validate", json=invalid_payload)

        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn('deployment_mapper_http_request_errors_total{method="POST",path="/schemas/validate",status_code="422"}', response.text)


if __name__ == "__main__":
    unittest.main()

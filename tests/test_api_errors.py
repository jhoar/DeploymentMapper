from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
_HAS_HTTPX = importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(_HAS_FASTAPI and _HAS_HTTPX, "fastapi/httpx not installed")
class ApiErrorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        from deployment_mapper.api.main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self.payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))

    def _assert_request_id_contract(self, response: object) -> None:
        request_id_header = response.headers.get("X-Request-ID")
        self.assertIsNotNone(request_id_header)
        self.assertTrue(request_id_header)

        body = response.json()
        self.assertIn("request_id", body)
        self.assertEqual(body["request_id"], request_id_header)

    def test_auth_http_exceptions_use_auth_error_code_for_401_and_403(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DEPLOYMENT_MAPPER_AUTH_MODE": "api_key",
                "DEPLOYMENT_MAPPER_API_KEYS_READER": "reader-key",
            },
            clear=False,
        ):
            unauthorized = self.client.post("/schemas/validate", json=self.payload)
            self.assertEqual(unauthorized.status_code, 401)
            self.assertEqual(unauthorized.json()["code"], "AUTH_ERROR")
            self._assert_request_id_contract(unauthorized)

            forbidden = self.client.post(
                "/schemas/validate",
                json=self.payload,
                headers={"X-API-Key": "reader-key"},
            )
            self.assertEqual(forbidden.status_code, 403)
            self.assertEqual(forbidden.json()["code"], "AUTH_ERROR")
            self._assert_request_id_contract(forbidden)

    def test_non_auth_http_exceptions_use_http_error_code(self) -> None:
        response = self.client.get("/diagrams/artifacts/missing-request/missing-artifact.txt")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "HTTP_ERROR")
        self._assert_request_id_contract(response)

    def test_fastapi_request_validation_uses_request_validation_error_code(self) -> None:
        response = self.client.post("/schemas/validate", json=["not-a-dict-payload"])

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["code"], "REQUEST_VALIDATION_ERROR")
        self.assertGreater(len(body["details"]), 0)
        self._assert_request_id_contract(response)


if __name__ == "__main__":
    unittest.main()

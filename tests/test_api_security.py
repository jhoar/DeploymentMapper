from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deployment_mapper.artifacts import LocalArtifactStore


@unittest.skipUnless(__import__("importlib").util.find_spec("fastapi") is not None, "fastapi not installed")
class ApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        from deployment_mapper.api import security
        from deployment_mapper.api.main import app
        from deployment_mapper.api.routers import diagrams
        from fastapi.testclient import TestClient

        self.security = security
        self.diagrams = diagrams
        self.client = TestClient(app)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.diagrams.artifact_store = LocalArtifactStore(base_dir=self.tmpdir.name)
        self.payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))
        self.payload["request_id"] = "sec-test"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_editor_can_validate_and_reader_cannot(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DEPLOYMENT_MAPPER_AUTH_MODE": "api_key",
                "DEPLOYMENT_MAPPER_API_KEYS_READER": "reader-key",
                "DEPLOYMENT_MAPPER_API_KEYS_EDITOR": "editor-key",
            },
            clear=False,
        ):
            unauthorized = self.client.post("/schemas/validate", json=self.payload, headers={"X-API-Key": "reader-key"})
            self.assertEqual(unauthorized.status_code, 403)

            authorized = self.client.post("/schemas/validate", json=self.payload, headers={"X-API-Key": "editor-key"})
            self.assertEqual(authorized.status_code, 200)
            self.assertTrue(authorized.json()["valid"])

    def test_reader_can_list_and_read_artifacts(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DEPLOYMENT_MAPPER_AUTH_MODE": "api_key",
                "DEPLOYMENT_MAPPER_API_KEYS_READER": "reader-key",
                "DEPLOYMENT_MAPPER_API_KEYS_EDITOR": "editor-key",
            },
            clear=False,
        ):
            create_resp = self.client.post("/diagrams/plantuml", json=self.payload, headers={"X-API-Key": "editor-key"})
            self.assertEqual(create_resp.status_code, 200)
            artifact_path = Path(create_resp.json()["artifact_path"])

            list_resp = self.client.get("/diagrams/artifacts", headers={"X-API-Key": "reader-key"})
            self.assertEqual(list_resp.status_code, 200)
            self.assertGreaterEqual(list_resp.json()["count"], 1)

            read_resp = self.client.get(
                f"/diagrams/artifacts/{self.payload['request_id']}/{artifact_path.name}",
                headers={"X-API-Key": "reader-key"},
            )
            self.assertEqual(read_resp.status_code, 200)
            self.assertIn("@startuml", read_resp.json()["content"])

    def test_admin_endpoints_require_admin_role(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DEPLOYMENT_MAPPER_AUTH_MODE": "api_key",
                "DEPLOYMENT_MAPPER_API_KEYS_READER": "reader-key",
                "DEPLOYMENT_MAPPER_API_KEYS_ADMIN": "admin-key",
            },
            clear=False,
        ):
            forbidden = self.client.get("/diagrams/admin/config", headers={"X-API-Key": "reader-key"})
            self.assertEqual(forbidden.status_code, 403)

            allowed = self.client.get("/diagrams/admin/config", headers={"X-API-Key": "admin-key"})
            self.assertEqual(allowed.status_code, 200)
            self.assertIn("base_dir", allowed.json())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(__import__("importlib").util.find_spec("fastapi") is not None, "fastapi not installed")
class ApiDiagramsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        from deployment_mapper.api.main import app
        from deployment_mapper.api.routers import diagrams
        from deployment_mapper.artifacts import LocalArtifactStore
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self.diagrams = diagrams
        self.tmpdir = tempfile.TemporaryDirectory()
        self.diagrams.artifact_store = LocalArtifactStore(base_dir=self.tmpdir.name)
        self.payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))
        self.payload["request_id"] = "api-diagram-test"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_generate_plantuml_and_fetch_artifact(self) -> None:
        create_response = self.client.post("/diagrams/plantuml", json=self.payload)
        self.assertEqual(create_response.status_code, 200)

        created = create_response.json()
        self.assertTrue(created["valid"])
        self.assertIn("@startuml", created["puml"])

        artifact_path = Path(created["artifact_path"])
        list_response = self.client.get("/diagrams/artifacts")
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(list_response.json()["count"], 1)

        read_response = self.client.get(f"/diagrams/artifacts/{self.payload['request_id']}/{artifact_path.name}")
        self.assertEqual(read_response.status_code, 200)
        self.assertIn("@startuml", read_response.json()["content"])

    def test_render_endpoint_returns_stubbed_message(self) -> None:
        response = self.client.post("/diagrams/render", json=self.payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["valid"])
        self.assertFalse(body["rendered"])
        self.assertIn("not enabled", body["message"])


if __name__ == "__main__":
    unittest.main()

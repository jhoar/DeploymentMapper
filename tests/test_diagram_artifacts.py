from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class DiagramArtifactEndpointTests(unittest.TestCase):
    @unittest.skipUnless(__import__("importlib").util.find_spec("fastapi") is not None, "fastapi not installed")
    def test_build_plantuml_writes_artifact(self) -> None:
        from deployment_mapper.api.routers import diagrams

        payload = json.loads(Path("examples/demo_input_dataset.json").read_text(encoding="utf-8"))
        payload["request_id"] = "endpoint-test"

        with tempfile.TemporaryDirectory() as tmp:
            diagrams.artifact_store = diagrams.LocalArtifactStore(base_dir=tmp)
            result = diagrams.build_plantuml(payload)

            self.assertTrue(result["valid"])
            artifact_path = Path(result["artifact_path"])
            self.assertTrue(artifact_path.exists())
            self.assertTrue(artifact_path.name.endswith(".puml"))
            self.assertEqual(result["artifact_metadata"]["source_schema_id"], payload.get("schema_id"))


if __name__ == "__main__":
    unittest.main()

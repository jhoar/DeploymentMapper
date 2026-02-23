from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from deployment_mapper.cli import main
from deployment_mapper.persistence import DeploymentRepository, apply_migrations


class CliCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.db"
        connection = sqlite3.connect(self.db_path)
        apply_migrations(connection, Path("deployment_mapper/persistence/migrations"))
        self.repository = DeploymentRepository(connection)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_get_system_topology_returns_transitive_relations(self) -> None:
        topology = self.repository.get_system_topology("system-orders")
        self.assertEqual(topology["system"]["id"], "system-orders")
        self.assertTrue(topology["relations"])
        relation = topology["relations"][0]
        self.assertIn("component_id", relation)
        self.assertIn("deployment_id", relation)
        self.assertIn("subnet_id", relation)

    def test_get_subnet_deployments_returns_systems(self) -> None:
        payload = self.repository.get_subnet_deployments("subnet-app")
        self.assertEqual(payload["subnet"]["id"], "subnet-app")
        self.assertTrue(payload["systems"])
        self.assertTrue(payload["relations"])

    def test_cli_get_system_topology_prints_summary_and_json(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--db", str(self.db_path), "get-system-topology", "system-orders"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("System:", output)
        self.assertIn("JSON:", output)
        self.assertIn('"relations"', output)

    def test_cli_generate_deployment_diagram_puml(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(
                [
                    "--db",
                    str(self.db_path),
                    "generate-deployment-diagram",
                    "system-orders",
                    "--format",
                    "puml",
                ]
            )

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Generated PlantUML", output)
        self.assertIn("@startuml", output)


if __name__ == "__main__":
    unittest.main()

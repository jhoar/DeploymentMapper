from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deployment_mapper.diagram.plantuml_renderer import (
    PlantUMLRenderer,
    _deterministic_node_id,
    _escape_label,
    render_system_topology,
)


class PlantUMLRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = PlantUMLRenderer()

    def test_escape_label(self) -> None:
        escaped = _escape_label('api "edge" \\ live\nline2')
        self.assertEqual(escaped, 'api \\"edge\\" \\\\ live\\nline2')

    def test_deterministic_node_id_is_stable(self) -> None:
        self.assertEqual(_deterministic_node_id("node", "abc"), _deterministic_node_id("node", "abc"))

    def test_render_puml_contains_required_shapes(self) -> None:
        topology = {
            "system": {"id": "sys1", "name": "Checkout", "version": "1.2.3"},
            "subnets": [{"id": "sn1", "name": "App", "cidr": "10.0.0.0/24"}],
            "hardware_nodes": [
                {"id": "hw1", "hostname": "metal-1", "ip_address": "10.0.0.10", "subnet_id": "sn1"}
            ],
            "virtual_machines": [
                {
                    "id": "vm1",
                    "hostname": "vm-1",
                    "ip_address": "10.0.0.20",
                    "subnet_id": "sn1",
                    "host_node_id": "hw1",
                }
            ],
            "kubernetes_clusters": [{"id": "k1", "name": "prod-cluster", "subnet_id": "sn1"}],
            "deployments": [
                {
                    "id": "d1",
                    "target_kind": "HOST",
                    "target_node_id": "hw1",
                    "component_id": "comp-api",
                    "component_name": "API",
                },
                {
                    "id": "d2",
                    "target_kind": "K8S_NAMESPACE",
                    "target_cluster_id": "k1",
                    "namespace": "payments",
                    "component_id": "comp-worker",
                    "component_name": "Worker",
                },
            ],
            "clusters": {"k1": [{"node_id": "hw1"}]},
            "dependencies": [{"id": "dep1", "from_component_id": "comp-worker", "to_component_id": "comp-api"}],
            "network_links": [
                {
                    "id": "net1",
                    "source_type": "vm",
                    "source_id": "vm1",
                    "target_type": "hardware",
                    "target_id": "hw1",
                    "label": "tcp/443",
                }
            ],
        }

        puml = self.renderer.render_puml(system_id="sys1", topology=topology)

        self.assertIn("package \"App\\\\n10.0.0.0/24\"", puml)
        self.assertIn("node \"metal-1\\\\n10.0.0.10\"", puml)
        self.assertIn("artifact \"API\"", puml)
        self.assertIn(": deployed on", puml)
        self.assertIn(": depends on", puml)
        self.assertIn(": tcp/443", puml)

    def test_render_system_topology_does_not_fail_without_plantuml(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            result = render_system_topology("sys1", {}, output_image="out.png")
        self.assertIsNotNone(result["puml"])
        self.assertIsNone(result["image_path"])

    def test_render_image_writes_file_when_runtime_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "diagram.png"
            with mock.patch("shutil.which", return_value="/usr/bin/plantuml"):
                process = mock.Mock(returncode=0, stdout=b"img")
                with mock.patch("subprocess.run", return_value=process):
                    image = self.renderer.render_image("@startuml\n@enduml\n", output)
            self.assertEqual(image, output)
            self.assertEqual(output.read_bytes(), b"img")


if __name__ == "__main__":
    unittest.main()

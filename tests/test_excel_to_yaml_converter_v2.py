import tempfile
import unittest
from pathlib import Path

import yaml

from tools.excel_to_yaml_converter_v2 import convert_excel_to_manifest


class ExcelToYamlConverterV2Tests(unittest.TestCase):
    def test_example_workbook_generates_expected_shape(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        input_file = repo_root / "examples" / "deployment_mapper_from_example_yaml.xlsx"
        self.assertTrue(input_file.exists(), f"Missing test input workbook: {input_file}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "manifest.yaml"
            convert_excel_to_manifest(str(input_file), str(output_file))
            self.assertTrue(output_file.exists(), "Converter did not create output YAML file.")

            with output_file.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)

        self.assertIsInstance(data, dict)
        self.assertIn("Manifest", data)
        self.assertIn("Deployments", data)
        self.assertIn("NodeRoles", data)
        self.assertIn("K8sServices", data)

        deployments = data["Deployments"]
        self.assertTrue(deployments)
        self.assertTrue(any("targets" in dep for dep in deployments))

        k8s_services = data["K8sServices"]
        self.assertTrue(k8s_services)
        for svc in k8s_services:
            if "routesToWorkload" in svc:
                self.assertIn("kind", svc["routesToWorkload"])
                self.assertIn("workloadName", svc["routesToWorkload"])
                self.assertTrue(str(svc["routesToWorkload"]["kind"]).strip())
                self.assertTrue(str(svc["routesToWorkload"]["workloadName"]).strip())


if __name__ == "__main__":
    unittest.main()

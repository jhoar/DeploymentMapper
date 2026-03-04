import argparse
from pathlib import Path

import pandas as pd
import yaml

INPUT_FILE = "deployment_mapper_template.xlsx"
OUTPUT_FILE = "deployment_manifest.yaml"

REQUIRED_SHEETS = [
    "Organizations",
    "Projects",
    "Applications",
    "Components",
    "Environments",
    "Nodes",
    "NodeRoles",
    "Clusters",
    "ClusterRoles",
    "ClusterEndpoints",
    "Deployments",
    "Filers",
    "FilerRoles",
    "Volumes",
    "Mounts",
    "Networks",
    "Subnets",
    "SubnetConnections",
]


def convert_excel_to_manifest(input_file: str, output_file: str) -> None:
    xls = pd.ExcelFile(input_file)
    data = {}
    missing = [sheet for sheet in REQUIRED_SHEETS if sheet not in xls.sheet_names]
    if missing:
        raise ValueError(f"Missing required sheets: {missing}")

    for sheet in REQUIRED_SHEETS:
        df = pd.read_excel(xls, sheet_name=sheet).dropna(how="all")
        data[sheet] = df.fillna("").to_dict(orient="records")

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)

    print(f"YAML file written to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert deployment mapper workbook template to YAML.")
    parser.add_argument("--input", default=INPUT_FILE, help="Path to source Excel workbook.")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Path to output YAML file.")
    args = parser.parse_args()

    input_file = str(Path(args.input))
    output_file = str(Path(args.output))
    convert_excel_to_manifest(input_file, output_file)

if __name__ == "__main__":
    main()

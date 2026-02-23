from __future__ import annotations

from pathlib import Path

from .json_loader import load_schema_from_json_file
from .uml_demo import generate_plantuml


def main() -> None:
    """Read the example JSON dataset and write a UML .puml file."""

    input_path = Path("examples/demo_input_dataset.json")
    output_path = Path("examples/demo_input_dataset_diagram.puml")

    schema = load_schema_from_json_file(input_path)
    diagram = generate_plantuml(schema, title="demo_input_dataset deployment")
    output_path.write_text(diagram, encoding="utf-8")

    print(f"Read JSON dataset: {input_path}")
    print(f"Wrote PlantUML diagram: {output_path}")


if __name__ == "__main__":
    main()

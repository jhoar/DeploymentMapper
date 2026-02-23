from __future__ import annotations

from pathlib import Path

from deployment_mapper.artifacts import LocalArtifactStore

from .json_loader import load_schema_from_json_file
from .uml_demo import generate_plantuml


def main() -> None:
    """Read the example JSON dataset and write a UML .puml file."""

    input_path = Path("examples/demo_input_dataset.json")

    schema = load_schema_from_json_file(input_path)
    diagram = generate_plantuml(schema, title="demo_input_dataset deployment")

    artifact_store = LocalArtifactStore(base_dir="examples")
    stored_artifact = artifact_store.write_text(
        request_id="demo_input_dataset_diagram",
        schema_payload={"schema_id": "demo_input_dataset", "schema_version": "1"},
        content=diagram,
        content_type="text/plantuml",
    )

    print(f"Read JSON dataset: {input_path}")
    print(f"Wrote PlantUML diagram: {stored_artifact.path}")


if __name__ == "__main__":
    main()

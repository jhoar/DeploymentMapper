# Deployment Mapper (Neo4j + YAML Manifests)

This folder is a starter **Codex project** for a software deployment mapper.

## Included
- `docs/neo4j_schema_deployment_mapper.md`
- `templates/deployment_mapper_template.xlsx`
- `tools/excel_to_yaml_converter.py`
- `examples/acme_example_manifest.yaml`
- `PLANS.md` and `CODEX_CONTEXT.md`

Generated: 2026-03-04

## Quick start
- Install dependencies: `python -m pip install -r requirements.txt`
- Convert the template workbook: `python tools/excel_to_yaml_converter.py --input templates/deployment_mapper_template.xlsx --output deployment_manifest.yaml`
- Convert the example workbook: `python tools/excel_to_yaml_converter_v2.py --input examples/deployment_mapper_from_example_yaml.xlsx --output deployment_manifest.yaml`

## Java application
- Build: `mvn clean package`
- Run tests: `mvn test`
- Run CLI:
  - `java -jar target/deployment-mapper-1.0.0-SNAPSHOT.jar --input examples/acme_example_manifest.yaml --output-dir out --clean-db`
  - `--input` accepts repeated files and/or directories (recursive `.yaml`/`.yml` scan)
  - Outputs: `out/deployment-map.puml`, `out/deployment-map.png`, and embedded Neo4j data under `out/neo4j-db` (or `--db-path`)

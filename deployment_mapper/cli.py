from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from deployment_mapper.diagram.plantuml_renderer import render_system_topology
from deployment_mapper.domain.models import ValidationError
from deployment_mapper.persistence.repository import DeploymentRepository
from deployment_mapper.validation import validate_topology_for_diagram


def _build_system_summary(topology: dict[str, Any]) -> str:
    system = topology["system"]
    relations = topology.get("relations", [])
    components = {row.get("component_id") for row in relations if row.get("component_id")}
    subnets = {(row.get("subnet_id"), row.get("subnet_name")) for row in relations}
    lines = [
        f"System: {system['name']} ({system['id']})",
        f"Version: {system.get('version') or 'n/a'}",
        f"Components: {len(components)}",
        f"Deployments: {len(relations)}",
        f"Subnets: {', '.join(sorted(name for _, name in subnets if name)) or 'none'}",
    ]
    return "\n".join(lines)


def _build_subnet_summary(payload: dict[str, Any]) -> str:
    subnet = payload["subnet"]
    systems = payload.get("systems", [])
    deployment_count = sum(
        len(component.get("deployments", []))
        for system in systems
        for component in system.get("components", [])
    )
    lines = [
        f"Subnet: {subnet['name']} ({subnet['id']})",
        f"CIDR: {subnet['cidr']}",
        f"Systems deployed: {len(systems)}",
        f"Deployments in subnet: {deployment_count}",
    ]
    return "\n".join(lines)


def _emit_result(summary: str, payload: dict[str, Any]) -> None:
    print(summary)
    print("\nJSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))


def _connect_repository(db_path: str) -> DeploymentRepository:
    connection = sqlite3.connect(db_path)
    return DeploymentRepository(connection)


def _handle_get_system_topology(repository: DeploymentRepository, system_id: str) -> int:
    topology = repository.get_system_topology(system_id)
    if not topology:
        print(f"System '{system_id}' not found")
        return 1
    _emit_result(_build_system_summary(topology), topology)
    return 0


def _handle_get_subnet_deployments(repository: DeploymentRepository, subnet_id: str) -> int:
    payload = repository.get_subnet_deployments(subnet_id)
    if not payload:
        print(f"Subnet '{subnet_id}' not found")
        return 1
    _emit_result(_build_subnet_summary(payload), payload)
    return 0


def _handle_generate_deployment_diagram(
    repository: DeploymentRepository,
    system_id: str,
    output_format: str,
    output: str | None,
) -> int:
    topology = repository.get_system_topology(system_id)
    if not topology:
        print(f"System '{system_id}' not found")
        return 1

    try:
        validate_topology_for_diagram(system_id, topology)
    except ValidationError as exc:
        print(f"Validation failed: {exc}")
        return 1

    if output_format == "puml":
        rendered = render_system_topology(system_id, topology)
        payload = {
            "system_id": system_id,
            "format": "puml",
            "puml": rendered["puml"],
        }
        summary = f"Generated PlantUML for system {system_id}"
        _emit_result(summary, payload)
        return 0

    output_path = Path(output) if output else Path(f"{system_id}-deployment.{output_format}")
    rendered = render_system_topology(system_id, topology, output_image=output_path)
    payload = {
        "system_id": system_id,
        "format": output_format,
        "output_path": str(output_path),
        "image_path": rendered["image_path"],
        "puml": rendered["puml"],
    }
    summary = (
        f"Generated {output_format.upper()} diagram at {output_path}"
        if rendered["image_path"]
        else f"PlantUML runtime unavailable; generated PUML only for {system_id}"
    )
    _emit_result(summary, payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deployment-mapper")
    parser.add_argument("--db", default="deployment_mapper.db", help="Path to the sqlite database")

    subparsers = parser.add_subparsers(dest="command", required=True)

    system_parser = subparsers.add_parser("get-system-topology", help="Resolve full system topology")
    system_parser.add_argument("system_id")

    subnet_parser = subparsers.add_parser("get-subnet-deployments", help="List deployments in a subnet")
    subnet_parser.add_argument("subnet_id")

    diagram_parser = subparsers.add_parser(
        "generate-deployment-diagram",
        help="Generate deployment diagram for a system",
    )
    diagram_parser.add_argument("system_id")
    diagram_parser.add_argument("--format", required=True, choices=["puml", "png", "svg"])
    diagram_parser.add_argument("--output", help="Optional output file path for diagram files")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repository = _connect_repository(args.db)

    if args.command == "get-system-topology":
        return _handle_get_system_topology(repository, args.system_id)

    if args.command == "get-subnet-deployments":
        return _handle_get_subnet_deployments(repository, args.subnet_id)

    if args.command == "generate-deployment-diagram":
        return _handle_generate_deployment_diagram(repository, args.system_id, args.format, args.output)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

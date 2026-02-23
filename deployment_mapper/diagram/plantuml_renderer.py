from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _escape_label(value: str) -> str:
    """Escape a label so it remains valid PlantUML text."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _deterministic_node_id(prefix: str, raw_id: str) -> str:
    """Return a stable PlantUML alias for a topology entity."""
    digest = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


class PlantUMLRenderer:
    """Render deployment topology data into PlantUML deployment diagrams."""

    def render_puml(self, system_id: str, topology: dict[str, Any]) -> str:
        lines = ["@startuml", "skinparam shadowing false", "left to right direction"]

        system = topology.get("system") or {"id": system_id, "name": system_id, "version": None}
        title = f"{system.get('name', system_id)}"
        if system.get("version"):
            title = f"{title} v{system['version']}"
        lines.append(f'title {_escape_label(title)}')

        node_alias: dict[tuple[str, str], str] = {}
        artifact_alias: dict[str, str] = {}

        subnets = sorted(topology.get("subnets", []), key=lambda subnet: subnet.get("id", ""))
        hardware = sorted(topology.get("hardware_nodes", []), key=lambda node: node.get("id", ""))
        vms = sorted(topology.get("virtual_machines", []), key=lambda vm: vm.get("id", ""))
        clusters = sorted(topology.get("kubernetes_clusters", []), key=lambda cluster: cluster.get("id", ""))
        deployments = sorted(topology.get("deployments", []), key=lambda deployment: deployment.get("id", ""))

        by_subnet_hardware: dict[str, list[dict[str, Any]]] = {}
        by_subnet_vms: dict[str, list[dict[str, Any]]] = {}
        by_subnet_clusters: dict[str, list[dict[str, Any]]] = {}

        for node in hardware:
            by_subnet_hardware.setdefault(node.get("subnet_id", ""), []).append(node)
        for vm in vms:
            by_subnet_vms.setdefault(vm.get("subnet_id", ""), []).append(vm)
        for cluster in clusters:
            by_subnet_clusters.setdefault(cluster.get("subnet_id", ""), []).append(cluster)

        clusters_by_id = {cluster.get("id"): cluster for cluster in clusters}

        for subnet in subnets:
            subnet_id = subnet.get("id", "")
            subnet_alias = _deterministic_node_id("subnet", subnet_id)
            subnet_label = f"{subnet.get('name', subnet_id)}\\n{subnet.get('cidr', '')}"
            lines.append(f'package "{_escape_label(subnet_label)}" as {subnet_alias} {{')

            for node in by_subnet_hardware.get(subnet_id, []):
                node_id = node.get("id", "")
                alias = _deterministic_node_id("hw", node_id)
                node_alias[("hardware", node_id)] = alias
                label = f"{node.get('hostname', node_id)}\\n{node.get('ip_address', '')}"
                lines.append(f'  node "{_escape_label(label)}" as {alias}')

            for vm in by_subnet_vms.get(subnet_id, []):
                vm_id = vm.get("id", "")
                alias = _deterministic_node_id("vm", vm_id)
                node_alias[("vm", vm_id)] = alias
                label = f"{vm.get('hostname', vm_id)}\\n{vm.get('ip_address', '')}"
                lines.append(f'  node "{_escape_label(label)}" as {alias}')

            for cluster in by_subnet_clusters.get(subnet_id, []):
                cluster_id = cluster.get("id", "")
                cluster_alias = _deterministic_node_id("k8s", cluster_id)
                node_alias[("cluster", cluster_id)] = cluster_alias
                lines.append(f'  node "{_escape_label(cluster.get("name", cluster_id))}" as {cluster_alias} {{')

                namespaces = sorted(
                    {
                        deployment.get("namespace")
                        for deployment in deployments
                        if deployment.get("target_kind") == "K8S_NAMESPACE"
                        and deployment.get("target_cluster_id") == cluster_id
                        and deployment.get("namespace")
                    }
                )
                for namespace in namespaces:
                    namespace_alias = _deterministic_node_id("ns", f"{cluster_id}:{namespace}")
                    node_alias[("namespace", f"{cluster_id}:{namespace}")] = namespace_alias
                    lines.append(f'    node "{_escape_label(namespace)}" as {namespace_alias}')

                lines.append("  }")

            lines.append("}")

        for deployment in deployments:
            deployment_id = deployment.get("id", "")
            artifact_name = deployment.get("component_name") or deployment.get("component_id") or deployment_id
            artifact_key = deployment.get("component_id") or deployment_id
            alias = artifact_alias.get(artifact_key)
            if alias is None:
                alias = _deterministic_node_id("artifact", artifact_key)
                artifact_alias[artifact_key] = alias
                lines.append(f'artifact "{_escape_label(artifact_name)}" as {alias}')

            target_kind = deployment.get("target_kind")
            target_alias: str | None = None
            if target_kind == "HOST":
                target_alias = node_alias.get(("hardware", deployment.get("target_node_id", "")))
            elif target_kind == "VM":
                target_alias = node_alias.get(("vm", deployment.get("target_node_id", "")))
            elif target_kind == "CLUSTER":
                target_alias = node_alias.get(("cluster", deployment.get("target_cluster_id", "")))
            elif target_kind == "K8S_NAMESPACE":
                namespace_key = f"{deployment.get('target_cluster_id', '')}:{deployment.get('namespace', '')}"
                target_alias = node_alias.get(("namespace", namespace_key))
                if target_alias is None:
                    cluster_id = deployment.get("target_cluster_id", "")
                    cluster = clusters_by_id.get(cluster_id, {})
                    cluster_alias = node_alias.get(("cluster", cluster_id))
                    if cluster_alias is None:
                        cluster_alias = _deterministic_node_id("k8s", cluster_id)
                        node_alias[("cluster", cluster_id)] = cluster_alias
                        lines.append(f'node "{_escape_label(cluster.get("name", cluster_id))}" as {cluster_alias}')
                    target_alias = _deterministic_node_id("ns", namespace_key)
                    node_alias[("namespace", namespace_key)] = target_alias
                    lines.append(f'node "{_escape_label(deployment.get("namespace", "default"))}" as {target_alias}')
                    lines.append(f"{cluster_alias} --> {target_alias} : contains")

            if target_alias:
                lines.append(f"{alias} --> {target_alias} : deployed on")

        for vm in vms:
            vm_alias = node_alias.get(("vm", vm.get("id", "")))
            host_alias = node_alias.get(("hardware", vm.get("host_node_id", "")))
            if vm_alias and host_alias:
                lines.append(f"{vm_alias} --> {host_alias} : hosted on")

        for cluster_id, nodes in sorted((topology.get("clusters") or {}).items()):
            cluster_alias = node_alias.get(("cluster", cluster_id))
            if not cluster_alias:
                continue
            for node in sorted(nodes, key=lambda item: item.get("node_id", "")):
                host_alias = node_alias.get(("hardware", node.get("node_id", "")))
                if host_alias:
                    lines.append(f"{cluster_alias} --> {host_alias} : schedules on")

        for link in sorted(topology.get("network_links", []), key=lambda item: item.get("id", "")):
            source_alias = self._resolve_alias(node_alias, link, "source")
            target_alias = self._resolve_alias(node_alias, link, "target")
            if source_alias and target_alias:
                label = _escape_label(link.get("label", "network"))
                lines.append(f"{source_alias} --> {target_alias} : {label}")

        for dependency in sorted(topology.get("dependencies", []), key=lambda item: item.get("id", "")):
            source_alias = artifact_alias.get(dependency.get("from_component_id", ""))
            target_alias = artifact_alias.get(dependency.get("to_component_id", ""))
            if source_alias and target_alias:
                label = _escape_label(dependency.get("label", "depends on"))
                lines.append(f"{source_alias} --> {target_alias} : {label}")

        lines.append("@enduml")
        return "\n".join(lines) + "\n"

    def render_image(self, puml_text: str, output_path: str | Path, image_format: str = "png") -> Path | None:
        """Render a PlantUML diagram image if the runtime is available locally."""
        if shutil.which("plantuml") is None:
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = ["plantuml", f"-t{image_format}", "-pipe"]
        result = subprocess.run(command, input=puml_text.encode("utf-8"), capture_output=True, check=False)
        if result.returncode != 0:
            return None

        output_path.write_bytes(result.stdout)
        return output_path

    @staticmethod
    def _resolve_alias(node_alias: dict[tuple[str, str], str], item: dict[str, Any], prefix: str) -> str | None:
        item_type = (item.get(f"{prefix}_type") or "").lower()
        item_id = item.get(f"{prefix}_id", "")

        key_map = {
            "hardware": "hardware",
            "host": "hardware",
            "vm": "vm",
            "cluster": "cluster",
            "namespace": "namespace",
        }
        normalized = key_map.get(item_type)
        if normalized is None:
            return None
        return node_alias.get((normalized, item_id))


def render_system_topology(system_id: str, topology: dict[str, Any], output_image: str | Path | None = None) -> dict[str, Any]:
    """Render PlantUML text and, when possible, a diagram image for a system topology."""
    renderer = PlantUMLRenderer()
    puml = renderer.render_puml(system_id=system_id, topology=topology)

    image_path: Path | None = None
    if output_image is not None:
        image_path = renderer.render_image(puml_text=puml, output_path=output_image)

    return {
        "puml": puml,
        "image_path": str(image_path) if image_path else None,
    }


__all__ = [
    "PlantUMLRenderer",
    "render_system_topology",
]

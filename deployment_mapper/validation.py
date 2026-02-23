from __future__ import annotations

from ipaddress import ip_address, ip_network
from typing import Any

from deployment_mapper.domain.models import DeploymentSchema, DeploymentTargetKind, ValidationError

_SUPPORTED_TARGET_KINDS = {kind.value for kind in DeploymentTargetKind}


def validate_schema_for_import(schema: DeploymentSchema) -> None:
    """Run fail-fast validation for imported schema data."""
    subnet_networks = {subnet.id: ip_network(subnet.cidr, strict=False) for subnet in schema.subnets}

    for node in schema.hardware_nodes:
        _require_ref(node.subnet_id, subnet_networks, "hardware_node", node.id, "subnet_id", "Create the subnet first or update subnet_id.")
        _ensure_ip_in_subnet(node.ip_address, node.subnet_id, subnet_networks, "hardware_node", node.id)

    hardware_ids = {node.id for node in schema.hardware_nodes}
    for vm in schema.virtual_machines:
        _require_ref(vm.subnet_id, subnet_networks, "virtual_machine", vm.id, "subnet_id", "Create the subnet first or update subnet_id.")
        _require_ref(vm.host_node_id, hardware_ids, "virtual_machine", vm.id, "host_node_id", "Use an existing hardware node id in host_node_id.")
        _ensure_ip_in_subnet(vm.ip_address, vm.subnet_id, subnet_networks, "virtual_machine", vm.id)

    for storage in schema.storage_servers:
        _require_ref(storage.subnet_id, subnet_networks, "storage_server", storage.id, "subnet_id", "Create the subnet first or update subnet_id.")
        _ensure_ip_in_subnet(storage.ip_address, storage.subnet_id, subnet_networks, "storage_server", storage.id)

    for switch in schema.network_switches:
        _require_ref(switch.subnet_id, subnet_networks, "network_switch", switch.id, "subnet_id", "Create the subnet first or update subnet_id.")
        _ensure_ip_in_subnet(switch.management_ip, switch.subnet_id, subnet_networks, "network_switch", switch.id)

    _ensure_no_duplicate_addresses(schema)

    cluster_ids = {cluster.id for cluster in schema.kubernetes_clusters}
    for cluster in schema.kubernetes_clusters:
        _require_ref(cluster.subnet_id, subnet_networks, "kubernetes_cluster", cluster.id, "subnet_id", "Create the subnet first or update subnet_id.")
        for node_id in cluster.node_ids:
            _require_ref(node_id, hardware_ids, "kubernetes_cluster", cluster.id, "node_ids", "Remove unknown node_ids or import referenced hardware nodes.")

    system_ids = {system.id for system in schema.software_systems}
    vm_ids = {vm.id for vm in schema.virtual_machines}
    for deployment in schema.deployment_instances:
        _require_ref(deployment.system_id, system_ids, "deployment_instance", deployment.id, "system_id", "Import software system before creating deployment instance.")
        _validate_deployment_target(deployment.id, deployment.target_kind, deployment.target_node_id, deployment.target_cluster_id, deployment.namespace, hardware_ids, vm_ids, cluster_ids)


def validate_topology_for_diagram(system_id: str, topology: dict[str, Any]) -> None:
    subnets = topology.get("subnets", [])
    subnet_networks = {subnet["id"]: ip_network(subnet["cidr"], strict=False) for subnet in subnets}

    hardware_by_id = {node["id"]: node for node in topology.get("hardware_nodes", [])}
    vm_by_id = {vm["id"]: vm for vm in topology.get("virtual_machines", [])}
    cluster_by_id = {cluster["id"]: cluster for cluster in topology.get("kubernetes_clusters", [])}

    for node in hardware_by_id.values():
        _require_ref(node.get("subnet_id"), subnet_networks, "hardware_node", node.get("id", "<missing>"), "subnet_id", "Fix hardware node subnet_id or add the missing subnet.")
        _ensure_ip_in_subnet(node.get("ip_address", ""), node.get("subnet_id", ""), subnet_networks, "hardware_node", node.get("id", "<missing>"))

    for vm in vm_by_id.values():
        _require_ref(vm.get("subnet_id"), subnet_networks, "virtual_machine", vm.get("id", "<missing>"), "subnet_id", "Fix VM subnet_id or add the missing subnet.")
        _ensure_ip_in_subnet(vm.get("ip_address", ""), vm.get("subnet_id", ""), subnet_networks, "virtual_machine", vm.get("id", "<missing>"))

    _ensure_no_duplicate_topology_addresses(topology)

    for deployment in topology.get("deployments", []):
        deployment_id = deployment.get("id", "<missing>")
        target_kind = deployment.get("target_kind")
        if target_kind not in _SUPPORTED_TARGET_KINDS:
            raise ValidationError(
                f"diagram generation blocked for system '{system_id}': deployment_instance '{deployment_id}' uses unsupported target_kind '{target_kind}'. "
                f"Supported target kinds: {', '.join(sorted(_SUPPORTED_TARGET_KINDS))}. Suggested fix: map deployment to one of the supported target kinds."
            )

        enum_kind = DeploymentTargetKind(target_kind)
        _validate_deployment_target(
            deployment_id,
            enum_kind,
            deployment.get("target_node_id"),
            deployment.get("target_cluster_id"),
            deployment.get("namespace"),
            set(hardware_by_id),
            set(vm_by_id),
            set(cluster_by_id),
        )


def _ensure_no_duplicate_addresses(schema: DeploymentSchema) -> None:
    seen: dict[tuple[str, str], str] = {}
    records: list[tuple[str, str, str]] = []
    records.extend((node.id, node.subnet_id, node.ip_address) for node in schema.hardware_nodes)
    records.extend((vm.id, vm.subnet_id, vm.ip_address) for vm in schema.virtual_machines)
    records.extend((storage.id, storage.subnet_id, storage.ip_address) for storage in schema.storage_servers)
    records.extend((switch.id, switch.subnet_id, switch.management_ip) for switch in schema.network_switches)

    for record_id, subnet_id, address in records:
        key = (subnet_id, address)
        if key in seen:
            raise ValidationError(
                f"duplicate addressing conflict: address '{address}' is assigned to '{seen[key]}' and '{record_id}' in subnet '{subnet_id}'. Suggested fix: assign a unique IP per subnet."
            )
        seen[key] = record_id


def _ensure_no_duplicate_topology_addresses(topology: dict[str, Any]) -> None:
    seen: dict[tuple[str, str], str] = {}
    for key, subnet_field, ip_field in (
        ("hardware_nodes", "subnet_id", "ip_address"),
        ("virtual_machines", "subnet_id", "ip_address"),
    ):
        for item in topology.get(key, []):
            subnet_id = item.get(subnet_field)
            ip = item.get(ip_field)
            item_id = item.get("id", "<missing>")
            if not subnet_id or not ip:
                continue
            conflict_key = (subnet_id, ip)
            if conflict_key in seen:
                raise ValidationError(
                    f"duplicate addressing conflict: address '{ip}' is assigned to '{seen[conflict_key]}' and '{item_id}' in subnet '{subnet_id}'. Suggested fix: assign unique target addresses before diagram generation."
                )
            seen[conflict_key] = item_id


def _validate_deployment_target(
    deployment_id: str,
    target_kind: DeploymentTargetKind,
    target_node_id: str | None,
    target_cluster_id: str | None,
    namespace: str | None,
    hardware_ids: set[str],
    vm_ids: set[str],
    cluster_ids: set[str],
) -> None:
    if target_kind is DeploymentTargetKind.HOST:
        _require_ref(target_node_id, hardware_ids, "deployment_instance", deployment_id, "target_node_id", "Set target_node_id to an existing hardware node id.")
    elif target_kind is DeploymentTargetKind.VM:
        _require_ref(target_node_id, vm_ids, "deployment_instance", deployment_id, "target_node_id", "Set target_node_id to an existing VM id.")
    elif target_kind is DeploymentTargetKind.CLUSTER:
        _require_ref(target_cluster_id, cluster_ids, "deployment_instance", deployment_id, "target_cluster_id", "Set target_cluster_id to an existing kubernetes cluster id.")
    elif target_kind is DeploymentTargetKind.K8S_NAMESPACE:
        _require_ref(target_cluster_id, cluster_ids, "deployment_instance", deployment_id, "target_cluster_id", "Set target_cluster_id to an existing kubernetes cluster id.")
        if not namespace:
            raise ValidationError(
                f"deployment_instance '{deployment_id}' is missing namespace for K8S_NAMESPACE target. Suggested fix: set a non-empty namespace value."
            )


def _require_ref(value: str | None, allowed: set[str] | dict[str, Any], entity: str, entity_id: str, field: str, suggestion: str) -> None:
    if not value or value not in allowed:
        raise ValidationError(
            f"missing foreign key reference: {entity} '{entity_id}' field '{field}' points to '{value}'. Suggested fix: {suggestion}"
        )


def _ensure_ip_in_subnet(ip_value: str, subnet_id: str, subnet_networks: dict[str, Any], entity: str, entity_id: str) -> None:
    network = subnet_networks[subnet_id]
    address = ip_address(ip_value)
    if address not in network:
        raise ValidationError(
            f"invalid subnet/CIDR assignment: {entity} '{entity_id}' uses address '{ip_value}' outside subnet '{subnet_id}' ({network}). Suggested fix: use an address inside the subnet CIDR or move the entity to the correct subnet."
        )

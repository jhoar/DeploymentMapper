from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address, ip_network
from typing import Iterable


class ValidationError(ValueError):
    """Raised when schema-level or model-level validation fails."""


class NodeKind(str, Enum):
    PHYSICAL = "PHYSICAL"
    VM = "VM"
    K8S_NODE = "K8S_NODE"
    STORAGE = "STORAGE"
    SWITCH = "SWITCH"


class DeploymentTargetKind(str, Enum):
    HOST = "HOST"
    VM = "VM"
    K8S_NAMESPACE = "K8S_NAMESPACE"
    CLUSTER = "CLUSTER"


@dataclass(slots=True)
class Subnet:
    id: str
    cidr: str
    name: str

    def __post_init__(self) -> None:
        _require_fields(self, "id", "cidr", "name")
        _validate_cidr(self.cidr)


@dataclass(slots=True)
class HardwareNode:
    id: str
    hostname: str
    ip_address: str
    subnet_id: str
    kind: NodeKind = NodeKind.PHYSICAL

    def __post_init__(self) -> None:
        _require_fields(self, "id", "hostname", "ip_address", "subnet_id")
        _validate_ip(self.ip_address)


@dataclass(slots=True)
class KubernetesCluster:
    id: str
    name: str
    subnet_id: str
    node_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_fields(self, "id", "name", "subnet_id")


@dataclass(slots=True)
class VirtualMachine:
    id: str
    hostname: str
    ip_address: str
    subnet_id: str
    host_node_id: str

    def __post_init__(self) -> None:
        _require_fields(self, "id", "hostname", "ip_address", "subnet_id", "host_node_id")
        _validate_ip(self.ip_address)


@dataclass(slots=True)
class StorageServer:
    id: str
    hostname: str
    ip_address: str
    subnet_id: str

    def __post_init__(self) -> None:
        _require_fields(self, "id", "hostname", "ip_address", "subnet_id")
        _validate_ip(self.ip_address)


@dataclass(slots=True)
class NetworkSwitch:
    id: str
    hostname: str
    management_ip: str
    subnet_id: str

    def __post_init__(self) -> None:
        _require_fields(self, "id", "hostname", "management_ip", "subnet_id")
        _validate_ip(self.management_ip)


@dataclass(slots=True)
class SoftwareSystem:
    id: str
    name: str
    version: str | None = None

    def __post_init__(self) -> None:
        _require_fields(self, "id", "name")


@dataclass(slots=True)
class DeploymentInstance:
    id: str
    system_id: str
    target_kind: DeploymentTargetKind
    target_node_id: str | None = None
    target_cluster_id: str | None = None
    component_id: str | None = None
    namespace: str | None = None

    def __post_init__(self) -> None:
        _require_fields(self, "id", "system_id")


@dataclass(slots=True)
class DeploymentSchema:
    subnets: list[Subnet] = field(default_factory=list)
    hardware_nodes: list[HardwareNode] = field(default_factory=list)
    kubernetes_clusters: list[KubernetesCluster] = field(default_factory=list)
    virtual_machines: list[VirtualMachine] = field(default_factory=list)
    storage_servers: list[StorageServer] = field(default_factory=list)
    network_switches: list[NetworkSwitch] = field(default_factory=list)
    software_systems: list[SoftwareSystem] = field(default_factory=list)
    deployment_instances: list[DeploymentInstance] = field(default_factory=list)

    def validate(self) -> None:
        subnet_ids = _unique_ids(self.subnets, "subnet")
        _ensure_unique(self.subnets, key=lambda s: s.cidr, label="subnet.cidr")

        hardware_ids = _unique_ids(self.hardware_nodes, "hardware node")
        vm_ids = _unique_ids(self.virtual_machines, "virtual machine")
        storage_ids = _unique_ids(self.storage_servers, "storage server")
        switch_ids = _unique_ids(self.network_switches, "network switch")
        _unique_ids(self.kubernetes_clusters, "kubernetes cluster")
        _unique_ids(self.software_systems, "software system")
        _unique_ids(self.deployment_instances, "deployment instance")

        for node in self.hardware_nodes:
            _assert_exists(node.subnet_id, subnet_ids, f"hardware node '{node.id}' subnet_id")

        for vm in self.virtual_machines:
            _assert_exists(vm.subnet_id, subnet_ids, f"virtual machine '{vm.id}' subnet_id")
            _assert_exists(vm.host_node_id, hardware_ids, f"virtual machine '{vm.id}' host_node_id")

        for storage in self.storage_servers:
            _assert_exists(storage.subnet_id, subnet_ids, f"storage server '{storage.id}' subnet_id")

        for switch in self.network_switches:
            _assert_exists(switch.subnet_id, subnet_ids, f"network switch '{switch.id}' subnet_id")

        cluster_ids = {cluster.id for cluster in self.kubernetes_clusters}
        for cluster in self.kubernetes_clusters:
            _assert_exists(cluster.subnet_id, subnet_ids, f"kubernetes cluster '{cluster.id}' subnet_id")
            for node_id in cluster.node_ids:
                _assert_exists(node_id, hardware_ids, f"kubernetes cluster '{cluster.id}' node_id")

        system_ids = {system.id for system in self.software_systems}
        for instance in self.deployment_instances:
            _assert_exists(instance.system_id, system_ids, f"deployment instance '{instance.id}' system_id")
            self._validate_instance_target(instance, hardware_ids, vm_ids, cluster_ids)

        self._validate_hostname_ip_uniqueness()

    def _validate_instance_target(
        self,
        instance: DeploymentInstance,
        hardware_ids: set[str],
        vm_ids: set[str],
        cluster_ids: set[str],
    ) -> None:
        if instance.target_kind is DeploymentTargetKind.HOST:
            _assert_exists(instance.target_node_id, hardware_ids, f"deployment instance '{instance.id}' target_node_id")
            if instance.target_cluster_id is not None:
                raise ValidationError(
                    f"deployment instance '{instance.id}' must not set target_cluster_id for HOST target"
                )
        elif instance.target_kind is DeploymentTargetKind.VM:
            _assert_exists(instance.target_node_id, vm_ids, f"deployment instance '{instance.id}' target_node_id")
            if instance.target_cluster_id is not None:
                raise ValidationError(
                    f"deployment instance '{instance.id}' must not set target_cluster_id for VM target"
                )
        elif instance.target_kind is DeploymentTargetKind.CLUSTER:
            _assert_exists(
                instance.target_cluster_id,
                cluster_ids,
                f"deployment instance '{instance.id}' target_cluster_id",
            )
            if instance.target_node_id is not None:
                raise ValidationError(
                    f"deployment instance '{instance.id}' must not set target_node_id for CLUSTER target"
                )
        elif instance.target_kind is DeploymentTargetKind.K8S_NAMESPACE:
            _assert_exists(
                instance.target_cluster_id,
                cluster_ids,
                f"deployment instance '{instance.id}' target_cluster_id",
            )
            if not instance.namespace:
                raise ValidationError(
                    f"deployment instance '{instance.id}' must include namespace for K8S_NAMESPACE target"
                )
            if instance.target_node_id is not None:
                raise ValidationError(
                    f"deployment instance '{instance.id}' must not set target_node_id for K8S_NAMESPACE target"
                )

    def _validate_hostname_ip_uniqueness(self) -> None:
        scoped_hosts: dict[tuple[str, str], str] = {}
        scoped_ips: dict[tuple[str, str], str] = {}

        records = [
            (node.id, node.subnet_id, node.hostname, node.ip_address) for node in self.hardware_nodes
        ]
        records.extend((vm.id, vm.subnet_id, vm.hostname, vm.ip_address) for vm in self.virtual_machines)
        records.extend(
            (storage.id, storage.subnet_id, storage.hostname, storage.ip_address)
            for storage in self.storage_servers
        )
        records.extend(
            (switch.id, switch.subnet_id, switch.hostname, switch.management_ip)
            for switch in self.network_switches
        )

        for record_id, subnet_id, hostname, ip in records:
            host_key = (subnet_id, hostname.lower())
            if host_key in scoped_hosts:
                raise ValidationError(
                    f"duplicate hostname '{hostname}' in subnet '{subnet_id}' ({scoped_hosts[host_key]}, {record_id})"
                )
            scoped_hosts[host_key] = record_id

            ip_key = (subnet_id, ip)
            if ip_key in scoped_ips:
                raise ValidationError(
                    f"duplicate IP '{ip}' in subnet '{subnet_id}' ({scoped_ips[ip_key]}, {record_id})"
                )
            scoped_ips[ip_key] = record_id


def _require_fields(model: object, *names: str) -> None:
    for name in names:
        value = getattr(model, name)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{model.__class__.__name__}.{name} is required")


def _unique_ids(items: Iterable[object], label: str) -> set[str]:
    ids: set[str] = set()
    for item in items:
        item_id = getattr(item, "id")
        if item_id in ids:
            raise ValidationError(f"duplicate {label} id '{item_id}'")
        ids.add(item_id)
    return ids


def _ensure_unique(items: Iterable[object], key, label: str) -> None:
    seen: dict[str, object] = {}
    for item in items:
        value = key(item)
        if value in seen:
            raise ValidationError(f"duplicate {label} '{value}'")
        seen[value] = item


def _assert_exists(value: str | None, allowed: set[str], field_name: str) -> None:
    if not value:
        raise ValidationError(f"{field_name} is required")
    if value not in allowed:
        raise ValidationError(f"{field_name} '{value}' does not reference an existing object")


def _validate_cidr(value: str) -> None:
    try:
        ip_network(value, strict=False)
    except ValueError as exc:
        raise ValidationError(f"invalid CIDR '{value}'") from exc


def _validate_ip(value: str) -> None:
    try:
        ip_address(value)
    except ValueError as exc:
        raise ValidationError(f"invalid IP address '{value}'") from exc

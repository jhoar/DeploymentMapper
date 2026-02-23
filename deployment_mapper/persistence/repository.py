from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deployment_mapper.domain.models import DeploymentSchema


@dataclass(slots=True, frozen=True)
class NodeRecord:
    node_id: str
    node_type: str
    hostname: str
    ip_address: str


class DeploymentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def list_nodes_hosting_system(self, system_id: str) -> list[NodeRecord]:
        """Return distinct physical or virtual nodes hosting a software system."""
        query = """
            WITH direct_nodes AS (
                SELECT d.target_node_id AS node_id, 'hardware' AS node_type
                FROM deployment_instances d
                WHERE d.system_id = ? AND d.target_kind = 'HOST'
                UNION
                SELECT d.target_node_id AS node_id, 'vm' AS node_type
                FROM deployment_instances d
                WHERE d.system_id = ? AND d.target_kind = 'VM'
            ),
            cluster_host_nodes AS (
                SELECT cn.node_id AS node_id, 'hardware' AS node_type
                FROM deployment_instances d
                JOIN cluster_nodes cn ON cn.cluster_id = d.target_cluster_id
                WHERE d.system_id = ? AND d.target_kind IN ('CLUSTER', 'K8S_NAMESPACE')
            ),
            all_nodes AS (
                SELECT * FROM direct_nodes
                UNION
                SELECT * FROM cluster_host_nodes
            )
            SELECT n.node_id,
                   n.node_type,
                   CASE
                     WHEN n.node_type = 'hardware' THEN h.hostname
                     WHEN n.node_type = 'vm' THEN v.hostname
                   END AS hostname,
                   CASE
                     WHEN n.node_type = 'hardware' THEN h.ip_address
                     WHEN n.node_type = 'vm' THEN v.ip_address
                   END AS ip_address
            FROM all_nodes n
            LEFT JOIN hardware_nodes h ON n.node_type = 'hardware' AND h.id = n.node_id
            LEFT JOIN virtual_machines v ON n.node_type = 'vm' AND v.id = n.node_id
            ORDER BY n.node_type, hostname
        """
        rows = self.connection.execute(query, (system_id, system_id, system_id)).fetchall()
        return [
            NodeRecord(
                node_id=row["node_id"],
                node_type=row["node_type"],
                hostname=row["hostname"],
                ip_address=row["ip_address"],
            )
            for row in rows
        ]

    def list_systems_per_subnet(self) -> dict[str, list[dict[str, str]]]:
        """Return systems grouped by subnet, including systems deployed to nodes within each subnet."""
        query = """
            WITH deployment_subnets AS (
                SELECT d.system_id, h.subnet_id
                FROM deployment_instances d
                JOIN hardware_nodes h ON d.target_kind = 'HOST' AND d.target_node_id = h.id
                UNION
                SELECT d.system_id, v.subnet_id
                FROM deployment_instances d
                JOIN virtual_machines v ON d.target_kind = 'VM' AND d.target_node_id = v.id
                UNION
                SELECT d.system_id, c.subnet_id
                FROM deployment_instances d
                JOIN kubernetes_clusters c
                  ON d.target_kind IN ('CLUSTER', 'K8S_NAMESPACE')
                 AND d.target_cluster_id = c.id
            )
            SELECT s.id AS subnet_id,
                   s.name AS subnet_name,
                   sys.id AS system_id,
                   sys.name AS system_name
            FROM deployment_subnets ds
            JOIN subnets s ON s.id = ds.subnet_id
            JOIN software_systems sys ON sys.id = ds.system_id
            GROUP BY s.id, s.name, sys.id, sys.name
            ORDER BY s.name, sys.name
        """
        rows = self.connection.execute(query).fetchall()
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            subnet_key = f"{row['subnet_id']}:{row['subnet_name']}"
            grouped.setdefault(subnet_key, []).append(
                {"system_id": row["system_id"], "system_name": row["system_name"]}
            )
        return grouped

    def fetch_full_deployment_graph(self, system_id: str) -> dict[str, Any]:
        """Return system, components, deployments, and linked infrastructure nodes."""
        system = self.connection.execute(
            "SELECT id, name, version FROM software_systems WHERE id = ?", (system_id,)
        ).fetchone()
        if system is None:
            return {}

        components = self.connection.execute(
            """
            SELECT c.id, c.name, c.component_type
            FROM components c
            JOIN system_components sc ON sc.component_id = c.id
            WHERE sc.system_id = ?
            ORDER BY c.name
            """,
            (system_id,),
        ).fetchall()

        deployments = self.connection.execute(
            """
            SELECT d.id,
                   d.target_kind,
                   d.target_node_id,
                   d.target_cluster_id,
                   d.namespace,
                   c.id AS component_id,
                   c.name AS component_name
            FROM deployment_instances d
            LEFT JOIN components c ON c.id = d.component_id
            WHERE d.system_id = ?
            ORDER BY d.id
            """,
            (system_id,),
        ).fetchall()

        subnets = self.connection.execute(
            """
            SELECT DISTINCT s.id, s.name, s.cidr
            FROM deployment_instances d
            LEFT JOIN hardware_nodes h
              ON d.target_kind = 'HOST'
             AND d.target_node_id = h.id
            LEFT JOIN virtual_machines v
              ON d.target_kind = 'VM'
             AND d.target_node_id = v.id
            LEFT JOIN kubernetes_clusters c
              ON d.target_kind IN ('CLUSTER', 'K8S_NAMESPACE')
             AND d.target_cluster_id = c.id
            JOIN subnets s ON s.id = COALESCE(h.subnet_id, v.subnet_id, c.subnet_id)
            WHERE d.system_id = ?
            ORDER BY s.id
            """,
            (system_id,),
        ).fetchall()

        subnet_ids = [row["id"] for row in subnets]
        if subnet_ids:
            placeholders = ",".join("?" for _ in subnet_ids)
            hardware_nodes = self.connection.execute(
                f"""
                SELECT id, hostname, ip_address, subnet_id, kind
                FROM hardware_nodes
                WHERE subnet_id IN ({placeholders})
                ORDER BY subnet_id, hostname
                """,
                tuple(subnet_ids),
            ).fetchall()
            virtual_machines = self.connection.execute(
                f"""
                SELECT id, hostname, ip_address, subnet_id, host_node_id
                FROM virtual_machines
                WHERE subnet_id IN ({placeholders})
                ORDER BY subnet_id, hostname
                """,
                tuple(subnet_ids),
            ).fetchall()
            kubernetes_clusters = self.connection.execute(
                f"""
                SELECT id, name, subnet_id
                FROM kubernetes_clusters
                WHERE subnet_id IN ({placeholders})
                ORDER BY subnet_id, name
                """,
                tuple(subnet_ids),
            ).fetchall()
        else:
            hardware_nodes = []
            virtual_machines = []
            kubernetes_clusters = []

        cluster_ids = [row["target_cluster_id"] for row in deployments if row["target_cluster_id"]]
        cluster_nodes: dict[str, list[dict[str, str]]] = {}
        if cluster_ids:
            placeholders = ",".join("?" for _ in cluster_ids)
            rows = self.connection.execute(
                f"""
                SELECT cn.cluster_id, h.id AS node_id, h.hostname, h.ip_address
                FROM cluster_nodes cn
                JOIN hardware_nodes h ON h.id = cn.node_id
                WHERE cn.cluster_id IN ({placeholders})
                ORDER BY cn.cluster_id, h.hostname
                """,
                tuple(cluster_ids),
            ).fetchall()
            for row in rows:
                cluster_nodes.setdefault(row["cluster_id"], []).append(
                    {
                        "node_id": row["node_id"],
                        "hostname": row["hostname"],
                        "ip_address": row["ip_address"],
                    }
                )

        return {
            "system": dict(system),
            "components": [dict(row) for row in components],
            "deployments": [dict(row) for row in deployments],
            "subnets": [dict(row) for row in subnets],
            "hardware_nodes": [dict(row) for row in hardware_nodes],
            "virtual_machines": [dict(row) for row in virtual_machines],
            "kubernetes_clusters": [dict(row) for row in kubernetes_clusters],
            "clusters": cluster_nodes,
            "hosting_nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "hostname": node.hostname,
                    "ip_address": node.ip_address,
                }
                for node in self.list_nodes_hosting_system(system_id)
            ],
        }

    def get_system_topology(self, system_id: str) -> dict[str, Any]:
        """Return transitive topology links for one system (system->component->deployment->target->subnet)."""
        graph = self.fetch_full_deployment_graph(system_id)
        if not graph:
            return {}

        relations = self.connection.execute(
            """
            SELECT d.id AS deployment_id,
                   c.id AS component_id,
                   c.name AS component_name,
                   d.target_kind,
                   d.namespace,
                   COALESCE(h.id, vm.id, kc.id) AS target_id,
                   CASE
                     WHEN d.target_kind = 'HOST' THEN 'hardware'
                     WHEN d.target_kind = 'VM' THEN 'vm'
                     ELSE 'cluster'
                   END AS target_type,
                   COALESCE(h.hostname, vm.hostname, kc.name) AS target_name,
                   COALESCE(h.ip_address, vm.ip_address, '') AS target_ip,
                   s.id AS subnet_id,
                   s.name AS subnet_name,
                   s.cidr AS subnet_cidr
            FROM deployment_instances d
            LEFT JOIN components c ON c.id = d.component_id
            LEFT JOIN hardware_nodes h
              ON d.target_kind = 'HOST'
             AND d.target_node_id = h.id
            LEFT JOIN virtual_machines vm
              ON d.target_kind = 'VM'
             AND d.target_node_id = vm.id
            LEFT JOIN kubernetes_clusters kc
              ON d.target_kind IN ('CLUSTER', 'K8S_NAMESPACE')
             AND d.target_cluster_id = kc.id
            JOIN subnets s ON s.id = COALESCE(h.subnet_id, vm.subnet_id, kc.subnet_id)
            WHERE d.system_id = ?
            ORDER BY c.name, d.id
            """,
            (system_id,),
        ).fetchall()

        graph["relations"] = [dict(row) for row in relations]
        return graph

    def get_subnet_deployments(self, subnet_id: str) -> dict[str, Any]:
        """Return deployments in a subnet via their resolved targets, including transitive path details."""
        subnet = self.connection.execute(
            "SELECT id, name, cidr FROM subnets WHERE id = ?",
            (subnet_id,),
        ).fetchone()
        if subnet is None:
            return {}

        rows = self.connection.execute(
            """
            SELECT sys.id AS system_id,
                   sys.name AS system_name,
                   sys.version AS system_version,
                   c.id AS component_id,
                   c.name AS component_name,
                   d.id AS deployment_id,
                   d.target_kind,
                   d.namespace,
                   COALESCE(h.id, vm.id, kc.id) AS target_id,
                   CASE
                     WHEN d.target_kind = 'HOST' THEN 'hardware'
                     WHEN d.target_kind = 'VM' THEN 'vm'
                     ELSE 'cluster'
                   END AS target_type,
                   COALESCE(h.hostname, vm.hostname, kc.name) AS target_name,
                   COALESCE(h.ip_address, vm.ip_address, '') AS target_ip
            FROM deployment_instances d
            JOIN software_systems sys ON sys.id = d.system_id
            LEFT JOIN components c ON c.id = d.component_id
            LEFT JOIN hardware_nodes h
              ON d.target_kind = 'HOST'
             AND d.target_node_id = h.id
            LEFT JOIN virtual_machines vm
              ON d.target_kind = 'VM'
             AND d.target_node_id = vm.id
            LEFT JOIN kubernetes_clusters kc
              ON d.target_kind IN ('CLUSTER', 'K8S_NAMESPACE')
             AND d.target_cluster_id = kc.id
            WHERE COALESCE(h.subnet_id, vm.subnet_id, kc.subnet_id) = ?
            ORDER BY sys.name, c.name, d.id
            """,
            (subnet_id,),
        ).fetchall()

        systems: dict[str, dict[str, Any]] = {}
        for row in rows:
            system_bucket = systems.setdefault(
                row["system_id"],
                {
                    "system_id": row["system_id"],
                    "system_name": row["system_name"],
                    "system_version": row["system_version"],
                    "components": {},
                },
            )
            component_key = row["component_id"] or "<unassigned>"
            component_bucket = system_bucket["components"].setdefault(
                component_key,
                {
                    "component_id": row["component_id"],
                    "component_name": row["component_name"] or "<unassigned>",
                    "deployments": [],
                },
            )
            component_bucket["deployments"].append(
                {
                    "deployment_id": row["deployment_id"],
                    "target_kind": row["target_kind"],
                    "target_id": row["target_id"],
                    "target_type": row["target_type"],
                    "target_name": row["target_name"],
                    "target_ip": row["target_ip"],
                    "namespace": row["namespace"],
                }
            )

        flattened_systems: list[dict[str, Any]] = []
        for system in systems.values():
            system["components"] = list(system["components"].values())
            flattened_systems.append(system)

        return {
            "subnet": dict(subnet),
            "systems": flattened_systems,
            "relations": [dict(row) for row in rows],
        }

    def upsert_schema(self, schema: DeploymentSchema) -> None:
        """Insert or update canonical deployment records idempotently."""
        schema.validate()
        with self.connection:
            for subnet in schema.subnets:
                self.connection.execute(
                    """
                    INSERT INTO subnets (id, cidr, name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      cidr = excluded.cidr,
                      name = excluded.name
                    """,
                    (subnet.id, subnet.cidr, subnet.name),
                )

            for node in schema.hardware_nodes:
                self.connection.execute(
                    """
                    INSERT INTO hardware_nodes (id, hostname, ip_address, subnet_id, kind)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      hostname = excluded.hostname,
                      ip_address = excluded.ip_address,
                      subnet_id = excluded.subnet_id,
                      kind = excluded.kind
                    """,
                    (node.id, node.hostname, node.ip_address, node.subnet_id, node.kind.value),
                )

            for vm in schema.virtual_machines:
                self.connection.execute(
                    """
                    INSERT INTO virtual_machines (id, hostname, ip_address, subnet_id, host_node_id)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      hostname = excluded.hostname,
                      ip_address = excluded.ip_address,
                      subnet_id = excluded.subnet_id,
                      host_node_id = excluded.host_node_id
                    """,
                    (vm.id, vm.hostname, vm.ip_address, vm.subnet_id, vm.host_node_id),
                )

            for storage in schema.storage_servers:
                self.connection.execute(
                    """
                    INSERT INTO storage_servers (id, hostname, ip_address, subnet_id)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      hostname = excluded.hostname,
                      ip_address = excluded.ip_address,
                      subnet_id = excluded.subnet_id
                    """,
                    (storage.id, storage.hostname, storage.ip_address, storage.subnet_id),
                )

            for switch in schema.network_switches:
                self.connection.execute(
                    """
                    INSERT INTO network_switches (id, hostname, management_ip, subnet_id)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      hostname = excluded.hostname,
                      management_ip = excluded.management_ip,
                      subnet_id = excluded.subnet_id
                    """,
                    (switch.id, switch.hostname, switch.management_ip, switch.subnet_id),
                )

            for system in schema.software_systems:
                self.connection.execute(
                    """
                    INSERT INTO software_systems (id, name, version)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      name = excluded.name,
                      version = excluded.version
                    """,
                    (system.id, system.name, system.version),
                )

            for cluster in schema.kubernetes_clusters:
                self.connection.execute(
                    """
                    INSERT INTO kubernetes_clusters (id, name, subnet_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      name = excluded.name,
                      subnet_id = excluded.subnet_id
                    """,
                    (cluster.id, cluster.name, cluster.subnet_id),
                )

                self.connection.execute("DELETE FROM cluster_nodes WHERE cluster_id = ?", (cluster.id,))
                for node_id in cluster.node_ids:
                    self.connection.execute(
                        "INSERT INTO cluster_nodes (cluster_id, node_id) VALUES (?, ?)",
                        (cluster.id, node_id),
                    )

            for deployment in schema.deployment_instances:
                self.connection.execute(
                    """
                    INSERT INTO deployment_instances
                    (id, system_id, target_kind, target_node_id, target_cluster_id, component_id, namespace)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      system_id = excluded.system_id,
                      target_kind = excluded.target_kind,
                      target_node_id = excluded.target_node_id,
                      target_cluster_id = excluded.target_cluster_id,
                      component_id = excluded.component_id,
                      namespace = excluded.namespace
                    """,
                    (
                        deployment.id,
                        deployment.system_id,
                        deployment.target_kind.value,
                        deployment.target_node_id,
                        deployment.target_cluster_id,
                        deployment.component_id,
                        deployment.namespace,
                    ),
                )


def apply_migrations(connection: sqlite3.Connection, migrations_dir: Path) -> None:
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        script = migration_file.read_text(encoding="utf-8")
        connection.executescript(script)
    connection.commit()

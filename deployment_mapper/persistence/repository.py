from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def apply_migrations(connection: sqlite3.Connection, migrations_dir: Path) -> None:
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        script = migration_file.read_text(encoding="utf-8")
        connection.executescript(script)
    connection.commit()

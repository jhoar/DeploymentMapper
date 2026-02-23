"""create deployment mapper schema

Revision ID: 20260223_0001
Revises: None
Create Date: 2026-02-23 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260223_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subnets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("cidr", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cidr", name="uq_subnets_cidr"),
    )

    op.create_table(
        "hardware_nodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subnet_id", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subnet_id", "ip", name="uq_hardware_nodes_subnet_ip"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_hardware_nodes_subnet_hostname_lower ON hardware_nodes (subnet_id, lower(hostname))"
    )

    op.create_table(
        "kubernetes_clusters",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subnet_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "virtual_machines",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subnet_id", sa.String(length=64), nullable=False),
        sa.Column("host_node_id", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["host_node_id"], ["hardware_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subnet_id", "ip", name="uq_virtual_machines_subnet_ip"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_virtual_machines_subnet_hostname_lower ON virtual_machines (subnet_id, lower(hostname))"
    )

    op.create_table(
        "storage_servers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subnet_id", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subnet_id", "ip", name="uq_storage_servers_subnet_ip"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_storage_servers_subnet_hostname_lower ON storage_servers (subnet_id, lower(hostname))"
    )

    op.create_table(
        "network_switches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subnet_id", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["subnet_id"], ["subnets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subnet_id", "ip", name="uq_network_switches_subnet_ip"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_network_switches_subnet_hostname_lower ON network_switches (subnet_id, lower(hostname))"
    )

    op.create_table(
        "software_systems",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "kubernetes_cluster_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_id", sa.String(length=64), nullable=False),
        sa.Column("hardware_node_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["kubernetes_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hardware_node_id"], ["hardware_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id", "hardware_node_id", name="uq_cluster_node"),
    )

    op.create_table(
        "deployment_instances",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("system_id", sa.String(length=64), nullable=False),
        sa.Column("target_kind", sa.String(length=32), nullable=False),
        sa.Column("target_hardware_node_id", sa.String(length=64), nullable=True),
        sa.Column("target_vm_id", sa.String(length=64), nullable=True),
        sa.Column("target_cluster_id", sa.String(length=64), nullable=True),
        sa.Column("namespace", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            """
            (target_kind = 'HOST' AND target_hardware_node_id IS NOT NULL AND target_vm_id IS NULL AND target_cluster_id IS NULL AND namespace IS NULL)
            OR
            (target_kind = 'VM' AND target_vm_id IS NOT NULL AND target_hardware_node_id IS NULL AND target_cluster_id IS NULL AND namespace IS NULL)
            OR
            (target_kind = 'CLUSTER' AND target_cluster_id IS NOT NULL AND target_hardware_node_id IS NULL AND target_vm_id IS NULL AND namespace IS NULL)
            OR
            (target_kind = 'K8S_NAMESPACE' AND target_cluster_id IS NOT NULL AND target_hardware_node_id IS NULL AND target_vm_id IS NULL AND namespace IS NOT NULL)
            """,
            name="ck_deployment_instance_target_kind",
        ),
        sa.ForeignKeyConstraint(["system_id"], ["software_systems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_cluster_id"], ["kubernetes_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_hardware_node_id"], ["hardware_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_vm_id"], ["virtual_machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("deployment_instances")
    op.drop_table("kubernetes_cluster_nodes")
    op.drop_table("software_systems")
    op.execute("DROP INDEX uq_network_switches_subnet_hostname_lower")
    op.drop_table("network_switches")
    op.execute("DROP INDEX uq_storage_servers_subnet_hostname_lower")
    op.drop_table("storage_servers")
    op.execute("DROP INDEX uq_virtual_machines_subnet_hostname_lower")
    op.drop_table("virtual_machines")
    op.drop_table("kubernetes_clusters")
    op.execute("DROP INDEX uq_hardware_nodes_subnet_hostname_lower")
    op.drop_table("hardware_nodes")
    op.drop_table("subnets")

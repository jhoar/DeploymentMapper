from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Subnet(Base):
    __tablename__ = "subnets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cidr: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class HardwareNode(Base):
    __tablename__ = "hardware_nodes"
    __table_args__ = (
        UniqueConstraint("subnet_id", "ip", name="uq_hardware_nodes_subnet_ip"),
        Index("uq_hardware_nodes_subnet_hostname_lower", "subnet_id", func.lower(text("hostname")), unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subnet_id: Mapped[str] = mapped_column(ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, default="PHYSICAL")

    subnet: Mapped[Subnet] = relationship()


class KubernetesCluster(Base):
    __tablename__ = "kubernetes_clusters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subnet_id: Mapped[str] = mapped_column(ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    subnet: Mapped[Subnet] = relationship()


class KubernetesClusterNode(Base):
    __tablename__ = "kubernetes_cluster_nodes"
    __table_args__ = (UniqueConstraint("cluster_id", "hardware_node_id", name="uq_cluster_node"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_id: Mapped[str] = mapped_column(
        ForeignKey("kubernetes_clusters.id", ondelete="CASCADE"), nullable=False
    )
    hardware_node_id: Mapped[str] = mapped_column(
        ForeignKey("hardware_nodes.id", ondelete="CASCADE"), nullable=False
    )


class VirtualMachine(Base):
    __tablename__ = "virtual_machines"
    __table_args__ = (
        UniqueConstraint("subnet_id", "ip", name="uq_virtual_machines_subnet_ip"),
        Index(
            "uq_virtual_machines_subnet_hostname_lower",
            "subnet_id",
            func.lower(text("hostname")),
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subnet_id: Mapped[str] = mapped_column(ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False)
    host_node_id: Mapped[str] = mapped_column(ForeignKey("hardware_nodes.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)


class StorageServer(Base):
    __tablename__ = "storage_servers"
    __table_args__ = (
        UniqueConstraint("subnet_id", "ip", name="uq_storage_servers_subnet_ip"),
        Index("uq_storage_servers_subnet_hostname_lower", "subnet_id", func.lower(text("hostname")), unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subnet_id: Mapped[str] = mapped_column(ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)


class NetworkSwitch(Base):
    __tablename__ = "network_switches"
    __table_args__ = (
        UniqueConstraint("subnet_id", "ip", name="uq_network_switches_subnet_ip"),
        Index("uq_network_switches_subnet_hostname_lower", "subnet_id", func.lower(text("hostname")), unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subnet_id: Mapped[str] = mapped_column(ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)


class SoftwareSystem(Base):
    __tablename__ = "software_systems"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)


class DeploymentInstance(Base):
    __tablename__ = "deployment_instances"
    __table_args__ = (
        CheckConstraint(
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
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    system_id: Mapped[str] = mapped_column(ForeignKey("software_systems.id", ondelete="CASCADE"), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_hardware_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("hardware_nodes.id", ondelete="CASCADE"), nullable=True
    )
    target_vm_id: Mapped[str | None] = mapped_column(
        ForeignKey("virtual_machines.id", ondelete="CASCADE"), nullable=True
    )
    target_cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey("kubernetes_clusters.id", ondelete="CASCADE"), nullable=True
    )
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

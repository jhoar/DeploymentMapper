from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractContextManager

from sqlalchemy import Select, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from deployment_mapper.persistence.models import (
    Base,
    DeploymentInstance,
    HardwareNode,
    KubernetesCluster,
    NetworkSwitch,
    SoftwareSystem,
    StorageServer,
    Subnet,
    VirtualMachine,
)


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session: Session | None = None

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def __enter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session is None:
            return
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()


class _BaseRepository:
    model = None

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity):
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id: str):
        return self.session.get(self.model, entity_id)

    def list(self):
        return self.session.scalars(select(self.model)).all()

    def delete(self, entity_id: str) -> None:
        entity = self.get(entity_id)
        if entity is not None:
            self.session.delete(entity)


class SubnetRepository(_BaseRepository):
    model = Subnet

    def get_by_cidr(self, cidr: str) -> Subnet | None:
        return self.session.scalar(select(Subnet).where(Subnet.cidr == cidr))


class HardwareNodeRepository(_BaseRepository):
    model = HardwareNode

    def list_by_subnet(self, subnet_id: str) -> list[HardwareNode]:
        return self.session.scalars(select(HardwareNode).where(HardwareNode.subnet_id == subnet_id)).all()


class KubernetesClusterRepository(_BaseRepository):
    model = KubernetesCluster

    def list_by_subnet(self, subnet_id: str) -> list[KubernetesCluster]:
        return self.session.scalars(
            select(KubernetesCluster).where(KubernetesCluster.subnet_id == subnet_id)
        ).all()


class VirtualMachineRepository(_BaseRepository):
    model = VirtualMachine

    def list_by_host(self, host_node_id: str) -> list[VirtualMachine]:
        return self.session.scalars(select(VirtualMachine).where(VirtualMachine.host_node_id == host_node_id)).all()


class StorageServerRepository(_BaseRepository):
    model = StorageServer


class NetworkSwitchRepository(_BaseRepository):
    model = NetworkSwitch


class SoftwareSystemRepository(_BaseRepository):
    model = SoftwareSystem


class DeploymentInstanceRepository(_BaseRepository):
    model = DeploymentInstance

    def list_by_system(self, system_id: str) -> list[DeploymentInstance]:
        return self.session.scalars(
            select(DeploymentInstance).where(DeploymentInstance.system_id == system_id)
        ).all()

    def list_by_kind(self, target_kind: str) -> list[DeploymentInstance]:
        return self.session.scalars(
            select(DeploymentInstance).where(DeploymentInstance.target_kind == target_kind)
        ).all()

    def list_systems_in_subnet(self, subnet_id: str) -> list[SoftwareSystem]:
        stmt: Select[tuple[SoftwareSystem]] = (
            select(SoftwareSystem)
            .join(DeploymentInstance, DeploymentInstance.system_id == SoftwareSystem.id)
            .join(
                HardwareNode,
                DeploymentInstance.target_hardware_node_id == HardwareNode.id,
                isouter=True,
            )
            .join(VirtualMachine, DeploymentInstance.target_vm_id == VirtualMachine.id, isouter=True)
            .join(
                KubernetesCluster,
                DeploymentInstance.target_cluster_id == KubernetesCluster.id,
                isouter=True,
            )
            .where(
                (HardwareNode.subnet_id == subnet_id)
                | (VirtualMachine.subnet_id == subnet_id)
                | (KubernetesCluster.subnet_id == subnet_id)
            )
            .distinct()
        )
        return self.session.scalars(stmt).all()


def bootstrap_repositories(session: Session) -> dict[str, _BaseRepository]:
    return {
        "subnets": SubnetRepository(session),
        "hardware_nodes": HardwareNodeRepository(session),
        "kubernetes_clusters": KubernetesClusterRepository(session),
        "virtual_machines": VirtualMachineRepository(session),
        "storage_servers": StorageServerRepository(session),
        "network_switches": NetworkSwitchRepository(session),
        "software_systems": SoftwareSystemRepository(session),
        "deployment_instances": DeploymentInstanceRepository(session),
    }

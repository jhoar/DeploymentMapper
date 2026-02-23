from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")
from sqlalchemy.exc import IntegrityError

from deployment_mapper.persistence.models import (
    Base,
    DeploymentInstance,
    HardwareNode,
    SoftwareSystem,
    Subnet,
    VirtualMachine,
)
from deployment_mapper.repositories.sqlalchemy_repositories import (
    DeploymentInstanceRepository,
    SubnetRepository,
    UnitOfWork,
)


def test_unique_subnet_cidr_constraint() -> None:
    uow = UnitOfWork("sqlite+pysqlite:///:memory:")
    uow.create_schema()

    with pytest.raises(IntegrityError):
        with uow as tx:
            tx.session.add(Subnet(id="s1", cidr="10.0.0.0/24", name="one"))
            tx.session.add(Subnet(id="s2", cidr="10.0.0.0/24", name="two"))


def test_unique_host_identity_per_subnet_case_insensitive() -> None:
    uow = UnitOfWork("sqlite+pysqlite:///:memory:")
    uow.create_schema()

    with pytest.raises(IntegrityError):
        with uow as tx:
            tx.session.add(Subnet(id="s1", cidr="10.0.1.0/24", name="one"))
            tx.session.add(HardwareNode(id="h1", subnet_id="s1", hostname="NODE-A", ip="10.0.1.10", kind="PHYSICAL"))
            tx.session.add(HardwareNode(id="h2", subnet_id="s1", hostname="node-a", ip="10.0.1.11", kind="PHYSICAL"))


def test_deployment_target_check_constraint() -> None:
    uow = UnitOfWork("sqlite+pysqlite:///:memory:")
    uow.create_schema()

    with pytest.raises(IntegrityError):
        with uow as tx:
            tx.session.add(Subnet(id="s1", cidr="10.0.2.0/24", name="one"))
            tx.session.add(HardwareNode(id="h1", subnet_id="s1", hostname="host-1", ip="10.0.2.10", kind="PHYSICAL"))
            tx.session.add(SoftwareSystem(id="sys1", name="system"))
            tx.session.add(
                DeploymentInstance(
                    id="d1",
                    system_id="sys1",
                    target_kind="HOST",
                    target_hardware_node_id="h1",
                    namespace="invalid",
                )
            )


def test_repository_queries() -> None:
    uow = UnitOfWork("sqlite+pysqlite:///:memory:")
    uow.create_schema()

    with uow as tx:
        subnet_repo = SubnetRepository(tx.session)
        deploy_repo = DeploymentInstanceRepository(tx.session)

        subnet_repo.add(Subnet(id="s1", cidr="10.0.3.0/24", name="one"))
        tx.session.add(HardwareNode(id="h1", subnet_id="s1", hostname="host-1", ip="10.0.3.10", kind="PHYSICAL"))
        tx.session.add(VirtualMachine(id="vm1", subnet_id="s1", host_node_id="h1", hostname="vm-1", ip="10.0.3.20"))
        tx.session.add(SoftwareSystem(id="sys1", name="system-1"))
        deploy_repo.add(
            DeploymentInstance(
                id="d1",
                system_id="sys1",
                target_kind="VM",
                target_vm_id="vm1",
            )
        )

        systems = deploy_repo.list_systems_in_subnet("s1")
        assert [s.id for s in systems] == ["sys1"]

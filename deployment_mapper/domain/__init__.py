from .models import (
    DeploymentInstance,
    DeploymentSchema,
    DeploymentTargetKind,
    HardwareNode,
    KubernetesCluster,
    NetworkSwitch,
    NodeKind,
    SoftwareSystem,
    StorageServer,
    Subnet,
    ValidationError,
    VirtualMachine,
)

DEMO_DATASET_NAME = "baseline-demo"


def build_demo_schema() -> DeploymentSchema:
    from .demo_dataset import build_demo_schema as _build_demo_schema

    return _build_demo_schema()


__all__ = [
    "Subnet",
    "HardwareNode",
    "KubernetesCluster",
    "VirtualMachine",
    "StorageServer",
    "NetworkSwitch",
    "SoftwareSystem",
    "DeploymentInstance",
    "DeploymentSchema",
    "NodeKind",
    "DeploymentTargetKind",
    "ValidationError",
    "DEMO_DATASET_NAME",
    "build_demo_schema",
]

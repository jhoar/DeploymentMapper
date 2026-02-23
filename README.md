# DeploymentMapper

DeploymentMapper provides a typed domain schema for describing infrastructure topology and software deployments.  
It includes strict validation for relationships, required fields, and uniqueness constraints so invalid input is caught early.

## Platform requirements

- **Operating system**: Linux, macOS, or Windows (WSL recommended on Windows).
- **Python**: 3.11+ (3.12 tested in this repository).
- **Dependencies**: standard library only (no third-party runtime dependencies currently required).

## Installation

Because this repository currently ships source files directly (without packaging metadata like `pyproject.toml`), use one of the following approaches.

### Option A: Clone and run with `PYTHONPATH` (recommended for now)

```bash
git clone <your-repo-url> DeploymentMapper
cd DeploymentMapper
export PYTHONPATH="$PWD"
```

Windows PowerShell:

```powershell
git clone <your-repo-url> DeploymentMapper
cd DeploymentMapper
$env:PYTHONPATH = (Get-Location).Path
```

### Option B: Vendor the package into another project

Copy the `deployment_mapper/` directory into your codebase and import from `deployment_mapper.domain`.

## Quick start

### Build and validate the in-repo demo dataset

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from deployment_mapper.domain import DEMO_DATASET_NAME, build_demo_schema

schema = build_demo_schema()
print(f"Loaded demo: {DEMO_DATASET_NAME}")
print(f"Subnets: {len(schema.subnets)}")
print(f"Deployment instances: {len(schema.deployment_instances)}")
PY
```

Expected output is similar to:

```text
Loaded demo: baseline-demo
Subnets: 2
Deployment instances: 2
```

### Run the demo module directly (cross-platform)

From the repository root:

```bash
python -m deployment_mapper.domain.demo_dataset
```

Windows PowerShell (same command):

```powershell
python -m deployment_mapper.domain.demo_dataset
```

> Note: running `python .\deployment_mapper\domain\demo_dataset.py` executes the file as a standalone script, which breaks relative imports like `from .models import ...`. Use `-m` so Python runs it as part of the `deployment_mapper` package.

### Validate your own schema in code

```python
from deployment_mapper.domain import (
    DeploymentSchema,
    DeploymentInstance,
    DeploymentTargetKind,
    HardwareNode,
    SoftwareSystem,
    Subnet,
)

schema = DeploymentSchema(
    subnets=[Subnet(id="s1", cidr="10.0.0.0/24", name="prod")],
    hardware_nodes=[
        HardwareNode(id="h1", hostname="host-1", ip_address="10.0.0.10", subnet_id="s1")
    ],
    software_systems=[SoftwareSystem(id="sys1", name="payments")],
    deployment_instances=[
        DeploymentInstance(
            id="dep1",
            system_id="sys1",
            target_kind=DeploymentTargetKind.HOST,
            target_node_id="h1",
        )
    ],
)

schema.validate()  # raises ValidationError on invalid models/relationships
```

## Domain model overview

The schema package is `deployment_mapper.domain` and includes:

- `Subnet`
- `HardwareNode`
- `KubernetesCluster`
- `VirtualMachine`
- `StorageServer`
- `NetworkSwitch`
- `SoftwareSystem`
- `DeploymentInstance`
- `DeploymentSchema` (aggregate + validation entrypoint)
- Enums:
  - `NodeKind`: `PHYSICAL`, `VM`, `K8S_NODE`, `STORAGE`, `SWITCH`
  - `DeploymentTargetKind`: `HOST`, `VM`, `K8S_NAMESPACE`, `CLUSTER`

## Input data formats

DeploymentMapper currently supports two practical input formats:

1. **Python object graph** using the dataclass models directly.
2. **JSON payloads** that can be parsed by your own loader and mapped to the dataclasses.

A complete example JSON payload is included at:

- `examples/demo_input_dataset.json`

### JSON structure

Top-level arrays:

- `subnets`
- `hardware_nodes`
- `kubernetes_clusters`
- `virtual_machines`
- `storage_servers`
- `network_switches`
- `software_systems`
- `deployment_instances`

Key relationship fields:

- `HardwareNode.subnet_id` → `Subnet.id`
- `VirtualMachine.subnet_id` → `Subnet.id`
- `VirtualMachine.host_node_id` → `HardwareNode.id`
- `KubernetesCluster.subnet_id` → `Subnet.id`
- `KubernetesCluster.node_ids[]` → `HardwareNode.id`
- `DeploymentInstance.system_id` → `SoftwareSystem.id`
- `DeploymentInstance.target_node_id` → `HardwareNode.id` or `VirtualMachine.id` (depends on `target_kind`)
- `DeploymentInstance.target_cluster_id` → `KubernetesCluster.id` (for cluster/namespace targets)
- `DeploymentInstance.component_id` (optional; service/component-level deployment)

## Validation and constraints

Validation is triggered with:

```python
schema.validate()
```

Checks include:

- Required fields on each model.
- CIDR and IP format checks.
- Relationship existence checks across IDs.
- Deployment target logic:
  - `HOST` requires `target_node_id` (hardware node).
  - `VM` requires `target_node_id` (VM).
  - `CLUSTER` requires `target_cluster_id`.
  - `K8S_NAMESPACE` requires `target_cluster_id` and `namespace`.
- Uniqueness:
  - IDs per object type.
  - `Subnet.cidr` uniqueness.
  - Hostname uniqueness per subnet (case-insensitive).
  - IP uniqueness per subnet.

## Database schema (reference mapping)

This project currently validates an **in-memory domain schema** rather than connecting to a database directly.  
If you need persistence, the following relational mapping is a recommended starting point.

### Suggested tables

- `subnets(id PK, cidr UNIQUE, name)`
- `hardware_nodes(id PK, hostname, ip_address, subnet_id FK, kind)`
- `kubernetes_clusters(id PK, name, subnet_id FK)`
- `kubernetes_cluster_nodes(cluster_id FK, node_id FK, PRIMARY KEY(cluster_id, node_id))`
- `virtual_machines(id PK, hostname, ip_address, subnet_id FK, host_node_id FK)`
- `storage_servers(id PK, hostname, ip_address, subnet_id FK)`
- `network_switches(id PK, hostname, management_ip, subnet_id FK)`
- `software_systems(id PK, name, version)`
- `deployment_instances(id PK, system_id FK, target_kind, target_node_id NULL, target_cluster_id NULL, component_id NULL, namespace NULL)`

### Suggested uniqueness indexes

- `subnets(cidr)` unique.
- `hardware_nodes(subnet_id, lower(hostname))` unique.
- `hardware_nodes(subnet_id, ip_address)` unique.
- Equivalent `(subnet_id, lower(hostname))` and `(subnet_id, ip)` unique indexes for VM/storage/switch tables.

### Suggested target integrity checks

- Check constraints ensuring valid combinations of `target_kind`, `target_node_id`, `target_cluster_id`, and `namespace`.
- Foreign keys from deployment target columns to the corresponding entity tables.

## Demo assets

- Programmatic demo builder: `deployment_mapper/domain/demo_dataset.py`
- JSON demo payload: `examples/demo_input_dataset.json`

## License

MIT (see `LICENSE`).

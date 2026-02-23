# DeploymentMapper

DeploymentMapper is currently a **Python domain-model library + demos** for describing infrastructure topology and software deployment placement.

It is **not yet a full server application**. There is no HTTP API, no persistence layer, and no packaged release metadata yet.

## Current application status

### What exists today

- Typed domain models in `deployment_mapper.domain.models` for:
  - `Subnet`
  - `HardwareNode`
  - `KubernetesCluster`
  - `VirtualMachine`
  - `StorageServer`
  - `NetworkSwitch`
  - `SoftwareSystem`
  - `DeploymentInstance`
- Enum types:
  - `NodeKind` (`PHYSICAL`, `VM`, `K8S_NODE`, `STORAGE`, `SWITCH`)
  - `DeploymentTargetKind` (`HOST`, `VM`, `K8S_NAMESPACE`, `CLUSTER`)
- Validation logic (`DeploymentSchema.validate()`) for:
  - required fields
  - CIDR and IP format checks
  - cross-object relationship checks
  - uniqueness constraints (IDs, subnet CIDR, hostname/IP per subnet)
- Demo workflows:
  - Build/validate an in-memory demo dataset
  - Generate PlantUML from demo data
  - Load JSON example and generate PlantUML

### What does not exist yet

- No REST/gRPC server
- No database integration or migrations
- No authentication/authorization
- No packaged installer (`pyproject.toml`) or container image

---

## Platform requirements

- **OS**: Linux, macOS, Windows (PowerShell supported)
- **Python**: 3.11+ (3.12 tested)
- **Runtime dependencies**: standard library only

## Installation (source mode)

This repo is currently source-first. From repository root:

### Linux/macOS

```bash
export PYTHONPATH="$PWD"
```

### Windows PowerShell

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

> If you are in repo root, `python -m ...` commands generally work without setting `PYTHONPATH`.

---

## Quick start

### 1) Run the demo dataset builder

```bash
python -m deployment_mapper.domain.demo_dataset
```

Expected output:

```text
Loaded demo: baseline-demo
Subnets: 2
Deployment instances: 2
```

### 2) Generate UML from in-code demo dataset

```bash
python -m deployment_mapper.domain.uml_demo
```

Output file:

- `examples/demo_deployment_diagram.puml`

### 3) Generate UML by reading JSON input

```bash
python -m deployment_mapper.domain.json_uml_demo
```

Reads:

- `examples/demo_input_dataset.json`

Writes:

- `examples/demo_input_dataset_diagram.puml`

---

## Public API (current)

Import from `deployment_mapper.domain`:

- `build_demo_schema()`
- `generate_demo_plantuml()`
- `load_schema_from_json_file(path)`
- All domain model classes and enums

Example:

```python
from deployment_mapper.domain import load_schema_from_json_file

schema = load_schema_from_json_file("examples/demo_input_dataset.json")
schema.validate()
print(len(schema.subnets), len(schema.deployment_instances))
```

---

## Input JSON format

Example file: `examples/demo_input_dataset.json`

Top-level arrays:

- `subnets`
- `hardware_nodes`
- `kubernetes_clusters`
- `virtual_machines`
- `storage_servers`
- `network_switches`
- `software_systems`
- `deployment_instances`

Important relationship fields:

- `HardwareNode.subnet_id -> Subnet.id`
- `VirtualMachine.subnet_id -> Subnet.id`
- `VirtualMachine.host_node_id -> HardwareNode.id`
- `KubernetesCluster.subnet_id -> Subnet.id`
- `KubernetesCluster.node_ids[] -> HardwareNode.id`
- `DeploymentInstance.system_id -> SoftwareSystem.id`
- `DeploymentInstance.target_node_id` or `target_cluster_id` depending on `target_kind`

---

## UML generation notes

- UML output is generated in PlantUML format (`.puml`).
- Alias generation is normalized to PlantUML-safe identifiers.
- Render with PlantUML locally or in your preferred renderer.

---

## Recommended next milestones (to become a full app)

1. Add API layer (e.g., FastAPI) for validate/generate endpoints.
2. Add persistence (SQLAlchemy + migrations).
3. Add tests and CI.
4. Add packaging (`pyproject.toml`) and containerization.

---

## License

MIT (see `LICENSE`).

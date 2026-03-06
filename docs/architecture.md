# DeploymentMapper Architecture

## Runtime Flow
1. `DeploymentMapperCli` resolves input files and output paths.
2. `YamlManifestReader` parses each YAML file into typed `ManifestData`.
3. `ManifestValidator.validateSingle` enforces schema/enum/required-field checks per file.
4. `ManifestMerger` merges all manifests with strict conflict rules and normalization.
5. `ManifestValidator.validateMerged` enforces cross-entity references and target existence.
6. `Neo4jEmbeddedManager` opens a file-backed embedded Neo4j database.
7. `SchemaInitializer` applies constraints and indexes.
8. `GraphWriter` writes nodes/relationships in deterministic order.
9. `DiagramProjectionService` reads from Neo4j and builds a diagram model.
10. `PlantUmlTextBuilder` emits PlantUML source and `PlantUmlRenderer` renders PNG.

## Validation Rules Implemented
- Strict fail-fast behavior.
- Fill-missing merge semantics for duplicate IDs, conflict on differing non-empty values.
- Node identity checks (`nodeId <-> hostname`) across merged files.
- Environment uniqueness checks by project/type and project/name.
- Deployment uniqueness checks by `(componentId, projectId, envId)`.
- Mount uniqueness checks by `(nodeId, volumeId)` and `(clusterId, volumeId)`.
- Target/reference validation for deployments, roles, mounts, subnet connections, and K8s service routes.
- VM hosting validation: `Nodes.hostedByNodeId` only on VM nodes, existing host required, host must be `Physical` and have `hypervisor` role.

## Diagram Policies
- One merged output diagram per run (`.puml` + `.png`).
- Grid deployment edges only to clusters (`DEPLOYED_TO_CLUSTER`).
- Cluster-mounted volumes attached to clusters.
- Subnet labels are `name | cidr | VLAN <vlan>`.
- `CONNECTED_TO_SUBNET` is rendered as dotted edges.
- VM hosting edges are rendered as solid `HOSTED_BY` edges from VM node to hypervisor node.

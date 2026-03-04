# CODEX_CONTEXT.md

## Rules
- Normalize: lowercase, trim, spaces -> `_`.
- Conflicts: fill missing else error.
- Node identity: nodeId<->hostname must be consistent.
- Deployments cannot reference unknown hostnames.

## Targets
- DEPLOYED_TO (Node)
- DEPLOYED_TO_CLUSTER (Grid)
- DEPLOYED_TO_WORKLOAD (K8s)
- For K8s: also create DEPLOYED_TO to endpoint nodes.

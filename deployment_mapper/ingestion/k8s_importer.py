from __future__ import annotations

from typing import Any

from deployment_mapper.domain.models import DeploymentInstance, DeploymentSchema, DeploymentTargetKind, KubernetesCluster, SoftwareSystem
from deployment_mapper.ingestion.diagnostics import DiagnosticLevel, ImportDiagnostics


def import_k8s_data(
    payload: dict[str, Any],
    *,
    known_node_ids: set[str],
    known_subnet_ids: set[str],
) -> tuple[DeploymentSchema, ImportDiagnostics]:
    diagnostics = ImportDiagnostics()
    schema = DeploymentSchema()

    known_system_ids: set[str] = set()
    for cluster_payload in payload.get("clusters", []):
        subnet_id = cluster_payload.get("subnet_id")
        if subnet_id not in known_subnet_ids:
            diagnostics.add(
                "missing_reference",
                "Cluster references unknown subnet.",
                level=DiagnosticLevel.ERROR,
                entity="kubernetes_cluster",
                entity_id=cluster_payload.get("id"),
                field="subnet_id",
                missing_id=subnet_id,
            )
            continue

        node_ids: list[str] = []
        for node_id in cluster_payload.get("node_ids", []):
            if node_id not in known_node_ids:
                diagnostics.add(
                    "missing_reference",
                    "Cluster node placement references unknown hardware node.",
                    level=DiagnosticLevel.ERROR,
                    entity="kubernetes_cluster",
                    entity_id=cluster_payload.get("id"),
                    field="node_ids",
                    missing_id=node_id,
                )
                continue
            node_ids.append(node_id)

        cluster = KubernetesCluster(
            id=cluster_payload["id"],
            name=cluster_payload["name"],
            subnet_id=subnet_id,
            node_ids=node_ids,
        )
        schema.kubernetes_clusters.append(cluster)

        for namespace_payload in cluster_payload.get("namespaces", []):
            namespace = namespace_payload.get("name")
            for workload in namespace_payload.get("workloads", []):
                system_id = workload["system_id"]
                if system_id not in known_system_ids:
                    schema.software_systems.append(
                        SoftwareSystem(
                            id=system_id,
                            name=workload.get("system_name", system_id),
                            version=workload.get("version"),
                        )
                    )
                    known_system_ids.add(system_id)

                deployment_id = workload.get("deployment_id", f"{cluster.id}:{namespace}:{system_id}")
                schema.deployment_instances.append(
                    DeploymentInstance(
                        id=deployment_id,
                        system_id=system_id,
                        target_kind=DeploymentTargetKind.K8S_NAMESPACE,
                        target_cluster_id=cluster.id,
                        namespace=namespace,
                        component_id=workload.get("component_id"),
                    )
                )

    return schema, diagnostics

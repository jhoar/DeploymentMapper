package com.esa.deploymentmapper.graph;

import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Transaction;

import java.util.List;

public class SchemaInitializer {
    private static final List<String> DDL = List.of(
            "CREATE CONSTRAINT manifest_id IF NOT EXISTS FOR (m:Manifest) REQUIRE m.manifestId IS UNIQUE",
            "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.orgId IS UNIQUE",
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.projectId IS UNIQUE",
            "CREATE CONSTRAINT app_id IF NOT EXISTS FOR (a:Application) REQUIRE a.appId IS UNIQUE",
            "CREATE CONSTRAINT component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.componentId IS UNIQUE",
            "CREATE CONSTRAINT env_projectEnvId IF NOT EXISTS FOR (e:Environment) REQUIRE e.projectEnvId IS UNIQUE",
            "CREATE CONSTRAINT env_projectTypeKey IF NOT EXISTS FOR (e:Environment) REQUIRE e.projectTypeKey IS UNIQUE",
            "CREATE CONSTRAINT env_projectNameKey IF NOT EXISTS FOR (e:Environment) REQUIRE e.projectNameKey IS UNIQUE",
            "CREATE CONSTRAINT deployment_id IF NOT EXISTS FOR (d:Deployment) REQUIRE d.deploymentId IS UNIQUE",
            "CREATE CONSTRAINT deployment_key IF NOT EXISTS FOR (d:Deployment) REQUIRE d.deploymentKey IS UNIQUE",
            "CREATE CONSTRAINT node_id IF NOT EXISTS FOR (n:Node) REQUIRE n.nodeId IS UNIQUE",
            "CREATE CONSTRAINT node_hostname IF NOT EXISTS FOR (n:Node) REQUIRE n.hostname IS UNIQUE",
            "CREATE CONSTRAINT cluster_id IF NOT EXISTS FOR (c:Cluster) REQUIRE c.clusterId IS UNIQUE",
            "CREATE CONSTRAINT filer_id IF NOT EXISTS FOR (f:Filer) REQUIRE f.filerId IS UNIQUE",
            "CREATE CONSTRAINT volume_id IF NOT EXISTS FOR (v:Volume) REQUIRE v.volumeId IS UNIQUE",
            "CREATE CONSTRAINT network_id IF NOT EXISTS FOR (n:Network) REQUIRE n.networkId IS UNIQUE",
            "CREATE CONSTRAINT subnet_id IF NOT EXISTS FOR (s:Subnet) REQUIRE s.subnetId IS UNIQUE",
            "CREATE CONSTRAINT subnet_cidr_unique IF NOT EXISTS FOR (s:Subnet) REQUIRE s.cidr IS UNIQUE",
            "CREATE CONSTRAINT subnet_vlanKey_unique IF NOT EXISTS FOR (s:Subnet) REQUIRE s.vlanKey IS UNIQUE",
            "CREATE CONSTRAINT k8s_namespace_id IF NOT EXISTS FOR (ns:K8sNamespace) REQUIRE ns.namespaceId IS UNIQUE",
            "CREATE CONSTRAINT k8s_workload_id IF NOT EXISTS FOR (w:K8sWorkload) REQUIRE w.workloadId IS UNIQUE",
            "CREATE CONSTRAINT k8s_pod_id IF NOT EXISTS FOR (p:K8sPod) REQUIRE p.podId IS UNIQUE",
            "CREATE CONSTRAINT k8s_service_id IF NOT EXISTS FOR (s:K8sService) REQUIRE s.serviceId IS UNIQUE",
            "CREATE INDEX env_type IF NOT EXISTS FOR (e:Environment) ON (e.type)",
            "CREATE INDEX node_type IF NOT EXISTS FOR (n:Node) ON (n.type)",
            "CREATE INDEX subnet_vlan IF NOT EXISTS FOR (s:Subnet) ON (s.vlan)",
            "CREATE INDEX volume_protocol IF NOT EXISTS FOR (v:Volume) ON (v.protocol)",
            "CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)"
    );

    public void initialize(GraphDatabaseService database) {
        try (Transaction tx = database.beginTx()) {
            for (String statement : DDL) {
                tx.execute(statement);
            }
            tx.commit();
        }
    }
}

package com.esa.deploymentmapper.graph;

import com.esa.deploymentmapper.model.ManifestData;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Transaction;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class GraphWriter {
    public void write(GraphDatabaseService database, ManifestData data) {
        try (Transaction tx = database.beginTx()) {
            writeManifest(tx, data);
            writeOrganizations(tx, data.organizations());
            writeProjects(tx, data.projects());
            writeApplications(tx, data.applications());
            writeComponents(tx, data.components());
            writeEnvironments(tx, data.environments());
            writeNodes(tx, data.nodes());
            writeHostedByEdges(tx, data.nodes());
            writeNodeRoles(tx, data.nodeRoles());
            writeClusters(tx, data.clusters());
            writeClusterRoles(tx, data.clusterRoles());
            writeGridMembers(tx, data.gridMembers());
            writeClusterEndpoints(tx, data.clusterEndpoints());
            writeK8s(tx, data);
            writeFilers(tx, data.filers());
            writeFilerRoles(tx, data.filerRoles());
            writeVolumes(tx, data.volumes());
            writeMounts(tx, data.mounts());
            writeNetworks(tx, data.networks());
            writeSubnets(tx, data.subnets());
            writeSubnetConnections(tx, data.subnetConnections());
            writeDeployments(tx, data.deployments());
            tx.commit();
        }
    }

    private void writeManifest(Transaction tx, ManifestData data) {
        if (data.manifest() == null) {
            return;
        }
        execute(tx,
                "MERGE (m:Manifest {manifestId:$manifestId}) SET m.path=$path",
                Map.of("manifestId", data.manifest().manifestId(), "path", data.manifest().path()));
    }

    private void writeOrganizations(Transaction tx, List<ManifestData.Organization> organizations) {
        for (ManifestData.Organization organization : organizations) {
            execute(tx,
                    "MERGE (o:Organization {orgId:$orgId}) SET o.name=$name",
                    Map.of("orgId", organization.orgId(), "name", organization.name()));
        }
    }

    private void writeProjects(Transaction tx, List<ManifestData.Project> projects) {
        for (ManifestData.Project project : projects) {
            execute(tx,
                    "MERGE (p:Project {projectId:$projectId}) SET p.name=$name " +
                            "WITH p MATCH (o:Organization {orgId:$orgId}) MERGE (o)-[:HAS_PROJECT]->(p)",
                    Map.of("projectId", project.projectId(), "name", project.name(), "orgId", project.orgId()));
        }
    }

    private void writeApplications(Transaction tx, List<ManifestData.Application> applications) {
        for (ManifestData.Application application : applications) {
            execute(tx,
                    "MERGE (a:Application {appId:$appId}) SET a.name=$name, a.configurationId=$configurationId, a.version=$version " +
                            "WITH a MATCH (p:Project {projectId:$projectId}) MERGE (p)-[:HAS_APPLICATION]->(a)",
                    Map.of(
                            "appId", application.appId(),
                            "name", application.name(),
                            "configurationId", application.configurationId(),
                            "version", application.version(),
                            "projectId", application.projectId()
                    ));
        }
    }

    private void writeComponents(Transaction tx, List<ManifestData.Component> components) {
        for (ManifestData.Component component : components) {
            execute(tx,
                    "MERGE (c:Component {componentId:$componentId}) SET c.name=$name, c.version=$version " +
                            "WITH c MATCH (a:Application {appId:$appId}) MERGE (a)-[:OWNS_COMPONENT]->(c)",
                    Map.of("componentId", component.componentId(), "name", component.name(), "version", component.version(), "appId", component.appId()));
        }
    }

    private void writeEnvironments(Transaction tx, List<ManifestData.Environment> environments) {
        for (ManifestData.Environment environment : environments) {
            String projectEnvId = environment.projectId() + ":" + environment.envId();
            String projectTypeKey = environment.projectId() + ":" + environment.type();
            String projectNameKey = environment.projectId() + ":" + environment.name();
            execute(tx,
                    "MERGE (e:Environment {projectEnvId:$projectEnvId}) " +
                            "SET e.envId=$envId, e.projectId=$projectId, e.name=$name, e.type=$type, e.projectTypeKey=$projectTypeKey, e.projectNameKey=$projectNameKey " +
                            "WITH e MATCH (p:Project {projectId:$projectId}) MERGE (p)-[:HAS_ENVIRONMENT]->(e)",
                    Map.of(
                            "projectEnvId", projectEnvId,
                            "envId", environment.envId(),
                            "projectId", environment.projectId(),
                            "name", environment.name(),
                            "type", environment.type(),
                            "projectTypeKey", projectTypeKey,
                            "projectNameKey", projectNameKey
                    ));
        }
    }

    private void writeNodes(Transaction tx, List<ManifestData.Node> nodes) {
        for (ManifestData.Node node : nodes) {
            execute(tx,
                    "MERGE (n:Node {nodeId:$nodeId}) SET n.hostname=$hostname, n.ipAddress=$ipAddress, n.type=$type, n.hostedByNodeId=$hostedByNodeId",
                    Map.of(
                            "nodeId", node.nodeId(),
                            "hostname", node.hostname(),
                            "ipAddress", node.ipAddress(),
                            "type", node.type(),
                            "hostedByNodeId", node.hostedByNodeId()
                    ));
        }
    }

    private void writeHostedByEdges(Transaction tx, List<ManifestData.Node> nodes) {
        for (ManifestData.Node node : nodes) {
            if (node.hostedByNodeId() == null || node.hostedByNodeId().isBlank()) {
                continue;
            }
            execute(tx,
                    "MATCH (vm:Node {nodeId:$nodeId}), (hv:Node {nodeId:$hostedByNodeId}) MERGE (vm)-[:HOSTED_BY]->(hv)",
                    Map.of("nodeId", node.nodeId(), "hostedByNodeId", node.hostedByNodeId()));
        }
    }

    private void writeNodeRoles(Transaction tx, List<ManifestData.NodeRoles> roles) {
        for (ManifestData.NodeRoles roleSet : roles) {
            for (String roleName : roleSet.roles()) {
                execute(tx,
                        "MATCH (n:Node {nodeId:$nodeId}) MERGE (r:NodeRole {nodeRoleId:$roleId}) SET r.name=$name MERGE (n)-[:HAS_ROLE]->(r)",
                        Map.of("nodeId", roleSet.nodeId(), "roleId", roleName, "name", roleName));
            }
        }
    }

    private void writeClusters(Transaction tx, List<ManifestData.Cluster> clusters) {
        for (ManifestData.Cluster cluster : clusters) {
            execute(tx,
                    "MERGE (c:Cluster {clusterId:$clusterId}) SET c.clusterName=$clusterName, c.type=$type",
                    Map.of("clusterId", cluster.clusterId(), "clusterName", cluster.clusterName(), "type", cluster.type()));
        }
    }

    private void writeClusterRoles(Transaction tx, List<ManifestData.ClusterRoles> roles) {
        for (ManifestData.ClusterRoles roleSet : roles) {
            for (String roleName : roleSet.roles()) {
                execute(tx,
                        "MATCH (c:Cluster {clusterId:$clusterId}) MERGE (r:ClusterRole {clusterRoleId:$roleId}) SET r.name=$name MERGE (c)-[:HAS_ROLE]->(r)",
                        Map.of("clusterId", roleSet.clusterId(), "roleId", roleName, "name", roleName));
            }
        }
    }

    private void writeGridMembers(Transaction tx, List<ManifestData.GridMembers> membersList) {
        for (ManifestData.GridMembers members : membersList) {
            for (String manager : members.managers()) {
                execute(tx,
                        "MATCH (c:Cluster {clusterId:$clusterId}), (n:Node {nodeId:$nodeId}) MERGE (c)-[:HAS_MANAGER]->(n)",
                        Map.of("clusterId", members.clusterId(), "nodeId", manager));
            }
            for (String worker : members.workers()) {
                execute(tx,
                        "MATCH (c:Cluster {clusterId:$clusterId}), (n:Node {nodeId:$nodeId}) MERGE (c)-[:HAS_WORKER]->(n)",
                        Map.of("clusterId", members.clusterId(), "nodeId", worker));
            }
        }
    }

    private void writeClusterEndpoints(Transaction tx, List<ManifestData.ClusterEndpoints> endpoints) {
        for (ManifestData.ClusterEndpoints endpoint : endpoints) {
            for (String nodeId : endpoint.endpointNodeIds()) {
                execute(tx,
                        "MATCH (c:Cluster {clusterId:$clusterId}), (n:Node {nodeId:$nodeId}) MERGE (c)-[:HAS_ENDPOINT]->(n)",
                        Map.of("clusterId", endpoint.clusterId(), "nodeId", nodeId));
            }
        }
    }

    private void writeK8s(Transaction tx, ManifestData data) {
        for (ManifestData.K8sNamespace namespace : data.k8sNamespaces()) {
            String namespaceId = namespace.clusterId() + ":" + namespace.namespaceName();
            execute(tx,
                    "MATCH (c:Cluster {clusterId:$clusterId}) " +
                            "MERGE (ns:K8sNamespace {namespaceId:$namespaceId}) SET ns.name=$name " +
                            "MERGE (c)-[:HAS_NAMESPACE]->(ns)",
                    Map.of("clusterId", namespace.clusterId(), "namespaceId", namespaceId, "name", namespace.namespaceName()));
        }
        for (ManifestData.K8sWorkload workload : data.k8sWorkloads()) {
            String namespaceId = workload.clusterId() + ":" + workload.namespaceName();
            String workloadId = namespaceId + ":" + workload.kind() + ":" + workload.workloadName();
            execute(tx,
                    "MATCH (ns:K8sNamespace {namespaceId:$namespaceId}) " +
                            "MERGE (w:K8sWorkload {workloadId:$workloadId}) SET w.name=$name, w.kind=$kind " +
                            "MERGE (ns)-[:HAS_WORKLOAD]->(w)",
                    Map.of("namespaceId", namespaceId, "workloadId", workloadId, "name", workload.workloadName(), "kind", workload.kind()));
        }
        for (ManifestData.K8sService service : data.k8sServices()) {
            String namespaceId = service.clusterId() + ":" + service.namespaceName();
            String serviceId = namespaceId + ":" + service.serviceName();
            execute(tx,
                    "MATCH (ns:K8sNamespace {namespaceId:$namespaceId}) " +
                            "MERGE (s:K8sService {serviceId:$serviceId}) SET s.name=$name, s.type=$type " +
                            "MERGE (ns)-[:EXPOSES_SERVICE]->(s)",
                    Map.of("namespaceId", namespaceId, "serviceId", serviceId, "name", service.serviceName(), "type", service.type()));
            if (service.routesToWorkload() != null) {
                String workloadId = namespaceId + ":" + service.routesToWorkload().kind() + ":" + service.routesToWorkload().workloadName();
                execute(tx,
                        "MATCH (s:K8sService {serviceId:$serviceId}), (w:K8sWorkload {workloadId:$workloadId}) MERGE (s)-[:ROUTES_TO_WORKLOAD]->(w)",
                        Map.of("serviceId", serviceId, "workloadId", workloadId));
            }
        }
        for (ManifestData.K8sPods podSet : data.k8sPods()) {
            String namespaceId = podSet.clusterId() + ":" + podSet.namespaceName();
            for (String podName : podSet.podNames()) {
                String podId = namespaceId + ":" + podName;
                execute(tx,
                        "MATCH (ns:K8sNamespace {namespaceId:$namespaceId}) " +
                                "MERGE (pod:K8sPod {podId:$podId}) SET pod.name=$name",
                        Map.of("namespaceId", namespaceId, "podId", podId, "name", podName));
            }
        }
    }

    private void writeFilers(Transaction tx, List<ManifestData.Filer> filers) {
        for (ManifestData.Filer filer : filers) {
            execute(tx,
                    "MERGE (f:Filer {filerId:$filerId}) SET f.name=$name, f.ipAddress=$ipAddress, f.type=$type",
                    Map.of("filerId", filer.filerId(), "name", filer.name(), "ipAddress", filer.ipAddress(), "type", filer.type()));
        }
    }

    private void writeFilerRoles(Transaction tx, List<ManifestData.FilerRoles> roles) {
        for (ManifestData.FilerRoles roleSet : roles) {
            for (String roleName : roleSet.roles()) {
                execute(tx,
                        "MATCH (f:Filer {filerId:$filerId}) MERGE (r:FilerRole {filerRoleId:$roleId}) SET r.name=$name MERGE (f)-[:HAS_ROLE]->(r)",
                        Map.of("filerId", roleSet.filerId(), "roleId", roleName, "name", roleName));
            }
        }
    }

    private void writeVolumes(Transaction tx, List<ManifestData.Volume> volumes) {
        for (ManifestData.Volume volume : volumes) {
            execute(tx,
                    "MERGE (v:Volume {volumeId:$volumeId}) SET v.name=$name, v.protocol=$protocol, v.hostedByNodeId=$hostedByNodeId " +
                            "WITH v MATCH (f:Filer {filerId:$filerId}) MERGE (f)-[:HOSTS_VOLUME]->(v)",
                    Map.of(
                            "volumeId", volume.volumeId(),
                            "name", volume.name(),
                            "protocol", volume.protocol(),
                            "hostedByNodeId", volume.hostedByNodeId(),
                            "filerId", volume.filerId()
                    ));
            if (volume.hostedByNodeId() != null && !volume.hostedByNodeId().isBlank()) {
                execute(tx,
                        "MATCH (n:Node {nodeId:$nodeId}), (v:Volume {volumeId:$volumeId}) MERGE (n)-[:HOSTS_VOLUME]->(v)",
                        Map.of("nodeId", volume.hostedByNodeId(), "volumeId", volume.volumeId()));
            }
        }
    }

    private void writeMounts(Transaction tx, List<ManifestData.Mount> mounts) {
        for (ManifestData.Mount mount : mounts) {
            Map<String, Object> params = new HashMap<>();
            params.put("volumeId", mount.volumeId());
            params.put("mountPath", mount.mountPath());
            params.put("accessMode", mount.accessMode());
            params.put("exportOrShareName", mount.exportOrShareName());
            params.put("protocolDetails", mount.protocolDetails());

            if (mount.nodeId() != null && !mount.nodeId().isBlank()) {
                params.put("nodeId", mount.nodeId());
                execute(tx,
                        "MATCH (n:Node {nodeId:$nodeId}), (v:Volume {volumeId:$volumeId}) " +
                                "MERGE (n)-[m:MOUNTS_VOLUME]->(v) " +
                                "SET m.mountPath=$mountPath, m.accessMode=$accessMode, m.exportOrShareName=$exportOrShareName, m.protocolDetails=$protocolDetails",
                        params);
            }
            if (mount.clusterId() != null && !mount.clusterId().isBlank()) {
                params.put("clusterId", mount.clusterId());
                execute(tx,
                        "MATCH (c:Cluster {clusterId:$clusterId}), (v:Volume {volumeId:$volumeId}) " +
                                "MERGE (c)-[m:MOUNTS_VOLUME]->(v) " +
                                "SET m.mountPath=$mountPath, m.accessMode=$accessMode, m.exportOrShareName=$exportOrShareName, m.protocolDetails=$protocolDetails",
                        params);
            }
        }
    }

    private void writeNetworks(Transaction tx, List<ManifestData.Network> networks) {
        for (ManifestData.Network network : networks) {
            execute(tx,
                    "MERGE (n:Network {networkId:$networkId}) SET n.name=$name",
                    Map.of("networkId", network.networkId(), "name", network.name()));
        }
    }

    private void writeSubnets(Transaction tx, List<ManifestData.Subnet> subnets) {
        for (ManifestData.Subnet subnet : subnets) {
            String vlanKey = subnet.networkId() + ":" + subnet.vlan();
            execute(tx,
                    "MERGE (s:Subnet {subnetId:$subnetId}) " +
                            "SET s.networkId=$networkId, s.name=$name, s.cidr=$cidr, s.vlan=$vlan, s.vlanKey=$vlanKey " +
                            "WITH s MATCH (n:Network {networkId:$networkId}) MERGE (n)-[:HAS_SUBNET]->(s)",
                    Map.of("subnetId", subnet.subnetId(), "networkId", subnet.networkId(), "name", subnet.name(), "cidr", subnet.cidr(), "vlan", subnet.vlan(), "vlanKey", vlanKey));
        }
    }

    private void writeSubnetConnections(Transaction tx, List<ManifestData.SubnetConnection> connections) {
        for (ManifestData.SubnetConnection connection : connections) {
            String query;
            if ("Node".equals(connection.entityType())) {
                query = "MATCH (e:Node {nodeId:$entityId}), (s:Subnet {subnetId:$subnetId}) MERGE (e)-[:CONNECTED_TO_SUBNET]->(s)";
            } else if ("Cluster".equals(connection.entityType())) {
                query = "MATCH (e:Cluster {clusterId:$entityId}), (s:Subnet {subnetId:$subnetId}) MERGE (e)-[:CONNECTED_TO_SUBNET]->(s)";
            } else if ("Filer".equals(connection.entityType())) {
                query = "MATCH (e:Filer {filerId:$entityId}), (s:Subnet {subnetId:$subnetId}) MERGE (e)-[:CONNECTED_TO_SUBNET]->(s)";
            } else {
                continue;
            }
            execute(tx, query, Map.of("entityId", connection.entityId(), "subnetId", connection.subnetId()));
        }
    }

    private void writeDeployments(Transaction tx, List<ManifestData.Deployment> deployments) {
        for (ManifestData.Deployment deployment : deployments) {
            String projectEnvId = deployment.projectId() + ":" + deployment.envId();
            String deploymentKey = deployment.componentId() + ":" + projectEnvId;
            execute(tx,
                    "MERGE (d:Deployment {deploymentId:$deploymentId}) SET d.componentId=$componentId, d.projectId=$projectId, d.envId=$envId, d.deploymentKey=$deploymentKey " +
                            "WITH d MATCH (c:Component {componentId:$componentId}), (e:Environment {projectEnvId:$projectEnvId}) " +
                            "MERGE (c)-[:HAS_DEPLOYMENT]->(d) MERGE (d)-[:IN_ENV]->(e)",
                    Map.of(
                            "deploymentId", deployment.deploymentId(),
                            "componentId", deployment.componentId(),
                            "projectId", deployment.projectId(),
                            "envId", deployment.envId(),
                            "deploymentKey", deploymentKey,
                            "projectEnvId", projectEnvId
                    ));

            for (String nodeId : deployment.targets().nodes()) {
                execute(tx,
                        "MATCH (d:Deployment {deploymentId:$deploymentId}), (n:Node {nodeId:$nodeId}) MERGE (d)-[:DEPLOYED_TO]->(n)",
                        Map.of("deploymentId", deployment.deploymentId(), "nodeId", nodeId));
            }

            for (String clusterId : deployment.targets().gridClusters()) {
                execute(tx,
                        "MATCH (d:Deployment {deploymentId:$deploymentId}), (c:Cluster {clusterId:$clusterId, type:'Grid'}) MERGE (d)-[:DEPLOYED_TO_CLUSTER]->(c)",
                        Map.of("deploymentId", deployment.deploymentId(), "clusterId", clusterId));
            }

            for (ManifestData.K8sWorkloadRef workloadRef : deployment.targets().k8sWorkloads()) {
                String namespaceId = workloadRef.clusterId() + ":" + workloadRef.namespaceName();
                String workloadId = namespaceId + ":" + workloadRef.kind() + ":" + workloadRef.workloadName();
                execute(tx,
                        "MATCH (d:Deployment {deploymentId:$deploymentId}), (w:K8sWorkload {workloadId:$workloadId}) MERGE (d)-[:DEPLOYED_TO_WORKLOAD]->(w)",
                        Map.of("deploymentId", deployment.deploymentId(), "workloadId", workloadId));
                execute(tx,
                        "MATCH (d:Deployment {deploymentId:$deploymentId}), (c:Cluster {clusterId:$clusterId})-[:HAS_ENDPOINT]->(ep:Node) MERGE (d)-[:DEPLOYED_TO]->(ep)",
                        Map.of("deploymentId", deployment.deploymentId(), "clusterId", workloadRef.clusterId()));
            }
        }
    }

    private void execute(Transaction tx, String query, Map<String, Object> params) {
        tx.execute(query, params);
    }
}

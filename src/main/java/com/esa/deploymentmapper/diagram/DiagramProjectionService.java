package com.esa.deploymentmapper.diagram;

import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Result;
import org.neo4j.graphdb.Transaction;

import java.util.Map;

public class DiagramProjectionService {

    public DiagramModel project(GraphDatabaseService database) {
        DiagramModel model = new DiagramModel();
        try (Transaction tx = database.beginTx()) {
            projectDeploymentStructure(tx, model);
            projectDeploymentTargets(tx, model);
            projectNodeHosting(tx, model);
            projectStorage(tx, model);
            projectNetworking(tx, model);
            tx.commit();
        }
        return model;
    }

    private void projectDeploymentStructure(Transaction tx, DiagramModel model) {
        Result result = tx.execute(
                "MATCH (p:Project)-[:HAS_ENVIRONMENT]->(e:Environment) " +
                        "MATCH (c:Component)-[:HAS_DEPLOYMENT]->(d:Deployment)-[:IN_ENV]->(e) " +
                        "RETURN p.projectId AS projectId, e.name AS envName, e.type AS envType, c.componentId AS componentId, c.name AS componentName, d.deploymentId AS deploymentId"
        );

        while (result.hasNext()) {
            Map<String, Object> row = result.next();
            String projectId = string(row.get("projectId"));
            String envName = string(row.get("envName"));
            String envType = string(row.get("envType"));
            String componentId = string(row.get("componentId"));
            String componentName = string(row.get("componentName"));
            String deploymentId = string(row.get("deploymentId"));

            String packageName = projectId + " / " + envName + " (" + envType + ")";
            String componentAlias = alias("component", componentId);
            String deploymentAlias = alias("deployment", deploymentId);

            model.addNode(componentAlias, componentName + "\\n(" + componentId + ")", "Component");
            model.addNode(deploymentAlias, deploymentId, "Deployment");
            model.addPackageMember(packageName, componentAlias);
            model.addPackageMember(packageName, deploymentAlias);
            model.addEdge(componentAlias, deploymentAlias, "HAS_DEPLOYMENT", false);
        }
    }

    private void projectDeploymentTargets(Transaction tx, DiagramModel model) {
        Result toNode = tx.execute(
                "MATCH (d:Deployment)-[:DEPLOYED_TO]->(n:Node) RETURN d.deploymentId AS deploymentId, n.nodeId AS nodeId, n.hostname AS hostname"
        );
        while (toNode.hasNext()) {
            Map<String, Object> row = toNode.next();
            String deploymentAlias = alias("deployment", string(row.get("deploymentId")));
            String nodeAlias = alias("node", string(row.get("nodeId")));
            model.addNode(nodeAlias, string(row.get("hostname")) + "\\n(" + string(row.get("nodeId")) + ")", "Node");
            model.addEdge(deploymentAlias, nodeAlias, "DEPLOYED_TO", false);
        }

        Result toGrid = tx.execute(
                "MATCH (d:Deployment)-[:DEPLOYED_TO_CLUSTER]->(c:Cluster) RETURN d.deploymentId AS deploymentId, c.clusterId AS clusterId, c.clusterName AS clusterName"
        );
        while (toGrid.hasNext()) {
            Map<String, Object> row = toGrid.next();
            String deploymentAlias = alias("deployment", string(row.get("deploymentId")));
            String clusterAlias = alias("cluster", string(row.get("clusterId")));
            model.addNode(clusterAlias, string(row.get("clusterName")) + "\\n(" + string(row.get("clusterId")) + ")", "Cluster");
            model.addEdge(deploymentAlias, clusterAlias, "DEPLOYED_TO_CLUSTER", false);
        }

        Result toWorkload = tx.execute(
                "MATCH (d:Deployment)-[:DEPLOYED_TO_WORKLOAD]->(w:K8sWorkload) " +
                        "MATCH (ns:K8sNamespace)-[:HAS_WORKLOAD]->(w) " +
                        "RETURN d.deploymentId AS deploymentId, w.workloadId AS workloadId, w.name AS workloadName, w.kind AS kind, ns.name AS namespace"
        );
        while (toWorkload.hasNext()) {
            Map<String, Object> row = toWorkload.next();
            String deploymentAlias = alias("deployment", string(row.get("deploymentId")));
            String workloadAlias = alias("workload", string(row.get("workloadId")));
            String label = string(row.get("namespace")) + "/" + string(row.get("workloadName")) + "\\n(" + string(row.get("kind")) + ")";
            model.addNode(workloadAlias, label, "K8sWorkload");
            model.addEdge(deploymentAlias, workloadAlias, "DEPLOYED_TO_WORKLOAD", false);
        }
    }

    private void projectStorage(Transaction tx, DiagramModel model) {
        Result nodeHostedVolumes = tx.execute(
                "MATCH (n:Node)-[:HOSTS_VOLUME]->(v:Volume) " +
                        "RETURN n.nodeId AS nodeId, n.hostname AS hostname, v.volumeId AS volumeId, v.name AS volumeName"
        );
        while (nodeHostedVolumes.hasNext()) {
            Map<String, Object> row = nodeHostedVolumes.next();
            String nodeAlias = alias("node", string(row.get("nodeId")));
            String volumeAlias = alias("volume", string(row.get("volumeId")));
            model.addNode(nodeAlias, string(row.get("hostname")) + "\\n(" + string(row.get("nodeId")) + ")", "Node");
            model.addNode(volumeAlias, string(row.get("volumeName")), "Volume");
            model.addEdge(nodeAlias, volumeAlias, "HOSTS_VOLUME", false);
        }

        Result nodeMounts = tx.execute(
                "MATCH (f:Filer)-[:HOSTS_VOLUME]->(v:Volume)<-[m:MOUNTS_VOLUME]-(n:Node) " +
                        "RETURN f.filerId AS filerId, f.name AS filerName, v.volumeId AS volumeId, v.name AS volumeName, n.nodeId AS nodeId, n.hostname AS hostname"
        );
        while (nodeMounts.hasNext()) {
            Map<String, Object> row = nodeMounts.next();
            String filerAlias = alias("filer", string(row.get("filerId")));
            String volumeAlias = alias("volume", string(row.get("volumeId")));
            String nodeAlias = alias("node", string(row.get("nodeId")));
            model.addNode(filerAlias, string(row.get("filerName")), "Filer");
            model.addNode(volumeAlias, string(row.get("volumeName")), "Volume");
            model.addNode(nodeAlias, string(row.get("hostname")) + "\\n(" + string(row.get("nodeId")) + ")", "Node");
            model.addEdge(filerAlias, volumeAlias, "HOSTS_VOLUME", false);
            model.addEdge(nodeAlias, volumeAlias, "MOUNTS_VOLUME", false);
        }

        Result clusterMounts = tx.execute(
                "MATCH (f:Filer)-[:HOSTS_VOLUME]->(v:Volume)<-[m:MOUNTS_VOLUME]-(c:Cluster) " +
                        "RETURN f.filerId AS filerId, f.name AS filerName, v.volumeId AS volumeId, v.name AS volumeName, c.clusterId AS clusterId, c.clusterName AS clusterName"
        );
        while (clusterMounts.hasNext()) {
            Map<String, Object> row = clusterMounts.next();
            String filerAlias = alias("filer", string(row.get("filerId")));
            String volumeAlias = alias("volume", string(row.get("volumeId")));
            String clusterAlias = alias("cluster", string(row.get("clusterId")));
            model.addNode(filerAlias, string(row.get("filerName")), "Filer");
            model.addNode(volumeAlias, string(row.get("volumeName")), "Volume");
            model.addNode(clusterAlias, string(row.get("clusterName")) + "\\n(" + string(row.get("clusterId")) + ")", "Cluster");
            model.addEdge(filerAlias, volumeAlias, "HOSTS_VOLUME", false);
            model.addEdge(clusterAlias, volumeAlias, "MOUNTS_VOLUME", false);
        }
    }

    private void projectNodeHosting(Transaction tx, DiagramModel model) {
        Result nodeHosting = tx.execute(
                "MATCH (vm:Node)-[:HOSTED_BY]->(hv:Node) " +
                        "RETURN vm.nodeId AS vmNodeId, vm.hostname AS vmHostname, hv.nodeId AS hostNodeId, hv.hostname AS hostHostname"
        );
        while (nodeHosting.hasNext()) {
            Map<String, Object> row = nodeHosting.next();
            String vmAlias = alias("node", string(row.get("vmNodeId")));
            String hostAlias = alias("node", string(row.get("hostNodeId")));
            model.addNode(vmAlias, string(row.get("vmHostname")) + "\\n(" + string(row.get("vmNodeId")) + ")", "Node");
            model.addNode(hostAlias, string(row.get("hostHostname")) + "\\n(" + string(row.get("hostNodeId")) + ")", "Node");
            model.addEdge(vmAlias, hostAlias, "HOSTED_BY", false);
        }
    }

    private void projectNetworking(Transaction tx, DiagramModel model) {
        Result nodeSubnet = tx.execute(
                "MATCH (n:Node)-[:CONNECTED_TO_SUBNET]->(s:Subnet)<-[:HAS_SUBNET]-(net:Network) " +
                        "RETURN n.nodeId AS nodeId, n.hostname AS hostname, s.subnetId AS subnetId, s.name AS subnetName, s.cidr AS cidr, s.vlan AS vlan, net.networkId AS networkId"
        );
        while (nodeSubnet.hasNext()) {
            Map<String, Object> row = nodeSubnet.next();
            String nodeAlias = alias("node", string(row.get("nodeId")));
            String subnetAlias = alias("subnet", string(row.get("subnetId")));
            String networkAlias = alias("network", string(row.get("networkId")));
            model.addNode(nodeAlias, string(row.get("hostname")) + "\\n(" + string(row.get("nodeId")) + ")", "Node");
            model.addNode(subnetAlias, subnetLabel(row), "Subnet");
            model.addNode(networkAlias, string(row.get("networkId")), "Network");
            model.addEdge(networkAlias, subnetAlias, "HAS_SUBNET", false);
            model.addEdge(nodeAlias, subnetAlias, "CONNECTED_TO_SUBNET", true);
        }

        Result clusterSubnet = tx.execute(
                "MATCH (c:Cluster)-[:CONNECTED_TO_SUBNET]->(s:Subnet)<-[:HAS_SUBNET]-(net:Network) " +
                        "RETURN c.clusterId AS clusterId, c.clusterName AS clusterName, s.subnetId AS subnetId, s.name AS subnetName, s.cidr AS cidr, s.vlan AS vlan, net.networkId AS networkId"
        );
        while (clusterSubnet.hasNext()) {
            Map<String, Object> row = clusterSubnet.next();
            String clusterAlias = alias("cluster", string(row.get("clusterId")));
            String subnetAlias = alias("subnet", string(row.get("subnetId")));
            String networkAlias = alias("network", string(row.get("networkId")));
            model.addNode(clusterAlias, string(row.get("clusterName")) + "\\n(" + string(row.get("clusterId")) + ")", "Cluster");
            model.addNode(subnetAlias, subnetLabel(row), "Subnet");
            model.addNode(networkAlias, string(row.get("networkId")), "Network");
            model.addEdge(networkAlias, subnetAlias, "HAS_SUBNET", false);
            model.addEdge(clusterAlias, subnetAlias, "CONNECTED_TO_SUBNET", true);
        }

        Result filerSubnet = tx.execute(
                "MATCH (f:Filer)-[:CONNECTED_TO_SUBNET]->(s:Subnet)<-[:HAS_SUBNET]-(net:Network) " +
                        "RETURN f.filerId AS filerId, f.name AS filerName, s.subnetId AS subnetId, s.name AS subnetName, s.cidr AS cidr, s.vlan AS vlan, net.networkId AS networkId"
        );
        while (filerSubnet.hasNext()) {
            Map<String, Object> row = filerSubnet.next();
            String filerAlias = alias("filer", string(row.get("filerId")));
            String subnetAlias = alias("subnet", string(row.get("subnetId")));
            String networkAlias = alias("network", string(row.get("networkId")));
            model.addNode(filerAlias, string(row.get("filerName")) + "\\n(" + string(row.get("filerId")) + ")", "Filer");
            model.addNode(subnetAlias, subnetLabel(row), "Subnet");
            model.addNode(networkAlias, string(row.get("networkId")), "Network");
            model.addEdge(networkAlias, subnetAlias, "HAS_SUBNET", false);
            model.addEdge(filerAlias, subnetAlias, "CONNECTED_TO_SUBNET", true);
        }
    }

    private String subnetLabel(Map<String, Object> row) {
        return string(row.get("subnetName")) + " | " + string(row.get("cidr")) + " | VLAN " + string(row.get("vlan"));
    }

    private String string(Object value) {
        return value == null ? "" : value.toString();
    }

    private String alias(String prefix, String value) {
        return prefix + "_" + value.replace('-', '_').replace(':', '_').replace('.', '_').replace('/', '_');
    }
}

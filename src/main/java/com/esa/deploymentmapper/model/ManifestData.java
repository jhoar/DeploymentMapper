package com.esa.deploymentmapper.model;

import java.util.ArrayList;
import java.util.List;

public final class ManifestData {
    private ManifestInfo manifest;
    private final List<Organization> organizations = new ArrayList<>();
    private final List<Project> projects = new ArrayList<>();
    private final List<Application> applications = new ArrayList<>();
    private final List<Component> components = new ArrayList<>();
    private final List<Environment> environments = new ArrayList<>();
    private final List<Node> nodes = new ArrayList<>();
    private final List<NodeRoles> nodeRoles = new ArrayList<>();
    private final List<Cluster> clusters = new ArrayList<>();
    private final List<ClusterRoles> clusterRoles = new ArrayList<>();
    private final List<GridMembers> gridMembers = new ArrayList<>();
    private final List<ClusterEndpoints> clusterEndpoints = new ArrayList<>();
    private final List<K8sNamespace> k8sNamespaces = new ArrayList<>();
    private final List<K8sWorkload> k8sWorkloads = new ArrayList<>();
    private final List<K8sService> k8sServices = new ArrayList<>();
    private final List<K8sPods> k8sPods = new ArrayList<>();
    private final List<Filer> filers = new ArrayList<>();
    private final List<FilerRoles> filerRoles = new ArrayList<>();
    private final List<Volume> volumes = new ArrayList<>();
    private final List<Mount> mounts = new ArrayList<>();
    private final List<Network> networks = new ArrayList<>();
    private final List<Subnet> subnets = new ArrayList<>();
    private final List<SubnetConnection> subnetConnections = new ArrayList<>();
    private final List<Deployment> deployments = new ArrayList<>();

    public ManifestInfo manifest() {
        return manifest;
    }

    public void setManifest(ManifestInfo manifest) {
        this.manifest = manifest;
    }

    public List<Organization> organizations() { return organizations; }
    public List<Project> projects() { return projects; }
    public List<Application> applications() { return applications; }
    public List<Component> components() { return components; }
    public List<Environment> environments() { return environments; }
    public List<Node> nodes() { return nodes; }
    public List<NodeRoles> nodeRoles() { return nodeRoles; }
    public List<Cluster> clusters() { return clusters; }
    public List<ClusterRoles> clusterRoles() { return clusterRoles; }
    public List<GridMembers> gridMembers() { return gridMembers; }
    public List<ClusterEndpoints> clusterEndpoints() { return clusterEndpoints; }
    public List<K8sNamespace> k8sNamespaces() { return k8sNamespaces; }
    public List<K8sWorkload> k8sWorkloads() { return k8sWorkloads; }
    public List<K8sService> k8sServices() { return k8sServices; }
    public List<K8sPods> k8sPods() { return k8sPods; }
    public List<Filer> filers() { return filers; }
    public List<FilerRoles> filerRoles() { return filerRoles; }
    public List<Volume> volumes() { return volumes; }
    public List<Mount> mounts() { return mounts; }
    public List<Network> networks() { return networks; }
    public List<Subnet> subnets() { return subnets; }
    public List<SubnetConnection> subnetConnections() { return subnetConnections; }
    public List<Deployment> deployments() { return deployments; }

    public record ManifestInfo(String manifestId, String path) {}
    public record Organization(String orgId, String name) {}
    public record Project(String projectId, String name, String orgId) {}
    public record Application(String appId, String name, String configurationId, String version, String projectId) {}
    public record Component(String componentId, String name, String version, String appId) {}
    public record Environment(String envId, String projectId, String name, String type) {}
    public record Node(String nodeId, String hostname, String ipAddress, String type) {}
    public record NodeRoles(String nodeId, List<String> roles) {}
    public record Cluster(String clusterId, String clusterName, String type) {}
    public record ClusterRoles(String clusterId, List<String> roles) {}
    public record GridMembers(String clusterId, List<String> managers, List<String> workers) {}
    public record ClusterEndpoints(String clusterId, List<String> endpointNodeIds) {}
    public record K8sNamespace(String clusterId, String namespaceName) {}
    public record K8sWorkload(String clusterId, String namespaceName, String kind, String workloadName) {}
    public record K8sWorkloadRef(String clusterId, String namespaceName, String kind, String workloadName) {}
    public record K8sService(String clusterId, String namespaceName, String serviceName, String type, K8sWorkloadRef routesToWorkload) {}
    public record K8sPods(String clusterId, String namespaceName, List<String> podNames) {}
    public record Filer(String filerId, String name, String ipAddress, String type) {}
    public record FilerRoles(String filerId, List<String> roles) {}
    public record Volume(String volumeId, String name, String protocol, String filerId) {}
    public record Mount(String volumeId, String nodeId, String clusterId, String mountPath, String accessMode, String exportOrShareName, String protocolDetails) {}
    public record Network(String networkId, String name) {}
    public record Subnet(String subnetId, String networkId, String name, String cidr, String vlan) {}
    public record SubnetConnection(String entityType, String entityId, String subnetId) {}
    public record DeploymentTarget(List<String> nodes, List<String> gridClusters, List<K8sWorkloadRef> k8sWorkloads) {}
    public record Deployment(String deploymentId, String componentId, String projectId, String envId, DeploymentTarget targets) {}
}

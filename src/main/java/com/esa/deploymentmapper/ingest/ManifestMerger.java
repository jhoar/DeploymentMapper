package com.esa.deploymentmapper.ingest;

import com.esa.deploymentmapper.error.ValidationException;
import com.esa.deploymentmapper.model.ManifestData;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class ManifestMerger {

    public ManifestData merge(List<ManifestData> manifests) {
        ManifestData merged = new ManifestData();
        List<String> errors = new ArrayList<>();

        Map<String, String> nodeIdToHostname = new HashMap<>();
        Map<String, String> hostnameToNodeId = new HashMap<>();
        Map<String, ManifestData.Organization> organizations = new LinkedHashMap<>();
        Map<String, ManifestData.Project> projects = new LinkedHashMap<>();
        Map<String, ManifestData.Application> applications = new LinkedHashMap<>();
        Map<String, ManifestData.Component> components = new LinkedHashMap<>();
        Map<String, ManifestData.Environment> environments = new LinkedHashMap<>();
        Map<String, ManifestData.Node> nodes = new LinkedHashMap<>();
        Map<String, ManifestData.Cluster> clusters = new LinkedHashMap<>();
        Map<String, ManifestData.Filer> filers = new LinkedHashMap<>();
        Map<String, ManifestData.Volume> volumes = new LinkedHashMap<>();
        Map<String, ManifestData.Network> networks = new LinkedHashMap<>();
        Map<String, ManifestData.Subnet> subnets = new LinkedHashMap<>();
        Map<String, ManifestData.Deployment> deployments = new LinkedHashMap<>();

        Map<String, ManifestData.NodeRoles> nodeRoles = new LinkedHashMap<>();
        Map<String, ManifestData.ClusterRoles> clusterRoles = new LinkedHashMap<>();
        Map<String, ManifestData.FilerRoles> filerRoles = new LinkedHashMap<>();

        Set<String> seenMountNodeVolume = new java.util.HashSet<>();
        Set<String> seenMountClusterVolume = new java.util.HashSet<>();
        Map<String, String> subnetCidrs = new HashMap<>();
        Map<String, String> subnetVlanKeys = new HashMap<>();
        Map<String, String> projectTypeKeys = new HashMap<>();
        Map<String, String> projectNameKeys = new HashMap<>();
        Map<String, String> deploymentKeys = new HashMap<>();

        List<ManifestData.GridMembers> gridMembers = new ArrayList<>();
        List<ManifestData.ClusterEndpoints> clusterEndpoints = new ArrayList<>();
        List<ManifestData.K8sNamespace> namespaces = new ArrayList<>();
        List<ManifestData.K8sWorkload> workloads = new ArrayList<>();
        List<ManifestData.K8sService> services = new ArrayList<>();
        List<ManifestData.K8sPods> pods = new ArrayList<>();
        List<ManifestData.Mount> mounts = new ArrayList<>();
        List<ManifestData.SubnetConnection> subnetConnections = new ArrayList<>();

        for (ManifestData source : manifests) {
            if (merged.manifest() == null && source.manifest() != null) {
                merged.setManifest(source.manifest());
            }
            for (ManifestData.Organization incoming : source.organizations()) {
                organizations.merge(incoming.orgId(), incoming,
                        (existing, add) -> new ManifestData.Organization(existing.orgId(), coalesce(existing.name(), add.name(), "Organization.name", errors)));
            }
            for (ManifestData.Project incoming : source.projects()) {
                projects.merge(incoming.projectId(), incoming,
                        (existing, add) -> new ManifestData.Project(
                                existing.projectId(),
                                coalesce(existing.name(), add.name(), "Project.name", errors),
                                coalesce(existing.orgId(), add.orgId(), "Project.orgId", errors)
                        ));
            }
            for (ManifestData.Application incoming : source.applications()) {
                applications.merge(incoming.appId(), incoming,
                        (existing, add) -> new ManifestData.Application(
                                existing.appId(),
                                coalesce(existing.name(), add.name(), "Application.name", errors),
                                coalesce(existing.configurationId(), add.configurationId(), "Application.configurationId", errors),
                                coalesce(existing.version(), add.version(), "Application.version", errors),
                                coalesce(existing.projectId(), add.projectId(), "Application.projectId", errors)
                        ));
            }
            for (ManifestData.Component incoming : source.components()) {
                components.merge(incoming.componentId(), incoming,
                        (existing, add) -> new ManifestData.Component(
                                existing.componentId(),
                                coalesce(existing.name(), add.name(), "Component.name", errors),
                                coalesce(existing.version(), add.version(), "Component.version", errors),
                                coalesce(existing.appId(), add.appId(), "Component.appId", errors)
                        ));
            }
            for (ManifestData.Environment incoming : source.environments()) {
                String envKey = incoming.projectId() + ":" + incoming.envId();
                ManifestData.Environment normalizedIncoming = new ManifestData.Environment(
                        incoming.envId(), incoming.projectId(), incoming.name(), incoming.type());
                environments.merge(envKey, normalizedIncoming,
                        (existing, add) -> new ManifestData.Environment(
                                existing.envId(),
                                existing.projectId(),
                                coalesce(existing.name(), add.name(), "Environment.name", errors),
                                coalesce(existing.type(), add.type(), "Environment.type", errors)
                        ));
                String projectTypeKey = incoming.projectId() + ":" + incoming.type();
                String envKeyForType = incoming.projectId() + ":" + incoming.envId();
                String existingTypeEnv = projectTypeKeys.putIfAbsent(projectTypeKey, envKeyForType);
                if (existingTypeEnv != null && !existingTypeEnv.equals(envKeyForType)) {
                    errors.add("Duplicate project environment type key: " + projectTypeKey);
                }
                String projectNameKey = incoming.projectId() + ":" + incoming.name();
                String existingNameEnv = projectNameKeys.putIfAbsent(projectNameKey, envKeyForType);
                if (existingNameEnv != null && !existingNameEnv.equals(envKeyForType)) {
                    errors.add("Duplicate project environment name key: " + projectNameKey);
                }
            }

            for (ManifestData.Node incoming : source.nodes()) {
                String existingHostnameForNode = nodeIdToHostname.putIfAbsent(incoming.nodeId(), incoming.hostname());
                if (existingHostnameForNode != null && !existingHostnameForNode.equals(incoming.hostname())) {
                    errors.add("Node identity conflict for nodeId " + incoming.nodeId() + ": hostname " + existingHostnameForNode + " vs " + incoming.hostname());
                }
                String existingNodeForHostname = hostnameToNodeId.putIfAbsent(incoming.hostname(), incoming.nodeId());
                if (existingNodeForHostname != null && !existingNodeForHostname.equals(incoming.nodeId())) {
                    errors.add("Node identity conflict for hostname " + incoming.hostname() + ": nodeId " + existingNodeForHostname + " vs " + incoming.nodeId());
                }
                nodes.merge(incoming.nodeId(), incoming,
                        (existing, add) -> new ManifestData.Node(
                                existing.nodeId(),
                                coalesce(existing.hostname(), add.hostname(), "Node.hostname", errors),
                                coalesce(existing.ipAddress(), add.ipAddress(), "Node.ipAddress", errors),
                                coalesce(existing.type(), add.type(), "Node.type", errors),
                                coalesce(existing.hostedByNodeId(), add.hostedByNodeId(), "Node.hostedByNodeId", errors)
                        ));
            }

            mergeRoleLists(source.nodeRoles(), nodeRoles, ManifestData.NodeRoles::nodeId,
                    (id, roles) -> new ManifestData.NodeRoles(id, roles), errors, "NodeRoles");

            for (ManifestData.Cluster incoming : source.clusters()) {
                clusters.merge(incoming.clusterId(), incoming,
                        (existing, add) -> new ManifestData.Cluster(
                                existing.clusterId(),
                                coalesce(existing.clusterName(), add.clusterName(), "Cluster.clusterName", errors),
                                coalesce(existing.type(), add.type(), "Cluster.type", errors)
                        ));
            }

            mergeRoleLists(source.clusterRoles(), clusterRoles, ManifestData.ClusterRoles::clusterId,
                    (id, roles) -> new ManifestData.ClusterRoles(id, roles), errors, "ClusterRoles");
            mergeRoleLists(source.filerRoles(), filerRoles, ManifestData.FilerRoles::filerId,
                    (id, roles) -> new ManifestData.FilerRoles(id, roles), errors, "FilerRoles");

            for (ManifestData.Filer incoming : source.filers()) {
                filers.merge(incoming.filerId(), incoming,
                        (existing, add) -> new ManifestData.Filer(
                                existing.filerId(),
                                coalesce(existing.name(), add.name(), "Filer.name", errors),
                                coalesce(existing.ipAddress(), add.ipAddress(), "Filer.ipAddress", errors),
                                coalesce(existing.type(), add.type(), "Filer.type", errors)
                        ));
            }
            for (ManifestData.Volume incoming : source.volumes()) {
                volumes.merge(incoming.volumeId(), incoming,
                        (existing, add) -> new ManifestData.Volume(
                                existing.volumeId(),
                                coalesce(existing.name(), add.name(), "Volume.name", errors),
                                coalesce(existing.protocol(), add.protocol(), "Volume.protocol", errors),
                                coalesce(existing.filerId(), add.filerId(), "Volume.filerId", errors),
                                coalesce(existing.hostedByNodeId(), add.hostedByNodeId(), "Volume.hostedByNodeId", errors)
                        ));
            }
            for (ManifestData.Network incoming : source.networks()) {
                networks.merge(incoming.networkId(), incoming,
                        (existing, add) -> new ManifestData.Network(
                                existing.networkId(),
                                coalesce(existing.name(), add.name(), "Network.name", errors)
                        ));
            }
            for (ManifestData.Subnet incoming : source.subnets()) {
                subnets.merge(incoming.subnetId(), incoming,
                        (existing, add) -> new ManifestData.Subnet(
                                existing.subnetId(),
                                coalesce(existing.networkId(), add.networkId(), "Subnet.networkId", errors),
                                coalesce(existing.name(), add.name(), "Subnet.name", errors),
                                coalesce(existing.cidr(), add.cidr(), "Subnet.cidr", errors),
                                coalesce(existing.vlan(), add.vlan(), "Subnet.vlan", errors)
                        ));
                String existingSubnetForCidr = subnetCidrs.putIfAbsent(incoming.cidr(), incoming.subnetId());
                if (existingSubnetForCidr != null && !existingSubnetForCidr.equals(incoming.subnetId())) {
                    errors.add("Subnet CIDR conflict (must be unique): " + incoming.cidr());
                }
                String vlanKey = incoming.networkId() + ":" + incoming.vlan();
                String existingSubnetForVlan = subnetVlanKeys.putIfAbsent(vlanKey, incoming.subnetId());
                if (existingSubnetForVlan != null && !existingSubnetForVlan.equals(incoming.subnetId())) {
                    errors.add("Subnet VLAN conflict (must be unique per network): " + vlanKey);
                }
            }
            for (ManifestData.Deployment incoming : source.deployments()) {
                deployments.merge(incoming.deploymentId(), incoming,
                        (existing, add) -> {
                            if (!Objects.equals(existing.componentId(), add.componentId())
                                    || !Objects.equals(existing.projectId(), add.projectId())
                                    || !Objects.equals(existing.envId(), add.envId())) {
                                errors.add("Deployment conflict for " + existing.deploymentId());
                            }
                            return mergeDeploymentTargets(existing, add, errors);
                        });
                String deploymentKey = incoming.componentId() + ":" + incoming.projectId() + ":" + incoming.envId();
                String existingDeploymentForKey = deploymentKeys.putIfAbsent(deploymentKey, incoming.deploymentId());
                if (existingDeploymentForKey != null && !existingDeploymentForKey.equals(incoming.deploymentId())) {
                    errors.add("Deployment key conflict (one deployment allowed per component/environment): " + deploymentKey);
                }
            }

            gridMembers.addAll(source.gridMembers());
            clusterEndpoints.addAll(source.clusterEndpoints());
            namespaces.addAll(source.k8sNamespaces());
            workloads.addAll(source.k8sWorkloads());
            services.addAll(source.k8sServices());
            pods.addAll(source.k8sPods());
            subnetConnections.addAll(source.subnetConnections());

            for (ManifestData.Mount mount : source.mounts()) {
                if (!isBlank(mount.nodeId())) {
                    String key = mount.nodeId() + ":" + mount.volumeId();
                    if (!seenMountNodeVolume.add(key)) {
                        errors.add("Duplicate node mount detected for key " + key);
                    }
                }
                if (!isBlank(mount.clusterId())) {
                    String key = mount.clusterId() + ":" + mount.volumeId();
                    if (!seenMountClusterVolume.add(key)) {
                        errors.add("Duplicate cluster mount detected for key " + key);
                    }
                }
                mounts.add(mount);
            }
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }

        merged.organizations().addAll(organizations.values());
        merged.projects().addAll(projects.values());
        merged.applications().addAll(applications.values());
        merged.components().addAll(components.values());
        merged.environments().addAll(environments.values());
        merged.nodes().addAll(nodes.values());
        merged.nodeRoles().addAll(nodeRoles.values());
        merged.clusters().addAll(clusters.values());
        merged.clusterRoles().addAll(clusterRoles.values());
        merged.gridMembers().addAll(gridMembers);
        merged.clusterEndpoints().addAll(clusterEndpoints);
        merged.k8sNamespaces().addAll(namespaces);
        merged.k8sWorkloads().addAll(workloads);
        merged.k8sServices().addAll(services);
        merged.k8sPods().addAll(pods);
        merged.filers().addAll(filers.values());
        merged.filerRoles().addAll(filerRoles.values());
        merged.volumes().addAll(volumes.values());
        merged.mounts().addAll(mounts);
        merged.networks().addAll(networks.values());
        merged.subnets().addAll(subnets.values());
        merged.subnetConnections().addAll(subnetConnections);
        merged.deployments().addAll(deployments.values());
        return merged;
    }

    private ManifestData.Deployment mergeDeploymentTargets(ManifestData.Deployment existing,
                                                           ManifestData.Deployment incoming,
                                                           List<String> errors) {
        List<String> nodes = union(existing.targets().nodes(), incoming.targets().nodes());
        List<String> grid = union(existing.targets().gridClusters(), incoming.targets().gridClusters());
        List<ManifestData.K8sWorkloadRef> k8s = union(existing.targets().k8sWorkloads(), incoming.targets().k8sWorkloads());
        return new ManifestData.Deployment(existing.deploymentId(), existing.componentId(), existing.projectId(), existing.envId(),
                new ManifestData.DeploymentTarget(nodes, grid, k8s));
    }

    private <T> List<T> union(List<T> a, List<T> b) {
        List<T> out = new ArrayList<>(a);
        for (T value : b) {
            if (!out.contains(value)) {
                out.add(value);
            }
        }
        return out;
    }

    private <T> void mergeRoleLists(List<T> source,
                                    Map<String, T> target,
                                    java.util.function.Function<T, String> idExtractor,
                                    java.util.function.BiFunction<String, List<String>, T> constructor,
                                    List<String> errors,
                                    String context) {
        for (T incoming : source) {
            String id = idExtractor.apply(incoming);
            target.merge(id, incoming, (existing, add) -> {
                List<String> existingRoles;
                List<String> addRoles;
                if (existing instanceof ManifestData.NodeRoles exNode && add instanceof ManifestData.NodeRoles addNode) {
                    existingRoles = exNode.roles();
                    addRoles = addNode.roles();
                } else if (existing instanceof ManifestData.ClusterRoles exCluster && add instanceof ManifestData.ClusterRoles addCluster) {
                    existingRoles = exCluster.roles();
                    addRoles = addCluster.roles();
                } else if (existing instanceof ManifestData.FilerRoles exFiler && add instanceof ManifestData.FilerRoles addFiler) {
                    existingRoles = exFiler.roles();
                    addRoles = addFiler.roles();
                } else {
                    errors.add("Unexpected role merge type for context " + context);
                    return existing;
                }
                List<String> mergedRoles = union(existingRoles, addRoles);
                return constructor.apply(id, mergedRoles);
            });
        }
    }

    private String coalesce(String existing, String incoming, String context, List<String> errors) {
        if (isBlank(existing)) {
            return incoming;
        }
        if (isBlank(incoming)) {
            return existing;
        }
        if (!existing.equals(incoming)) {
            errors.add("Conflict in " + context + ": '" + existing + "' vs '" + incoming + "'");
        }
        return existing;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}

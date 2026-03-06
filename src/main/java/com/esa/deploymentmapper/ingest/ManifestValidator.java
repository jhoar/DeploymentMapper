package com.esa.deploymentmapper.ingest;

import com.esa.deploymentmapper.error.ValidationException;
import com.esa.deploymentmapper.model.ManifestData;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ManifestValidator {
    public void validateSingle(ManifestData data, String sourceLabel) {
        List<String> errors = new ArrayList<>();

        if (data.manifest() == null) {
            errors.add(sourceLabel + ": missing Manifest section");
        } else {
            required(errors, sourceLabel, "Manifest.manifestId", data.manifest().manifestId());
            required(errors, sourceLabel, "Manifest.path", data.manifest().path());
        }

        validateRequiredIds(errors, sourceLabel, "Organizations", data.organizations().stream().map(ManifestData.Organization::orgId).toList());
        validateRequiredIds(errors, sourceLabel, "Projects", data.projects().stream().map(ManifestData.Project::projectId).toList());
        validateRequiredIds(errors, sourceLabel, "Applications", data.applications().stream().map(ManifestData.Application::appId).toList());
        validateRequiredIds(errors, sourceLabel, "Components", data.components().stream().map(ManifestData.Component::componentId).toList());
        validateRequiredIds(errors, sourceLabel, "Environments", data.environments().stream().map(ManifestData.Environment::envId).toList());
        validateRequiredIds(errors, sourceLabel, "Nodes", data.nodes().stream().map(ManifestData.Node::nodeId).toList());
        validateRequiredIds(errors, sourceLabel, "Clusters", data.clusters().stream().map(ManifestData.Cluster::clusterId).toList());
        validateRequiredIds(errors, sourceLabel, "Filers", data.filers().stream().map(ManifestData.Filer::filerId).toList());
        validateRequiredIds(errors, sourceLabel, "Volumes", data.volumes().stream().map(ManifestData.Volume::volumeId).toList());
        validateRequiredIds(errors, sourceLabel, "Networks", data.networks().stream().map(ManifestData.Network::networkId).toList());
        validateRequiredIds(errors, sourceLabel, "Subnets", data.subnets().stream().map(ManifestData.Subnet::subnetId).toList());
        validateRequiredIds(errors, sourceLabel, "Deployments", data.deployments().stream().map(ManifestData.Deployment::deploymentId).toList());

        for (ManifestData.Environment environment : data.environments()) {
            required(errors, sourceLabel, "Environments.projectId", environment.projectId());
            required(errors, sourceLabel, "Environments.name", environment.name());
            required(errors, sourceLabel, "Environments.type", environment.type());
            validateEnum(errors, sourceLabel, "Environments.type", environment.type(), Set.of("Development", "Test", "Staging", "Production"));
        }

        for (ManifestData.Node node : data.nodes()) {
            required(errors, sourceLabel, "Nodes.hostname", node.hostname());
            required(errors, sourceLabel, "Nodes.type", node.type());
            validateEnum(errors, sourceLabel, "Nodes.type", node.type(), Set.of("Physical", "VM"));
            if (!isBlank(node.hostedByNodeId()) && !"VM".equals(node.type())) {
                errors.add(sourceLabel + ": Nodes.hostedByNodeId can only be set for VM nodes: " + node.nodeId());
            }
            if (!isBlank(node.hostedByNodeId()) && node.nodeId().equals(node.hostedByNodeId())) {
                errors.add(sourceLabel + ": node cannot host itself: " + node.nodeId());
            }
        }

        for (ManifestData.Cluster cluster : data.clusters()) {
            required(errors, sourceLabel, "Clusters.clusterName", cluster.clusterName());
            validateEnum(errors, sourceLabel, "Clusters.type", cluster.type(), Set.of("Grid", "Kubernetes"));
        }

        for (ManifestData.Filer filer : data.filers()) {
            validateEnum(errors, sourceLabel, "Filers.type", filer.type(), Set.of("SAN", "NAS"));
        }

        for (ManifestData.Volume volume : data.volumes()) {
            required(errors, sourceLabel, "Volumes.filerId", volume.filerId());
            validateEnum(errors, sourceLabel, "Volumes.protocol", volume.protocol(), Set.of("NFS", "SMB", "iSCSI", "S3"));
        }

        for (ManifestData.Mount mount : data.mounts()) {
            required(errors, sourceLabel, "Mounts.volumeId", mount.volumeId());
            required(errors, sourceLabel, "Mounts.mountPath", mount.mountPath());
            validateEnum(errors, sourceLabel, "Mounts.accessMode", mount.accessMode(), Set.of("ro", "rw"));
            if (isBlank(mount.nodeId()) && isBlank(mount.clusterId())) {
                errors.add(sourceLabel + ": Mount must define either nodeId or clusterId");
            }
            if (!isBlank(mount.nodeId()) && !isBlank(mount.clusterId())) {
                errors.add(sourceLabel + ": Mount cannot define both nodeId and clusterId");
            }
        }

        for (ManifestData.Deployment deployment : data.deployments()) {
            required(errors, sourceLabel, "Deployments.componentId", deployment.componentId());
            required(errors, sourceLabel, "Deployments.projectId", deployment.projectId());
            required(errors, sourceLabel, "Deployments.envId", deployment.envId());
            if (deployment.targets() == null ||
                    (deployment.targets().nodes().isEmpty()
                    && deployment.targets().gridClusters().isEmpty()
                    && deployment.targets().k8sWorkloads().isEmpty())) {
                errors.add(sourceLabel + ": deployment " + deployment.deploymentId() + " must have at least one target");
            }
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
    }

    public void validateMerged(ManifestData data) {
        List<String> errors = new ArrayList<>();

        Set<String> orgIds = new HashSet<>(data.organizations().stream().map(ManifestData.Organization::orgId).toList());
        Set<String> projectIds = new HashSet<>(data.projects().stream().map(ManifestData.Project::projectId).toList());
        Set<String> appIds = new HashSet<>(data.applications().stream().map(ManifestData.Application::appId).toList());
        Set<String> componentIds = new HashSet<>(data.components().stream().map(ManifestData.Component::componentId).toList());
        Set<String> nodeIds = new HashSet<>(data.nodes().stream().map(ManifestData.Node::nodeId).toList());
        Map<String, ManifestData.Node> nodesById = new HashMap<>();
        for (ManifestData.Node node : data.nodes()) {
            nodesById.put(node.nodeId(), node);
        }
        Set<String> clusterIds = new HashSet<>(data.clusters().stream().map(ManifestData.Cluster::clusterId).toList());
        Set<String> filerIds = new HashSet<>(data.filers().stream().map(ManifestData.Filer::filerId).toList());
        Set<String> volumeIds = new HashSet<>(data.volumes().stream().map(ManifestData.Volume::volumeId).toList());
        Set<String> subnetIds = new HashSet<>(data.subnets().stream().map(ManifestData.Subnet::subnetId).toList());
        Map<String, Set<String>> nodeRolesByNodeId = new HashMap<>();
        for (ManifestData.NodeRoles role : data.nodeRoles()) {
            nodeRolesByNodeId.computeIfAbsent(role.nodeId(), ignored -> new HashSet<>()).addAll(role.roles());
        }

        Set<String> projectEnvKeys = new HashSet<>();
        for (ManifestData.Environment env : data.environments()) {
            projectEnvKeys.add(env.projectId() + ":" + env.envId());
        }

        for (ManifestData.Project project : data.projects()) {
            if (!orgIds.contains(project.orgId())) {
                errors.add("Project " + project.projectId() + " references missing orgId " + project.orgId());
            }
        }

        for (ManifestData.Application application : data.applications()) {
            if (!projectIds.contains(application.projectId())) {
                errors.add("Application " + application.appId() + " references missing projectId " + application.projectId());
            }
        }

        for (ManifestData.Component component : data.components()) {
            if (!appIds.contains(component.appId())) {
                errors.add("Component " + component.componentId() + " references missing appId " + component.appId());
            }
        }

        for (ManifestData.NodeRoles role : data.nodeRoles()) {
            if (!nodeIds.contains(role.nodeId())) {
                errors.add("NodeRoles references missing nodeId " + role.nodeId());
            }
        }

        for (ManifestData.Node node : data.nodes()) {
            if (isBlank(node.hostedByNodeId())) {
                continue;
            }
            if (!nodeIds.contains(node.hostedByNodeId())) {
                errors.add("Node " + node.nodeId() + " references missing hostedByNodeId " + node.hostedByNodeId());
                continue;
            }
            ManifestData.Node hostNode = nodesById.get(node.hostedByNodeId());
            if (hostNode == null) {
                errors.add("Node " + node.nodeId() + " references missing hostedByNodeId " + node.hostedByNodeId());
                continue;
            }
            if (!"Physical".equals(hostNode.type())) {
                errors.add("Node " + node.nodeId() + " host node must be Physical: " + hostNode.nodeId());
            }
            Set<String> hostRoles = nodeRolesByNodeId.getOrDefault(hostNode.nodeId(), Set.of());
            if (!hostRoles.contains("hypervisor")) {
                errors.add("Node " + node.nodeId() + " host node must have hypervisor role: " + hostNode.nodeId());
            }
        }

        for (ManifestData.ClusterRoles role : data.clusterRoles()) {
            if (!clusterIds.contains(role.clusterId())) {
                errors.add("ClusterRoles references missing clusterId " + role.clusterId());
            }
        }

        for (ManifestData.FilerRoles role : data.filerRoles()) {
            if (!filerIds.contains(role.filerId())) {
                errors.add("FilerRoles references missing filerId " + role.filerId());
            }
        }

        for (ManifestData.GridMembers members : data.gridMembers()) {
            if (!clusterIds.contains(members.clusterId())) {
                errors.add("GridMembers references missing clusterId " + members.clusterId());
            }
            members.managers().forEach(nodeId -> {
                if (!nodeIds.contains(nodeId)) {
                    errors.add("GridMembers manager node missing: " + nodeId);
                }
            });
            members.workers().forEach(nodeId -> {
                if (!nodeIds.contains(nodeId)) {
                    errors.add("GridMembers worker node missing: " + nodeId);
                }
            });
        }

        for (ManifestData.ClusterEndpoints endpoints : data.clusterEndpoints()) {
            if (!clusterIds.contains(endpoints.clusterId())) {
                errors.add("ClusterEndpoints references missing clusterId " + endpoints.clusterId());
            }
            endpoints.endpointNodeIds().forEach(nodeId -> {
                if (!nodeIds.contains(nodeId)) {
                    errors.add("ClusterEndpoints node missing: " + nodeId);
                }
            });
        }

        for (ManifestData.K8sNamespace namespace : data.k8sNamespaces()) {
            if (!clusterIds.contains(namespace.clusterId())) {
                errors.add("K8sNamespace references missing clusterId " + namespace.clusterId());
            }
        }

        Set<String> workloadKeys = new HashSet<>();
        for (ManifestData.K8sWorkload workload : data.k8sWorkloads()) {
            String key = workload.clusterId() + ":" + workload.namespaceName() + ":" + workload.kind() + ":" + workload.workloadName();
            workloadKeys.add(key);
        }

        for (ManifestData.K8sService service : data.k8sServices()) {
            if (service.routesToWorkload() != null) {
                String key = service.routesToWorkload().clusterId() + ":" + service.routesToWorkload().namespaceName() + ":"
                        + service.routesToWorkload().kind() + ":" + service.routesToWorkload().workloadName();
                if (!workloadKeys.contains(key)) {
                    errors.add("K8sService " + service.serviceName() + " routes to missing workload " + key);
                }
            }
        }

        for (ManifestData.Volume volume : data.volumes()) {
            if (!filerIds.contains(volume.filerId())) {
                errors.add("Volume " + volume.volumeId() + " references missing filerId " + volume.filerId());
            }
            if (isBlank(volume.hostedByNodeId())) {
                continue;
            }
            if (!nodeIds.contains(volume.hostedByNodeId())) {
                errors.add("Volume " + volume.volumeId() + " references missing hostedByNodeId " + volume.hostedByNodeId());
                continue;
            }
            ManifestData.Node hostNode = nodesById.get(volume.hostedByNodeId());
            if (hostNode == null) {
                errors.add("Volume " + volume.volumeId() + " references missing hostedByNodeId " + volume.hostedByNodeId());
                continue;
            }
            if (!"Physical".equals(hostNode.type())) {
                errors.add("Volume " + volume.volumeId() + " host node must be Physical: " + hostNode.nodeId());
            }
        }

        for (ManifestData.Mount mount : data.mounts()) {
            if (!volumeIds.contains(mount.volumeId())) {
                errors.add("Mount references missing volumeId " + mount.volumeId());
            }
            if (!isBlank(mount.nodeId()) && !nodeIds.contains(mount.nodeId())) {
                errors.add("Mount references missing nodeId " + mount.nodeId());
            }
            if (!isBlank(mount.clusterId()) && !clusterIds.contains(mount.clusterId())) {
                errors.add("Mount references missing clusterId " + mount.clusterId());
            }
        }

        for (ManifestData.Subnet subnet : data.subnets()) {
            if (isBlank(subnet.networkId())) {
                errors.add("Subnet " + subnet.subnetId() + " has empty networkId");
            }
        }

        for (ManifestData.SubnetConnection connection : data.subnetConnections()) {
            if (!subnetIds.contains(connection.subnetId())) {
                errors.add("SubnetConnection references missing subnetId " + connection.subnetId());
            }
            if (connection.entityType().equals("Node") && !nodeIds.contains(connection.entityId())) {
                errors.add("SubnetConnection references missing node " + connection.entityId());
            }
            if (connection.entityType().equals("Cluster") && !clusterIds.contains(connection.entityId())) {
                errors.add("SubnetConnection references missing cluster " + connection.entityId());
            }
            if (connection.entityType().equals("Filer") && !filerIds.contains(connection.entityId())) {
                errors.add("SubnetConnection references missing filer " + connection.entityId());
            }
        }

        for (ManifestData.Deployment deployment : data.deployments()) {
            if (!componentIds.contains(deployment.componentId())) {
                errors.add("Deployment " + deployment.deploymentId() + " references missing componentId " + deployment.componentId());
            }
            String envKey = deployment.projectId() + ":" + deployment.envId();
            if (!projectEnvKeys.contains(envKey)) {
                errors.add("Deployment " + deployment.deploymentId() + " references missing environment " + envKey);
            }
            deployment.targets().nodes().forEach(nodeId -> {
                if (!nodeIds.contains(nodeId)) {
                    errors.add("Deployment " + deployment.deploymentId() + " references missing node target " + nodeId);
                }
            });
            deployment.targets().gridClusters().forEach(clusterId -> {
                if (!clusterIds.contains(clusterId)) {
                    errors.add("Deployment " + deployment.deploymentId() + " references missing grid cluster target " + clusterId);
                }
            });
            deployment.targets().k8sWorkloads().forEach(ref -> {
                String key = ref.clusterId() + ":" + ref.namespaceName() + ":" + ref.kind() + ":" + ref.workloadName();
                if (!workloadKeys.contains(key)) {
                    errors.add("Deployment " + deployment.deploymentId() + " references missing k8s workload target " + key);
                }
            });
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
    }

    private void required(List<String> errors, String source, String field, String value) {
        if (isBlank(value)) {
            errors.add(source + ": missing required value for " + field);
        }
    }

    private void validateRequiredIds(List<String> errors, String source, String section, List<String> ids) {
        for (String id : ids) {
            if (isBlank(id)) {
                errors.add(source + ": section " + section + " has entry with empty id");
            }
        }
    }

    private void validateEnum(List<String> errors, String source, String field, String value, Set<String> allowed) {
        if (!isBlank(value) && !allowed.contains(value)) {
            errors.add(source + ": invalid value for " + field + ": " + value + "; allowed: " + allowed);
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}

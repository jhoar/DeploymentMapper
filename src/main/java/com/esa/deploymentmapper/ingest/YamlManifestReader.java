package com.esa.deploymentmapper.ingest;

import com.esa.deploymentmapper.error.ManifestParseException;
import com.esa.deploymentmapper.model.ManifestData;
import com.esa.deploymentmapper.util.NormalizationUtil;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class YamlManifestReader {
    public ManifestData read(Path path) {
        try (InputStream inputStream = Files.newInputStream(path)) {
            Yaml yaml = new Yaml();
            Object loaded = yaml.load(inputStream);
            if (!(loaded instanceof Map<?, ?> loadedMap)) {
                throw new ManifestParseException("Root YAML object must be a map in file: " + path);
            }
            Map<String, Object> root = toStringObjectMap(loadedMap);
            ManifestData data = new ManifestData();
            parseManifest(root, data);
            parseOrganizations(root, data);
            parseProjects(root, data);
            parseApplications(root, data);
            parseComponents(root, data);
            parseEnvironments(root, data);
            parseNodes(root, data);
            parseNodeRoles(root, data);
            parseClusters(root, data);
            parseClusterRoles(root, data);
            parseGridMembers(root, data);
            parseClusterEndpoints(root, data);
            parseK8s(root, data);
            parseFilers(root, data);
            parseVolumes(root, data);
            parseMounts(root, data);
            parseNetworks(root, data);
            parseSubnets(root, data);
            parseSubnetConnections(root, data);
            parseDeployments(root, data);
            return data;
        } catch (IOException e) {
            throw new ManifestParseException("Failed to read YAML file: " + path, e);
        } catch (RuntimeException e) {
            if (e instanceof ManifestParseException) {
                throw e;
            }
            throw new ManifestParseException("Failed to parse YAML file: " + path + " due to: " + e.getMessage(), e);
        }
    }

    private void parseManifest(Map<String, Object> root, ManifestData data) {
        Map<String, Object> map = getMap(root, "Manifest");
        if (map == null) {
            return;
        }
        data.setManifest(new ManifestData.ManifestInfo(asString(map.get("manifestId")), asString(map.get("path"))));
    }

    private void parseOrganizations(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Organizations")) {
            data.organizations().add(new ManifestData.Organization(asString(item.get("orgId")), asString(item.get("name"))));
        }
    }

    private void parseProjects(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Projects")) {
            data.projects().add(new ManifestData.Project(
                    asString(item.get("projectId")),
                    asString(item.get("name")),
                    asString(item.get("orgId"))
            ));
        }
    }

    private void parseApplications(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Applications")) {
            data.applications().add(new ManifestData.Application(
                    asString(item.get("appId")),
                    asString(item.get("name")),
                    asString(item.get("configurationId")),
                    asString(item.get("version")),
                    asString(item.get("projectId"))
            ));
        }
    }

    private void parseComponents(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Components")) {
            data.components().add(new ManifestData.Component(
                    asString(item.get("componentId")),
                    asString(item.get("name")),
                    asString(item.get("version")),
                    asString(item.get("appId"))
            ));
        }
    }

    private void parseEnvironments(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Environments")) {
            data.environments().add(new ManifestData.Environment(
                    asString(item.get("envId")),
                    asString(item.get("projectId")),
                    NormalizationUtil.normalize(asString(item.get("name"))),
                    asString(item.get("type"))
            ));
        }
    }

    private void parseNodes(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Nodes")) {
            data.nodes().add(new ManifestData.Node(
                    asString(item.get("nodeId")),
                    asString(item.get("hostname")),
                    asString(item.get("ipAddress")),
                    asString(item.get("type")),
                    asString(item.get("hostedByNodeId"))
            ));
        }
    }

    private void parseNodeRoles(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "NodeRoles")) {
            data.nodeRoles().add(new ManifestData.NodeRoles(
                    asString(item.get("nodeId")),
                    normalizeValues(getStringList(item.get("roles")))
            ));
        }
    }

    private void parseClusters(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Clusters")) {
            data.clusters().add(new ManifestData.Cluster(
                    asString(item.get("clusterId")),
                    asString(item.get("clusterName")),
                    asString(item.get("type"))
            ));
        }
    }

    private void parseClusterRoles(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "ClusterRoles")) {
            data.clusterRoles().add(new ManifestData.ClusterRoles(
                    asString(item.get("clusterId")),
                    normalizeValues(getStringList(item.get("roles")))
            ));
        }
    }

    private void parseGridMembers(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "GridMembers")) {
            data.gridMembers().add(new ManifestData.GridMembers(
                    asString(item.get("clusterId")),
                    getStringList(item.get("managers")),
                    getStringList(item.get("workers"))
            ));
        }
    }

    private void parseClusterEndpoints(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "ClusterEndpoints")) {
            data.clusterEndpoints().add(new ManifestData.ClusterEndpoints(
                    asString(item.get("clusterId")),
                    getStringList(item.get("endpointNodeIds"))
            ));
        }
    }

    private void parseK8s(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "K8sNamespaces")) {
            data.k8sNamespaces().add(new ManifestData.K8sNamespace(
                    asString(item.get("clusterId")),
                    asString(item.get("namespaceName"))
            ));
        }
        for (Map<String, Object> item : getListOfMaps(root, "K8sWorkloads")) {
            data.k8sWorkloads().add(new ManifestData.K8sWorkload(
                    asString(item.get("clusterId")),
                    asString(item.get("namespaceName")),
                    asString(item.get("kind")),
                    asString(item.get("workloadName"))
            ));
        }
        for (Map<String, Object> item : getListOfMaps(root, "K8sServices")) {
            ManifestData.K8sWorkloadRef ref = null;
            Map<String, Object> routesMap = getMap(item, "routesToWorkload");
            if (routesMap != null) {
                ref = new ManifestData.K8sWorkloadRef(
                        asString(item.get("clusterId")),
                        asString(item.get("namespaceName")),
                        asString(routesMap.get("kind")),
                        asString(routesMap.get("workloadName"))
                );
            }
            data.k8sServices().add(new ManifestData.K8sService(
                    asString(item.get("clusterId")),
                    asString(item.get("namespaceName")),
                    asString(item.get("serviceName")),
                    asString(item.get("type")),
                    ref
            ));
        }
        for (Map<String, Object> item : getListOfMaps(root, "K8sPods")) {
            data.k8sPods().add(new ManifestData.K8sPods(
                    asString(item.get("clusterId")),
                    asString(item.get("namespaceName")),
                    getStringList(item.get("podNames"))
            ));
        }
    }

    private void parseFilers(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Filers")) {
            data.filers().add(new ManifestData.Filer(
                    asString(item.get("filerId")),
                    asString(item.get("name")),
                    asString(item.get("ipAddress")),
                    asString(item.get("type"))
            ));
        }

        for (Map<String, Object> item : getListOfMaps(root, "FilerRoles")) {
            data.filerRoles().add(new ManifestData.FilerRoles(
                    asString(item.get("filerId")),
                    normalizeValues(getStringList(item.get("roles")))
            ));
        }
    }

    private void parseVolumes(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Volumes")) {
            data.volumes().add(new ManifestData.Volume(
                    asString(item.get("volumeId")),
                    asString(item.get("name")),
                    asString(item.get("protocol")),
                    asString(item.get("filerId")),
                    asString(item.get("hostedByNodeId"))
            ));
        }
    }

    private void parseMounts(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Mounts")) {
            data.mounts().add(new ManifestData.Mount(
                    asString(item.get("volumeId")),
                    asString(item.get("nodeId")),
                    asString(item.get("clusterId")),
                    asString(item.get("mountPath")),
                    asString(item.get("accessMode")),
                    asString(item.get("exportOrShareName")),
                    NormalizationUtil.normalize(asString(item.get("protocolDetails")))
            ));
        }
    }

    private void parseNetworks(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Networks")) {
            data.networks().add(new ManifestData.Network(
                    asString(item.get("networkId")),
                    asString(item.get("name"))
            ));
        }
    }

    private void parseSubnets(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Subnets")) {
            data.subnets().add(new ManifestData.Subnet(
                    asString(item.get("subnetId")),
                    asString(item.get("networkId")),
                    asString(item.get("name")),
                    asString(item.get("cidr")),
                    asString(item.get("vlan"))
            ));
        }
    }

    private void parseSubnetConnections(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "SubnetConnections")) {
            data.subnetConnections().add(new ManifestData.SubnetConnection(
                    asString(item.get("entityType")),
                    asString(item.get("entityId")),
                    asString(item.get("subnetId"))
            ));
        }
    }

    private void parseDeployments(Map<String, Object> root, ManifestData data) {
        for (Map<String, Object> item : getListOfMaps(root, "Deployments")) {
            Map<String, Object> targetMap = getMap(item, "targets");
            List<String> nodes = new ArrayList<>();
            List<String> grids = new ArrayList<>();
            List<ManifestData.K8sWorkloadRef> workloads = new ArrayList<>();
            if (targetMap != null) {
                nodes = getStringList(targetMap.get("nodes"));
                grids = getStringList(targetMap.get("gridClusters"));
                for (Map<String, Object> k8sItem : getListOfMaps(targetMap, "k8sWorkloads")) {
                    workloads.add(new ManifestData.K8sWorkloadRef(
                            asString(k8sItem.get("clusterId")),
                            asString(k8sItem.get("namespaceName")),
                            asString(k8sItem.get("kind")),
                            asString(k8sItem.get("workloadName"))
                    ));
                }
            }

            data.deployments().add(new ManifestData.Deployment(
                    asString(item.get("deploymentId")),
                    asString(item.get("componentId")),
                    asString(item.get("projectId")),
                    asString(item.get("envId")),
                    new ManifestData.DeploymentTarget(nodes, grids, workloads)
            ));
        }
    }

    private List<String> normalizeValues(List<String> values) {
        List<String> normalized = new ArrayList<>();
        for (String value : values) {
            normalized.add(NormalizationUtil.normalize(value));
        }
        return normalized;
    }

    private Map<String, Object> getMap(Map<String, Object> root, String key) {
        Object obj = root.get(key);
        if (obj == null) {
            return null;
        }
        if (!(obj instanceof Map<?, ?> map)) {
            throw new ManifestParseException("Section '" + key + "' must be a map.");
        }
        return toStringObjectMap(map);
    }

    private List<Map<String, Object>> getListOfMaps(Map<String, Object> root, String key) {
        Object obj = root.get(key);
        if (obj == null) {
            return List.of();
        }
        if (!(obj instanceof List<?> list)) {
            throw new ManifestParseException("Section '" + key + "' must be a list.");
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> map)) {
                throw new ManifestParseException("Section '" + key + "' must contain map objects.");
            }
            out.add(toStringObjectMap(map));
        }
        return out;
    }

    private List<String> getStringList(Object obj) {
        if (obj == null) {
            return List.of();
        }
        if (!(obj instanceof List<?> list)) {
            throw new ManifestParseException("Expected list value but got: " + obj.getClass().getSimpleName());
        }
        List<String> out = new ArrayList<>();
        for (Object item : list) {
            out.add(asString(item));
        }
        return out;
    }

    private String asString(Object value) {
        if (value == null) {
            return "";
        }
        return String.valueOf(value).trim();
    }

    private Map<String, Object> toStringObjectMap(Map<?, ?> map) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            out.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return out;
    }
}

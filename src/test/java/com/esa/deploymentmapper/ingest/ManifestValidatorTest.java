package com.esa.deploymentmapper.ingest;

import com.esa.deploymentmapper.error.ValidationException;
import com.esa.deploymentmapper.model.ManifestData;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ManifestValidatorTest {

    private final ManifestValidator validator = new ManifestValidator();

    @Test
    void rejects_invalid_environment_enum() {
        ManifestData data = minimalValidManifest();
        data.environments().clear();
        data.environments().add(new ManifestData.Environment("env-prod", "prj-1", "prod", "Prod"));

        assertThatThrownBy(() -> validator.validateSingle(data, "test.yaml"))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("invalid value for Environments.type");
    }

    @Test
    void rejects_empty_deployment_targets() {
        ManifestData data = minimalValidManifest();
        data.deployments().clear();
        data.deployments().add(new ManifestData.Deployment("dep-1", "cmp-1", "prj-1", "env-1",
                new ManifestData.DeploymentTarget(List.of(), List.of(), List.of())));

        assertThatThrownBy(() -> validator.validateSingle(data, "test.yaml"))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("must have at least one target");
    }

    @Test
    void rejects_hostedBy_for_non_vm_node() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodes().add(new ManifestData.Node("node-1", "host1", "10.0.0.1", "Physical", "node-hv-1"));

        assertThatThrownBy(() -> validator.validateSingle(data, "test.yaml"))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("Nodes.hostedByNodeId can only be set for VM nodes");
    }

    @Test
    void rejects_self_hosting_node() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodes().add(new ManifestData.Node("node-1", "host1", "10.0.0.1", "VM", "node-1"));

        assertThatThrownBy(() -> validator.validateSingle(data, "test.yaml"))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("node cannot host itself");
    }

    @Test
    void rejects_missing_host_node_in_merged_validation() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodes().add(new ManifestData.Node("node-1", "vm1", "10.0.0.1", "VM", "node-hv-1"));

        assertThatThrownBy(() -> validator.validateMerged(data))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("references missing hostedByNodeId");
    }

    @Test
    void rejects_non_physical_host_node() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodeRoles().clear();
        data.nodes().add(new ManifestData.Node("node-1", "vm1", "10.0.0.1", "VM", "node-hv-1"));
        data.nodes().add(new ManifestData.Node("node-hv-1", "host1", "10.0.0.2", "VM", ""));
        data.nodeRoles().add(new ManifestData.NodeRoles("node-hv-1", List.of("hypervisor")));

        assertThatThrownBy(() -> validator.validateMerged(data))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("host node must be Physical");
    }

    @Test
    void rejects_host_without_hypervisor_role() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodeRoles().clear();
        data.nodes().add(new ManifestData.Node("node-1", "vm1", "10.0.0.1", "VM", "node-hv-1"));
        data.nodes().add(new ManifestData.Node("node-hv-1", "host1", "10.0.0.2", "Physical", ""));
        data.nodeRoles().add(new ManifestData.NodeRoles("node-hv-1", List.of("app_server")));

        assertThatThrownBy(() -> validator.validateMerged(data))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("host node must have hypervisor role");
    }

    @Test
    void accepts_vm_with_valid_hypervisor_host() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodeRoles().clear();
        data.nodes().add(new ManifestData.Node("node-1", "vm1", "10.0.0.1", "VM", "node-hv-1"));
        data.nodes().add(new ManifestData.Node("node-hv-1", "host1", "10.0.0.2", "Physical", ""));
        data.nodeRoles().add(new ManifestData.NodeRoles("node-hv-1", List.of("hypervisor")));

        validator.validateMerged(data);
    }

    @Test
    void rejects_missing_volume_host_node_in_merged_validation() {
        ManifestData data = minimalValidManifest();
        data.volumes().clear();
        data.volumes().add(new ManifestData.Volume("v-1", "vol", "NFS", "f-1", "node-host-1"));

        assertThatThrownBy(() -> validator.validateMerged(data))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("references missing hostedByNodeId");
    }

    @Test
    void rejects_non_physical_volume_host_node() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodes().add(new ManifestData.Node("node-1", "app1", "10.0.0.11", "VM", ""));
        data.nodes().add(new ManifestData.Node("node-host-1", "vm1", "10.0.0.1", "VM", ""));
        data.volumes().clear();
        data.volumes().add(new ManifestData.Volume("v-1", "vol", "NFS", "f-1", "node-host-1"));

        assertThatThrownBy(() -> validator.validateMerged(data))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("Volume v-1 host node must be Physical");
    }

    @Test
    void accepts_volume_with_physical_host_node() {
        ManifestData data = minimalValidManifest();
        data.nodes().clear();
        data.nodes().add(new ManifestData.Node("node-1", "app1", "10.0.0.11", "VM", ""));
        data.nodes().add(new ManifestData.Node("node-host-1", "host1", "10.0.0.1", "Physical", ""));
        data.volumes().clear();
        data.volumes().add(new ManifestData.Volume("v-1", "vol", "NFS", "f-1", "node-host-1"));

        validator.validateMerged(data);
    }

    private ManifestData minimalValidManifest() {
        ManifestData data = new ManifestData();
        data.setManifest(new ManifestData.ManifestInfo("m-1", "test.yaml"));
        data.organizations().add(new ManifestData.Organization("org-1", "Org"));
        data.projects().add(new ManifestData.Project("prj-1", "Project", "org-1"));
        data.applications().add(new ManifestData.Application("app-1", "App", "cfg", "1.0", "prj-1"));
        data.components().add(new ManifestData.Component("cmp-1", "Comp", "1.0", "app-1"));
        data.environments().add(new ManifestData.Environment("env-1", "prj-1", "prod", "Production"));
        data.nodes().add(new ManifestData.Node("node-1", "host1", "10.0.0.1", "VM", ""));
        data.clusters().add(new ManifestData.Cluster("cl-1", "grid", "Grid"));
        data.filers().add(new ManifestData.Filer("f-1", "nas", "10.0.1.1", "NAS"));
        data.volumes().add(new ManifestData.Volume("v-1", "vol", "NFS", "f-1", ""));
        data.networks().add(new ManifestData.Network("net-1", "net"));
        data.subnets().add(new ManifestData.Subnet("s-1", "net-1", "sub", "10.0.0.0/24", "100"));
        data.deployments().add(new ManifestData.Deployment("dep-1", "cmp-1", "prj-1", "env-1",
                new ManifestData.DeploymentTarget(List.of("node-1"), List.of(), List.of())));
        return data;
    }
}

package com.esa.deploymentmapper.ingest;

import com.esa.deploymentmapper.error.ValidationException;
import com.esa.deploymentmapper.model.ManifestData;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ManifestMergerTest {

    private final ManifestMerger merger = new ManifestMerger();

    @Test
    void merges_missing_values_from_other_manifest() {
        ManifestData first = new ManifestData();
        first.setManifest(new ManifestData.ManifestInfo("m-1", "one.yaml"));
        first.organizations().add(new ManifestData.Organization("org-1", ""));

        ManifestData second = new ManifestData();
        second.setManifest(new ManifestData.ManifestInfo("m-2", "two.yaml"));
        second.organizations().add(new ManifestData.Organization("org-1", "Acme"));

        ManifestData merged = merger.merge(List.of(first, second));
        assertThat(merged.organizations()).hasSize(1);
        assertThat(merged.organizations().get(0).name()).isEqualTo("Acme");
    }

    @Test
    void fails_on_conflicting_non_empty_values() {
        ManifestData first = new ManifestData();
        first.setManifest(new ManifestData.ManifestInfo("m-1", "one.yaml"));
        first.organizations().add(new ManifestData.Organization("org-1", "Acme"));

        ManifestData second = new ManifestData();
        second.setManifest(new ManifestData.ManifestInfo("m-2", "two.yaml"));
        second.organizations().add(new ManifestData.Organization("org-1", "Beta"));

        assertThatThrownBy(() -> merger.merge(List.of(first, second)))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("Conflict in Organization.name");
    }

    @Test
    void fails_on_node_identity_mismatch() {
        ManifestData first = new ManifestData();
        first.setManifest(new ManifestData.ManifestInfo("m-1", "one.yaml"));
        first.nodes().add(new ManifestData.Node("node-1", "a.local", "10.0.0.1", "VM", ""));

        ManifestData second = new ManifestData();
        second.setManifest(new ManifestData.ManifestInfo("m-2", "two.yaml"));
        second.nodes().add(new ManifestData.Node("node-1", "b.local", "10.0.0.1", "VM", ""));

        assertThatThrownBy(() -> merger.merge(List.of(first, second)))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("Node identity conflict");
    }

    @Test
    void merges_missing_hostedByNodeId_from_other_manifest() {
        ManifestData first = new ManifestData();
        first.setManifest(new ManifestData.ManifestInfo("m-1", "one.yaml"));
        first.nodes().add(new ManifestData.Node("node-1", "a.local", "10.0.0.1", "VM", ""));

        ManifestData second = new ManifestData();
        second.setManifest(new ManifestData.ManifestInfo("m-2", "two.yaml"));
        second.nodes().add(new ManifestData.Node("node-1", "a.local", "10.0.0.1", "VM", "node-hv-1"));

        ManifestData merged = merger.merge(List.of(first, second));
        assertThat(merged.nodes()).hasSize(1);
        assertThat(merged.nodes().get(0).hostedByNodeId()).isEqualTo("node-hv-1");
    }

    @Test
    void fails_on_conflicting_hostedByNodeId_values() {
        ManifestData first = new ManifestData();
        first.setManifest(new ManifestData.ManifestInfo("m-1", "one.yaml"));
        first.nodes().add(new ManifestData.Node("node-1", "a.local", "10.0.0.1", "VM", "node-hv-1"));

        ManifestData second = new ManifestData();
        second.setManifest(new ManifestData.ManifestInfo("m-2", "two.yaml"));
        second.nodes().add(new ManifestData.Node("node-1", "a.local", "10.0.0.1", "VM", "node-hv-2"));

        assertThatThrownBy(() -> merger.merge(List.of(first, second)))
                .isInstanceOf(ValidationException.class)
                .hasMessageContaining("Conflict in Node.hostedByNodeId");
    }
}

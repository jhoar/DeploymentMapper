package com.esa.deploymentmapper.integration;

import com.esa.deploymentmapper.cli.DeploymentMapperCli;
import org.junit.jupiter.api.Test;
import picocli.CommandLine;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class MultiManifestAndFailureIntegrationTest {

    @Test
    void merges_multiple_manifests_successfully() throws Exception {
        Path tempDir = Files.createTempDirectory("dm-it-split-");
        Path outputDir = tempDir.resolve("out");
        Path dbDir = tempDir.resolve("db");

        int exitCode = new CommandLine(new DeploymentMapperCli()).execute(
                "--input", Path.of("src", "test", "resources", "manifests", "valid", "split_a.yaml").toAbsolutePath().toString(),
                "--input", Path.of("src", "test", "resources", "manifests", "valid", "split_b.yaml").toAbsolutePath().toString(),
                "--output-dir", outputDir.toString(),
                "--db-path", dbDir.toString(),
                "--clean-db"
        );

        assertThat(exitCode).isEqualTo(0);
        assertThat(outputDir.resolve("deployment-map.puml")).exists();
        assertThat(Files.readString(outputDir.resolve("deployment-map.puml"))).contains("HOSTED_BY");
    }

    @Test
    void fails_fast_on_conflicting_node_identity() throws Exception {
        Path tempDir = Files.createTempDirectory("dm-it-bad-");
        Path outputDir = tempDir.resolve("out");

        int exitCode = new CommandLine(new DeploymentMapperCli()).execute(
                "--input", Path.of("src", "test", "resources", "manifests", "invalid", "conflict_node_a.yaml").toAbsolutePath().toString(),
                "--input", Path.of("src", "test", "resources", "manifests", "invalid", "conflict_node_b.yaml").toAbsolutePath().toString(),
                "--output-dir", outputDir.toString()
        );

        assertThat(exitCode).isEqualTo(1);
    }

    @Test
    void fails_fast_on_invalid_hosted_by_relationship() throws Exception {
        Path tempDir = Files.createTempDirectory("dm-it-bad-host-");
        Path outputDir = tempDir.resolve("out");

        int exitCode = new CommandLine(new DeploymentMapperCli()).execute(
                "--input", Path.of("src", "test", "resources", "manifests", "invalid", "hosted_by_non_vm.yaml").toAbsolutePath().toString(),
                "--output-dir", outputDir.toString()
        );

        assertThat(exitCode).isEqualTo(1);
    }
}

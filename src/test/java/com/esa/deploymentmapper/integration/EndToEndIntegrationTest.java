package com.esa.deploymentmapper.integration;

import com.esa.deploymentmapper.cli.DeploymentMapperCli;
import org.junit.jupiter.api.Test;
import picocli.CommandLine;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class EndToEndIntegrationTest {

    @Test
    void generates_puml_and_png_from_single_manifest() throws Exception {
        Path tempDir = Files.createTempDirectory("dm-it-");
        Path outputDir = tempDir.resolve("out");
        Path dbDir = tempDir.resolve("db");
        Path input = Path.of("examples", "acme_example_manifest.yaml").toAbsolutePath();

        int exitCode = new CommandLine(new DeploymentMapperCli()).execute(
                "--input", input.toString(),
                "--output-dir", outputDir.toString(),
                "--db-path", dbDir.toString(),
                "--clean-db"
        );

        assertThat(exitCode).isEqualTo(0);
        assertThat(outputDir.resolve("deployment-map.puml")).exists();
        assertThat(outputDir.resolve("deployment-map.png")).exists();
        assertThat(Files.size(outputDir.resolve("deployment-map.png"))).isGreaterThan(0L);
    }
}

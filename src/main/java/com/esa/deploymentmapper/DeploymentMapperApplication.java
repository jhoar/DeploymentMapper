package com.esa.deploymentmapper;

import com.esa.deploymentmapper.cli.DeploymentMapperCli;
import picocli.CommandLine;

public final class DeploymentMapperApplication {
    private DeploymentMapperApplication() {
    }

    public static void main(String[] args) {
        int exitCode = new CommandLine(new DeploymentMapperCli()).execute(args);
        System.exit(exitCode);
    }
}

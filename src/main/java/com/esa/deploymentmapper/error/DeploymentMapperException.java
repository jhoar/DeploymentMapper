package com.esa.deploymentmapper.error;

public class DeploymentMapperException extends RuntimeException {
    public DeploymentMapperException(String message) {
        super(message);
    }

    public DeploymentMapperException(String message, Throwable cause) {
        super(message, cause);
    }
}

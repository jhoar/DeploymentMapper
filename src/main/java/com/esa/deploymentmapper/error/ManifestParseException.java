package com.esa.deploymentmapper.error;

public class ManifestParseException extends DeploymentMapperException {
    public ManifestParseException(String message, Throwable cause) {
        super(message, cause);
    }

    public ManifestParseException(String message) {
        super(message);
    }
}

package com.esa.deploymentmapper.diagram;

import com.esa.deploymentmapper.error.DeploymentMapperException;
import net.sourceforge.plantuml.SourceStringReader;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class PlantUmlRenderer {

    public void render(String plantUmlText, Path pumlPath, Path pngPath) {
        try {
            Files.createDirectories(pumlPath.getParent());
            Files.writeString(pumlPath, plantUmlText, StandardCharsets.UTF_8);
            SourceStringReader reader = new SourceStringReader(plantUmlText);
            try (OutputStream outputStream = Files.newOutputStream(pngPath)) {
                reader.outputImage(outputStream);
            }
        } catch (IOException e) {
            throw new DeploymentMapperException("Failed to write diagram artifacts", e);
        }
    }
}

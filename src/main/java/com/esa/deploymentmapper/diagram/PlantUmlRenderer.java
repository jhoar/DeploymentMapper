package com.esa.deploymentmapper.diagram;

import com.esa.deploymentmapper.error.DeploymentMapperException;
import net.sourceforge.plantuml.SourceStringReader;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class PlantUmlRenderer {
    private static final int MIN_PLANTUML_LIMIT_SIZE = 16384;

    public void render(String plantUmlText, Path pumlPath, Path pngPath) {
        try {
            ensurePlantUmlLimitSize();
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

    private void ensurePlantUmlLimitSize() {
        String currentValue = System.getProperty("PLANTUML_LIMIT_SIZE");
        if (currentValue == null) {
            System.setProperty("PLANTUML_LIMIT_SIZE", Integer.toString(MIN_PLANTUML_LIMIT_SIZE));
            return;
        }
        try {
            int parsed = Integer.parseInt(currentValue.trim());
            if (parsed < MIN_PLANTUML_LIMIT_SIZE) {
                System.setProperty("PLANTUML_LIMIT_SIZE", Integer.toString(MIN_PLANTUML_LIMIT_SIZE));
            }
        } catch (NumberFormatException ignored) {
            System.setProperty("PLANTUML_LIMIT_SIZE", Integer.toString(MIN_PLANTUML_LIMIT_SIZE));
        }
    }
}

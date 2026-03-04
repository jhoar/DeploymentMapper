package com.esa.deploymentmapper.cli;

import com.esa.deploymentmapper.diagram.DiagramModel;
import com.esa.deploymentmapper.diagram.DiagramProjectionService;
import com.esa.deploymentmapper.diagram.PlantUmlRenderer;
import com.esa.deploymentmapper.diagram.PlantUmlTextBuilder;
import com.esa.deploymentmapper.error.DeploymentMapperException;
import com.esa.deploymentmapper.error.ValidationException;
import com.esa.deploymentmapper.graph.GraphWriter;
import com.esa.deploymentmapper.graph.Neo4jEmbeddedManager;
import com.esa.deploymentmapper.graph.SchemaInitializer;
import com.esa.deploymentmapper.ingest.ManifestMerger;
import com.esa.deploymentmapper.ingest.ManifestValidator;
import com.esa.deploymentmapper.ingest.YamlManifestReader;
import com.esa.deploymentmapper.model.ManifestData;
import picocli.CommandLine;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.DosFileAttributeView;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.stream.Stream;

@CommandLine.Command(name = "deployment-mapper", mixinStandardHelpOptions = true,
        description = "Read deployment manifests, load embedded Neo4j, and generate PlantUML outputs.")
public class DeploymentMapperCli implements Callable<Integer> {

    @CommandLine.Option(names = "--input", required = true, arity = "1..*", description = "Input YAML file(s) or directories")
    private List<Path> inputs;

    @CommandLine.Option(names = "--output-dir", required = true, description = "Output directory for diagram files")
    private Path outputDir;

    @CommandLine.Option(names = "--db-path", description = "Path for embedded Neo4j data")
    private Path dbPath;

    @CommandLine.Option(names = "--clean-db", description = "Delete existing embedded Neo4j directory before run")
    private boolean cleanDb;

    @CommandLine.Option(names = "--diagram-name", defaultValue = "deployment-map", description = "Base output filename")
    private String diagramName;

    @Override
    public Integer call() {
        try {
            List<Path> inputFiles = resolveInputFiles(inputs);
            if (inputFiles.isEmpty()) {
                throw new DeploymentMapperException("No YAML files found from provided --input paths");
            }

            YamlManifestReader reader = new YamlManifestReader();
            ManifestValidator validator = new ManifestValidator();
            List<ManifestData> manifests = new ArrayList<>();
            for (Path inputFile : inputFiles) {
                ManifestData data = reader.read(inputFile);
                validator.validateSingle(data, inputFile.toString());
                manifests.add(data);
            }

            ManifestMerger merger = new ManifestMerger();
            ManifestData merged = merger.merge(manifests);
            validator.validateMerged(merged);

            Files.createDirectories(outputDir);
            Path resolvedDbPath = dbPath != null ? dbPath : outputDir.resolve("neo4j-db");
            if (cleanDb && Files.exists(resolvedDbPath)) {
                deleteRecursively(resolvedDbPath);
            }
            Files.createDirectories(resolvedDbPath.getParent() == null ? Paths.get(".") : resolvedDbPath.getParent());

            try (Neo4jEmbeddedManager neo4j = new Neo4jEmbeddedManager(resolvedDbPath)) {
                new SchemaInitializer().initialize(neo4j.database());
                new GraphWriter().write(neo4j.database(), merged);

                DiagramModel model = new DiagramProjectionService().project(neo4j.database());
                String plantUmlText = new PlantUmlTextBuilder().build(model);
                Path pumlPath = outputDir.resolve(diagramName + ".puml");
                Path pngPath = outputDir.resolve(diagramName + ".png");
                new PlantUmlRenderer().render(plantUmlText, pumlPath, pngPath);

                System.out.println("Generated: " + pumlPath);
                System.out.println("Generated: " + pngPath);
                System.out.println("Embedded Neo4j path: " + resolvedDbPath);
            }

            return 0;
        } catch (ValidationException e) {
            System.err.println(e.getMessage());
            return 1;
        } catch (DeploymentMapperException e) {
            System.err.println("Error: " + e.getMessage());
            return 2;
        } catch (IOException e) {
            System.err.println("I/O error: " + e.getMessage());
            return 2;
        } catch (RuntimeException e) {
            System.err.println("Unexpected error: " + e.getMessage());
            return 3;
        }
    }

    private List<Path> resolveInputFiles(List<Path> paths) {
        List<Path> files = new ArrayList<>();
        for (Path path : paths) {
            if (Files.isRegularFile(path) && isYaml(path)) {
                files.add(path.toAbsolutePath().normalize());
                continue;
            }
            if (Files.isDirectory(path)) {
                try (Stream<Path> stream = Files.walk(path)) {
                    stream
                            .filter(Files::isRegularFile)
                            .filter(this::isYaml)
                            .forEach(candidate -> files.add(candidate.toAbsolutePath().normalize()));
                } catch (IOException e) {
                    throw new DeploymentMapperException("Failed to enumerate directory: " + path, e);
                }
                continue;
            }
            throw new DeploymentMapperException("Input path does not exist or is invalid: " + path);
        }
        files.sort(Comparator.comparing(Path::toString));
        return files;
    }

    private boolean isYaml(Path path) {
        String name = path.getFileName().toString().toLowerCase();
        return name.endsWith(".yaml") || name.endsWith(".yml");
    }

    private void deleteRecursively(Path path) {
        try {
            Files.walkFileTree(path, new SimpleFileVisitor<>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                    deletePathWithRetry(file);
                    return FileVisitResult.CONTINUE;
                }

                @Override
                public FileVisitResult postVisitDirectory(Path dir, IOException exc) throws IOException {
                    if (exc != null) {
                        throw exc;
                    }
                    deletePathWithRetry(dir);
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            throw new DeploymentMapperException("Failed to clean db path: " + path, e);
        }
    }

    private void deletePathWithRetry(Path path) {
        IOException last = null;
        for (int attempt = 1; attempt <= 5; attempt++) {
            try {
                clearReadOnlyAttribute(path);
                Files.deleteIfExists(path);
                return;
            } catch (IOException e) {
                last = e;
                if (attempt < 5) {
                    try {
                        Thread.sleep(150L);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new DeploymentMapperException("Interrupted while deleting path: " + path, ie);
                    }
                }
            }
        }
        throw new DeploymentMapperException("Failed deleting path: " + path, last);
    }

    private void clearReadOnlyAttribute(Path path) {
        try {
            DosFileAttributeView dos = Files.getFileAttributeView(path, DosFileAttributeView.class);
            if (dos != null) {
                dos.setReadOnly(false);
            }
        } catch (IOException ignored) {
            // Best-effort: deletion retry will surface the real problem if it still fails.
        }
    }
}

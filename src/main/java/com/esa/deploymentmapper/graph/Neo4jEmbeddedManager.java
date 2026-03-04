package com.esa.deploymentmapper.graph;

import org.neo4j.configuration.GraphDatabaseSettings;
import org.neo4j.dbms.api.DatabaseManagementService;
import org.neo4j.dbms.api.DatabaseManagementServiceBuilder;
import org.neo4j.graphdb.GraphDatabaseService;

import java.nio.file.Path;

public class Neo4jEmbeddedManager implements AutoCloseable {
    private final DatabaseManagementService managementService;
    private final GraphDatabaseService database;

    public Neo4jEmbeddedManager(Path dbPath) {
        this.managementService = new DatabaseManagementServiceBuilder(dbPath)
                .setConfig(GraphDatabaseSettings.strict_config_validation, false)
                .build();
        this.database = managementService.database(GraphDatabaseSettings.DEFAULT_DATABASE_NAME);
    }

    public GraphDatabaseService database() {
        return database;
    }

    @Override
    public void close() {
        managementService.shutdown();
    }
}

package com.esa.deploymentmapper.diagram;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class DiagramModel {
    private final Map<String, NodeDecl> nodes = new LinkedHashMap<>();
    private final List<EdgeDecl> edges = new ArrayList<>();
    private final Map<String, List<String>> packageMembers = new LinkedHashMap<>();

    public Map<String, NodeDecl> nodes() {
        return nodes;
    }

    public List<EdgeDecl> edges() {
        return edges;
    }

    public Map<String, List<String>> packageMembers() {
        return packageMembers;
    }

    public void addNode(String alias, String label, String stereotype) {
        nodes.putIfAbsent(alias, new NodeDecl(alias, label, stereotype));
    }

    public void addEdge(String fromAlias, String toAlias, String label, boolean dotted) {
        edges.add(new EdgeDecl(fromAlias, toAlias, label, dotted));
    }

    public void addPackageMember(String packageName, String alias) {
        packageMembers.computeIfAbsent(packageName, ignored -> new ArrayList<>());
        if (!packageMembers.get(packageName).contains(alias)) {
            packageMembers.get(packageName).add(alias);
        }
    }

    public record NodeDecl(String alias, String label, String stereotype) {}
    public record EdgeDecl(String fromAlias, String toAlias, String label, boolean dotted) {}
}

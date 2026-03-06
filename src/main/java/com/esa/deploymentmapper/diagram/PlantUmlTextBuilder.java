package com.esa.deploymentmapper.diagram;

public class PlantUmlTextBuilder {

    public String build(DiagramModel model) {
        StringBuilder sb = new StringBuilder();
        sb.append("@startuml\n");
        sb.append("skinparam backgroundColor #FFFFFF\n");
        sb.append("skinparam defaultFontName Courier\n");
        sb.append("skinparam Padding 24\n");
        sb.append("scale max 3800 width\n");
        sb.append("hide empty members\n\n");

        for (var entry : model.packageMembers().entrySet()) {
            sb.append("package \"").append(escape(entry.getKey())).append("\" {\n");
            for (String alias : entry.getValue()) {
                DiagramModel.NodeDecl node = model.nodes().get(alias);
                if (node != null) {
                    sb.append("  node \"").append(escape(node.label())).append("\" as ").append(node.alias())
                            .append(" <<").append(node.stereotype()).append(">>\n");
                }
            }
            sb.append("}\n\n");
        }

        for (DiagramModel.NodeDecl node : model.nodes().values()) {
            if (!isInAnyPackage(model, node.alias())) {
                sb.append("node \"").append(escape(node.label())).append("\" as ").append(node.alias())
                        .append(" <<").append(node.stereotype()).append(">>\n");
            }
        }
        sb.append("\n");

        for (DiagramModel.EdgeDecl edge : model.edges()) {
            sb.append(edge.fromAlias())
                    .append(edge.dotted() ? " ..> " : " --> ")
                    .append(edge.toAlias())
                    .append(" : ")
                    .append(escape(edge.label()))
                    .append("\n");
        }
        sb.append("@enduml\n");
        return sb.toString();
    }

    private boolean isInAnyPackage(DiagramModel model, String alias) {
        return model.packageMembers().values().stream().anyMatch(members -> members.contains(alias));
    }

    private String escape(String value) {
        return value.replace("\"", "\\\"");
    }
}

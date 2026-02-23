PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subnets (
  id TEXT PRIMARY KEY,
  cidr TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hardware_nodes (
  id TEXT PRIMARY KEY,
  hostname TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  subnet_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kubernetes_clusters (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  subnet_id TEXT NOT NULL,
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS virtual_machines (
  id TEXT PRIMARY KEY,
  hostname TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  subnet_id TEXT NOT NULL,
  host_node_id TEXT NOT NULL,
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE,
  FOREIGN KEY (host_node_id) REFERENCES hardware_nodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS storage_servers (
  id TEXT PRIMARY KEY,
  hostname TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  subnet_id TEXT NOT NULL,
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS network_switches (
  id TEXT PRIMARY KEY,
  hostname TEXT NOT NULL,
  management_ip TEXT NOT NULL,
  subnet_id TEXT NOT NULL,
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS software_systems (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT
);

CREATE TABLE IF NOT EXISTS components (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  component_type TEXT
);

CREATE TABLE IF NOT EXISTS deployment_instances (
  id TEXT PRIMARY KEY,
  system_id TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_node_id TEXT,
  target_cluster_id TEXT,
  component_id TEXT,
  namespace TEXT,
  FOREIGN KEY (system_id) REFERENCES software_systems(id) ON DELETE CASCADE,
  FOREIGN KEY (target_cluster_id) REFERENCES kubernetes_clusters(id) ON DELETE CASCADE,
  FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS system_components (
  system_id TEXT NOT NULL,
  component_id TEXT NOT NULL,
  PRIMARY KEY (system_id, component_id),
  FOREIGN KEY (system_id) REFERENCES software_systems(id) ON DELETE CASCADE,
  FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS component_deployments (
  component_id TEXT NOT NULL,
  deployment_instance_id TEXT NOT NULL,
  PRIMARY KEY (component_id, deployment_instance_id),
  FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE,
  FOREIGN KEY (deployment_instance_id) REFERENCES deployment_instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cluster_nodes (
  cluster_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  PRIMARY KEY (cluster_id, node_id),
  FOREIGN KEY (cluster_id) REFERENCES kubernetes_clusters(id) ON DELETE CASCADE,
  FOREIGN KEY (node_id) REFERENCES hardware_nodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS network_links (
  subnet_id TEXT NOT NULL,
  node_type TEXT NOT NULL,
  node_id TEXT NOT NULL,
  PRIMARY KEY (subnet_id, node_type, node_id),
  FOREIGN KEY (subnet_id) REFERENCES subnets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_deployment_instances_system ON deployment_instances(system_id);
CREATE INDEX IF NOT EXISTS idx_network_links_subnet ON network_links(subnet_id);

INSERT INTO subnets (id, cidr, name) VALUES
  ('subnet-dc', '10.0.10.0/24', 'datacenter'),
  ('subnet-app', '10.0.20.0/24', 'application'),
  ('subnet-k8s', '10.0.30.0/24', 'kubernetes');

INSERT INTO hardware_nodes (id, hostname, ip_address, subnet_id, kind) VALUES
  ('host-1', 'metal-host-1', '10.0.10.10', 'subnet-dc', 'PHYSICAL'),
  ('k8s-node-1', 'k8s-node-1', '10.0.30.21', 'subnet-k8s', 'K8S_NODE'),
  ('k8s-node-2', 'k8s-node-2', '10.0.30.22', 'subnet-k8s', 'K8S_NODE');

INSERT INTO virtual_machines (id, hostname, ip_address, subnet_id, host_node_id) VALUES
  ('vm-orders-1', 'orders-vm-1', '10.0.20.11', 'subnet-app', 'host-1');

INSERT INTO storage_servers (id, hostname, ip_address, subnet_id) VALUES
  ('storage-1', 'storage-main-1', '10.0.10.40', 'subnet-dc');

INSERT INTO network_switches (id, hostname, management_ip, subnet_id) VALUES
  ('switch-1', 'dc-switch-1', '10.0.10.2', 'subnet-dc');

INSERT INTO kubernetes_clusters (id, name, subnet_id) VALUES
  ('cluster-1', 'prod-cluster', 'subnet-k8s');

INSERT INTO cluster_nodes (cluster_id, node_id) VALUES
  ('cluster-1', 'k8s-node-1'),
  ('cluster-1', 'k8s-node-2');

INSERT INTO software_systems (id, name, version) VALUES
  ('system-billing', 'Billing API', '2.3.1'),
  ('system-orders', 'Orders API', '4.1.0'),
  ('system-observability', 'Observability Stack', '1.18.2');

INSERT INTO components (id, name, component_type) VALUES
  ('cmp-billing-app', 'billing-app', 'service'),
  ('cmp-orders-api', 'orders-api', 'service'),
  ('cmp-orders-worker', 'orders-worker', 'worker'),
  ('cmp-observability', 'prometheus', 'platform');

INSERT INTO system_components (system_id, component_id) VALUES
  ('system-billing', 'cmp-billing-app'),
  ('system-orders', 'cmp-orders-api'),
  ('system-orders', 'cmp-orders-worker'),
  ('system-observability', 'cmp-observability');

INSERT INTO deployment_instances (id, system_id, target_kind, target_node_id, target_cluster_id, component_id, namespace) VALUES
  ('dep-billing-host', 'system-billing', 'HOST', 'host-1', NULL, 'cmp-billing-app', NULL),
  ('dep-orders-vm', 'system-orders', 'VM', 'vm-orders-1', NULL, 'cmp-orders-api', NULL),
  ('dep-orders-worker', 'system-orders', 'VM', 'vm-orders-1', NULL, 'cmp-orders-worker', NULL),
  ('dep-observe-k8s', 'system-observability', 'K8S_NAMESPACE', NULL, 'cluster-1', 'cmp-observability', 'observability');

INSERT INTO component_deployments (component_id, deployment_instance_id) VALUES
  ('cmp-billing-app', 'dep-billing-host'),
  ('cmp-orders-api', 'dep-orders-vm'),
  ('cmp-orders-worker', 'dep-orders-worker'),
  ('cmp-observability', 'dep-observe-k8s');

INSERT INTO network_links (subnet_id, node_type, node_id) VALUES
  ('subnet-dc', 'hardware', 'host-1'),
  ('subnet-k8s', 'hardware', 'k8s-node-1'),
  ('subnet-k8s', 'hardware', 'k8s-node-2'),
  ('subnet-app', 'vm', 'vm-orders-1'),
  ('subnet-dc', 'storage', 'storage-1'),
  ('subnet-dc', 'switch', 'switch-1');

# Neo4j Schema for Software Deployment Mapper

This document contains the Neo4j **schema** (labels, relationships, constraints/indexes) derived from the provided requirements, plus the remaining **missing/ambiguous** information.

---

## 1) Graph schema

### Provenance
**Manifest**
- `manifestId` *(string, unique; allocated at ingest start)*
- `path` *(string; filename/path)*
- `ingestedAt` *(datetime, optional)*
- `hash` *(string, optional)*

Optional provenance edge:
- `(m:Manifest)-[:DECLARES]->(x)` *(any node/relationship)*

---

### Organization hierarchy
**Organization**
- `orgId` *(string, unique)*
- `name` *(string)*

**Project**
- `projectId` *(string, unique)*
- `name` *(string)*

**Application**
- `appId` *(string, unique)*
- `name` *(string)*
- `configurationId` *(string)*
- `version` *(string)*

**Component**
- `componentId` *(string, unique)*
- `name` *(string)*
- `version` *(string)*

---

### Environment (project-scoped, envName normalized)
Rules:
- Environments not shared across projects
- Unique env type per project
- Actual key = `projectId + ":" + envId`
- `envName` case-normalized and `(projectId, envName)` unique

**Environment**
- `envId` *(string; unique only within project)*
- `projectEnvId` *(string, unique)* = `projectId + ":" + envId`
- `name` *(string; stored normalized)*
- `type` *(enum: `Development|Test|Staging|Production`)*
- `projectTypeKey` *(string, unique)* = `projectId + ":" + type`
- `projectNameKey` *(string, unique)* = `projectId + ":" + name` *(name already normalized)*

---

### Deployment
Rules:
- one per (Component, Environment)
- no history over time
- hostname targets must exist
- different target relationship types

**Deployment**
- `deploymentId` *(string, unique)*
- `deploymentKey` *(string, unique)* = `componentId + ":" + projectEnvId`

---

### Nodes and roles
**Node**
- `nodeId` *(string, unique)*
- `hostname` *(string, unique)*
- `ipAddress` *(string; IPv4 not validated)*
- `type` *(enum: `Physical|VM`)*
- `hostedByNodeId` *(string, optional; source field used to create `HOSTED_BY` edge)*

**NodeRole**
- `nodeRoleId` *(string, unique)* = normalize(name)
- `name` *(string; normalized)*

> Since IDs are derived from normalized names, `nodeRoleId` can equal the normalized `name`.

---

### Clusters and roles (shared across projects)
**Cluster**
- `clusterId` *(string, unique)*
- `clusterName` *(string)*
- `type` *(enum: `Grid|Kubernetes`)*

**ClusterRole**
- `clusterRoleId` *(string, unique)* = normalize(name)
- `name` *(string; normalized)*

---

### Kubernetes model (desired state pods, summarized in diagram)
Deterministic IDs:

**K8sNamespace**
- `namespaceId` *(string, unique)* = `clusterId + ":" + namespaceName`
- `name` *(string)*

**K8sWorkload**
- `workloadId` *(string, unique)* = `namespaceId + ":" + kind + ":" + workloadName`
- `name` *(string)*
- `kind` *(enum: `Deployment|StatefulSet|DaemonSet|Job|CronJob|Other`)*

**K8sPod** *(desired state)*
- `podId` *(string, unique)* = `namespaceId + ":" + podName`
- `name` *(string)*

**K8sService**
- `serviceId` *(string, unique)* = `namespaceId + ":" + serviceName`
- `name` *(string)*
- `type` *(enum: `ClusterIP|NodePort|LoadBalancer|ExternalName|Other`)*

---

### Storage
**Filer**
- `filerId` *(string, unique)*
- `name` *(string)*
- `ipAddress` *(string)*
- `type` *(enum: `SAN|NAS`)*

**FilerRole**
- `filerRoleId` *(string, unique)* = normalize(name)
- `name` *(string; normalized)*

**Volume**
- `volumeId` *(string, unique)*
- `name` *(string)*
- `protocol` *(enum: `NFS|SMB|iSCSI|S3`)*

Mount relationship properties (same for node and cluster mounts):
- `mountPath` (string)
- `accessMode` (`ro|rw`)
- `exportOrShareName` (string)
- `protocolDetails` (string; normalized free text)

---

### Network / Subnet
**Network**
- `networkId` *(string, unique)*
- `name` *(string)*

**Subnet**
- `subnetId` *(string, unique)*
- `name` *(string)*
- `cidr` *(string; globally unique across networks)*
- `vlan` *(string)*
- `vlanKey` *(string, unique)* = `networkId + ":" + vlan`

---

## 2) Relationships

### Hierarchy
- `(o:Organization)-[:HAS_PROJECT]->(p:Project)`
- `(p:Project)-[:HAS_APPLICATION]->(a:Application)`
- `(a:Application)-[:OWNS_COMPONENT]->(c:Component)`

### Environments
- `(p:Project)-[:HAS_ENVIRONMENT]->(e:Environment)`

### Deployments
- `(c:Component)-[:HAS_DEPLOYMENT]->(d:Deployment)`
- `(d:Deployment)-[:IN_ENV]->(e:Environment)`

Targets (explicit types):
- **Node deployments:** `(d)-[:DEPLOYED_TO]->(n:Node)`
- **Grid deployments:** `(d)-[:DEPLOYED_TO_CLUSTER]->(g:Cluster {type:'Grid'})`
- **K8s deployments:** `(d)-[:DEPLOYED_TO_WORKLOAD]->(w:K8sWorkload)`

Convenience edges for K8s:
- also create `(d)-[:DEPLOYED_TO]->(ep:Node)` for cluster endpoint nodes associated with that workload's cluster.

### Roles
- `(n:Node)-[:HAS_ROLE]->(r:NodeRole)`
- `(c:Cluster)-[:HAS_ROLE]->(r:ClusterRole)`
- `(f:Filer)-[:HAS_ROLE]->(r:FilerRole)`

### Grid cluster structure
- `(g:Cluster {type:'Grid'})-[:HAS_MANAGER]->(n:Node)`
- `(g:Cluster {type:'Grid'})-[:HAS_WORKER]->(n:Node)`

### Virtualization topology
- `(vm:Node {type:'VM'})-[:HOSTED_BY]->(hv:Node {type:'Physical'})`
- Host node (`hv`) must carry node role `hypervisor`.

### Kubernetes topology + endpoints
Endpoint nodes are `Node` objects; a cluster can have multiple:
- `(k:Cluster {type:'Kubernetes'})-[:HAS_ENDPOINT]->(ep:Node)`

K8s resources:
- `(k)-[:HAS_NAMESPACE]->(ns:K8sNamespace)`
- `(ns)-[:HAS_WORKLOAD]->(w:K8sWorkload)`
- `(w)-[:OWNS_POD]->(pod:K8sPod)` *(desired-state)*
- `(ns)-[:EXPOSES_SERVICE]->(svc:K8sService)`
- `(svc)-[:ROUTES_TO_WORKLOAD]->(w)`

### Storage
- `(f:Filer)-[:HOSTS_VOLUME]->(v:Volume)`
- `(n:Node)-[m:MOUNTS_VOLUME]->(v:Volume)`
- `(c:Cluster)-[m:MOUNTS_VOLUME]->(v:Volume)`

*(Uniqueness "mounted once" per (Node,Volume) and per (Cluster,Volume) is enforced in ingestion logic.)*

### Networking
- `(net:Network)-[:HAS_SUBNET]->(s:Subnet)`
- `(n:Node)-[:CONNECTED_TO_SUBNET]->(s:Subnet)`
- `(c:Cluster)-[:CONNECTED_TO_SUBNET]->(s:Subnet)`
- `(f:Filer)-[:CONNECTED_TO_SUBNET]->(s:Subnet)`

---

## 3) Constraints & indexes (Cypher DDL)

```cypher
// --- Manifest ---
CREATE CONSTRAINT manifest_id IF NOT EXISTS
FOR (m:Manifest) REQUIRE m.manifestId IS UNIQUE;

// --- Core ---
CREATE CONSTRAINT org_id IF NOT EXISTS
FOR (o:Organization) REQUIRE o.orgId IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.projectId IS UNIQUE;

CREATE CONSTRAINT app_id IF NOT EXISTS
FOR (a:Application) REQUIRE a.appId IS UNIQUE;

CREATE CONSTRAINT component_id IF NOT EXISTS
FOR (c:Component) REQUIRE c.componentId IS UNIQUE;

// --- Environment (project-scoped) ---
CREATE CONSTRAINT env_projectEnvId IF NOT EXISTS
FOR (e:Environment) REQUIRE e.projectEnvId IS UNIQUE;

CREATE CONSTRAINT env_projectTypeKey IF NOT EXISTS
FOR (e:Environment) REQUIRE e.projectTypeKey IS UNIQUE;

CREATE CONSTRAINT env_projectNameKey IF NOT EXISTS
FOR (e:Environment) REQUIRE e.projectNameKey IS UNIQUE;

// --- Deployment uniqueness ---
CREATE CONSTRAINT deployment_id IF NOT EXISTS
FOR (d:Deployment) REQUIRE d.deploymentId IS UNIQUE;

CREATE CONSTRAINT deployment_key IF NOT EXISTS
FOR (d:Deployment) REQUIRE d.deploymentKey IS UNIQUE;

// --- Nodes ---
CREATE CONSTRAINT node_id IF NOT EXISTS
FOR (n:Node) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT node_hostname IF NOT EXISTS
FOR (n:Node) REQUIRE n.hostname IS UNIQUE;

// --- Clusters ---
CREATE CONSTRAINT cluster_id IF NOT EXISTS
FOR (c:Cluster) REQUIRE c.clusterId IS UNIQUE;

// --- Roles (IDs derived from normalized name) ---
CREATE CONSTRAINT nodeRole_id IF NOT EXISTS
FOR (r:NodeRole) REQUIRE r.nodeRoleId IS UNIQUE;

CREATE CONSTRAINT clusterRole_id IF NOT EXISTS
FOR (r:ClusterRole) REQUIRE r.clusterRoleId IS UNIQUE;

CREATE CONSTRAINT filerRole_id IF NOT EXISTS
FOR (r:FilerRole) REQUIRE r.filerRoleId IS UNIQUE;

// --- Filer / Volume ---
CREATE CONSTRAINT filer_id IF NOT EXISTS
FOR (f:Filer) REQUIRE f.filerId IS UNIQUE;

CREATE CONSTRAINT volume_id IF NOT EXISTS
FOR (v:Volume) REQUIRE v.volumeId IS UNIQUE;

// --- Network/Subnet ---
CREATE CONSTRAINT network_id IF NOT EXISTS
FOR (n:Network) REQUIRE n.networkId IS UNIQUE;

CREATE CONSTRAINT subnet_id IF NOT EXISTS
FOR (s:Subnet) REQUIRE s.subnetId IS UNIQUE;

// CIDR cannot appear in multiple networks
CREATE CONSTRAINT subnet_cidr_unique IF NOT EXISTS
FOR (s:Subnet) REQUIRE s.cidr IS UNIQUE;

// VLAN unique within a network
CREATE CONSTRAINT subnet_vlanKey_unique IF NOT EXISTS
FOR (s:Subnet) REQUIRE s.vlanKey IS UNIQUE;

// --- Kubernetes ---
CREATE CONSTRAINT k8s_namespace_id IF NOT EXISTS
FOR (ns:K8sNamespace) REQUIRE ns.namespaceId IS UNIQUE;

CREATE CONSTRAINT k8s_workload_id IF NOT EXISTS
FOR (w:K8sWorkload) REQUIRE w.workloadId IS UNIQUE;

CREATE CONSTRAINT k8s_pod_id IF NOT EXISTS
FOR (p:K8sPod) REQUIRE p.podId IS UNIQUE;

CREATE CONSTRAINT k8s_service_id IF NOT EXISTS
FOR (s:K8sService) REQUIRE s.serviceId IS UNIQUE;

// --- Helpful indexes for your query set ---
CREATE INDEX env_type IF NOT EXISTS FOR (e:Environment) ON (e.type);
CREATE INDEX node_type IF NOT EXISTS FOR (n:Node) ON (n.type);
CREATE INDEX subnet_vlan IF NOT EXISTS FOR (s:Subnet) ON (s.vlan);
CREATE INDEX volume_protocol IF NOT EXISTS FOR (v:Volume) ON (v.protocol);
CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name);
```

---

## 4) Ingestion/consistency rules implied by your spec

### Normalization
`normalize(x) = lowercase(trim(x))` then replace spaces with `_`.

Apply to:
- `Environment.name` before building `projectNameKey`
- role names before creating role nodes / IDs
- `protocolDetails`

### Conflict resolution ("fill missing else error")
- existing null/empty + new non-empty -> set
- both non-empty and differ -> error

Hard errors:
- same `nodeId` different `hostname` -> error
- same `hostname` different `nodeId` -> error
- deployment references hostname not found as `Node` -> error
- if `hostedByNodeId` is set, source node must be `type=VM`
- if `hostedByNodeId` is set, source node cannot equal host node
- `hostedByNodeId` must reference an existing node
- host node for `HOSTED_BY` must be `type=Physical`
- host node for `HOSTED_BY` must have node role `hypervisor`

Mount uniqueness (ingestion logic, not constraints):
- at most one `MOUNTS_VOLUME` per `(Node,Volume)`
- at most one `MOUNTS_VOLUME` per `(Cluster,Volume)`

K8s convenience edge (ingestion behavior):
- when creating `(d)-[:DEPLOYED_TO_WORKLOAD]->(w)`, also create `(d)-[:DEPLOYED_TO]->(ep)` for each endpoint `ep` of that workload's cluster.

---

## 5) Missing / ambiguous information

1) **How to link a K8sWorkload to its Cluster endpoints**
You have `Cluster-[:HAS_NAMESPACE]->Namespace-[:HAS_WORKLOAD]->Workload` and `Cluster-[:HAS_ENDPOINT]->Node`.
This works, but ingestion should validate that each `K8sNamespace` belongs to exactly one cluster (and therefore each workload does too).

2) **Grid deployment convenience edges**
You now have `DEPLOYED_TO_CLUSTER` for grid deployments.
Decide whether ingestion should also create `DEPLOYED_TO` edges to the grid's manager/worker nodes automatically (convenience), or keep only the cluster edge.

3) **Kubernetes endpoint node identification**
Endpoint nodes are `Node` objects with `type Physical|VM`. Distinguish "cluster endpoint" vs regular nodes either by:
- relationship presence `(Cluster)-[:HAS_ENDPOINT]->(Node)` (sufficient), or
- an explicit boolean property (optional).

4) **Environment envId collisions within a project**
Given `projectEnvId = projectId:envId`, ingestion should treat collisions with differing name/type as errors (recommended), but it should be explicitly enforced in the loader.

5) **Diagram rule for volumes mounted by cluster vs node**
You decided: exclude volumes not mounted by any node **or cluster** in the project.
For volumes mounted by a cluster, decide whether the diagram shows the mount attached to:
- the cluster node itself,
- the endpoint nodes,
- or both (most informative but could clutter).

6) **Subnet label format in PlantUML**
You said dotted lines for `CONNECTED_TO_SUBNET` and subnets under network packages.
Define the exact label you want (commonly: subnet name + CIDR + VLAN).


import argparse
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pandas as pd
import yaml

INPUT_FILE = "deployment_mapper_from_example_yaml.xlsx"
OUTPUT_FILE = "deployment_manifest.yaml"


def _read_sheet_optional(xls: pd.ExcelFile, name: str) -> pd.DataFrame:
    if name not in xls.sheet_names:
        return pd.DataFrame()
    df = pd.read_excel(xls, sheet_name=name)
    return df.dropna(how="all")


def _read_sheet_required(xls: pd.ExcelFile, name: str) -> pd.DataFrame:
    if name not in xls.sheet_names:
        raise ValueError(f"Missing required sheet: {name}")
    df = pd.read_excel(xls, sheet_name=name)
    return df.dropna(how="all")


def _require_columns(df: pd.DataFrame, sheet: str, columns: Sequence[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Sheet '{sheet}' is missing required columns: {missing}")

def _split_csv(value: Any) -> List[str]:
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    parts = []
    for chunk in s.replace(";", ",").split(","):
        c = chunk.strip()
        if c:
            parts.append(c)
    return parts


def convert_excel_to_manifest(input_file: str, output_file: str) -> None:
    xls = pd.ExcelFile(input_file)
    out: Dict[str, Any] = {}

    # Manifest (single row)
    df = _read_sheet_required(xls, "Manifest")
    _require_columns(df, "Manifest", ["manifestId", "path"])
    manifest_rows = df.fillna("").to_dict(orient="records")
    if not manifest_rows:
        raise ValueError("Sheet 'Manifest' must contain at least one non-empty row.")
    r = manifest_rows[0]
    out["Manifest"] = {"manifestId": r.get("manifestId", ""), "path": r.get("path", "")}

    def records(sheet: str):
        df = _read_sheet_optional(xls, sheet)
        if df.empty:
            return []
        return df.fillna("").to_dict(orient="records")

    # Simple collections
    for key in [
        "Organizations","Projects","Applications","Components","Environments","Nodes",
        "Clusters","Filers","Volumes","Networks","Subnets","SubnetConnections"
    ]:
        recs = records(key)
        if recs:
            out[key] = recs

    # Roles (list fields)
    df = _read_sheet_optional(xls, "NodeRoles")
    if not df.empty:
        _require_columns(df, "NodeRoles", ["nodeId", "roles_csv"])
        out["NodeRoles"] = [
            {"nodeId": r["nodeId"], "roles": _split_csv(r.get("roles_csv",""))}
            for r in df.fillna("").to_dict(orient="records")
            if str(r.get("nodeId","")).strip()
        ]

    df = _read_sheet_optional(xls, "ClusterRoles")
    if not df.empty:
        _require_columns(df, "ClusterRoles", ["clusterId", "roles_csv"])
        out["ClusterRoles"] = [
            {"clusterId": r["clusterId"], "roles": _split_csv(r.get("roles_csv",""))}
            for r in df.fillna("").to_dict(orient="records")
            if str(r.get("clusterId","")).strip()
        ]

    df = _read_sheet_optional(xls, "FilerRoles")
    if not df.empty:
        _require_columns(df, "FilerRoles", ["filerId", "roles_csv"])
        out["FilerRoles"] = [
            {"filerId": r["filerId"], "roles": _split_csv(r.get("roles_csv",""))}
            for r in df.fillna("").to_dict(orient="records")
            if str(r.get("filerId","")).strip()
        ]

    # GridMembers
    df = _read_sheet_optional(xls, "GridMembers")
    if not df.empty:
        _require_columns(df, "GridMembers", ["clusterId", "managers_csv", "workers_csv"])
        out["GridMembers"] = [{
            "clusterId": r["clusterId"],
            "managers": _split_csv(r.get("managers_csv","")),
            "workers": _split_csv(r.get("workers_csv","")),
        } for r in df.fillna("").to_dict(orient="records") if str(r.get("clusterId","")).strip()]

    # ClusterEndpoints
    df = _read_sheet_optional(xls, "ClusterEndpoints")
    if not df.empty:
        _require_columns(df, "ClusterEndpoints", ["clusterId", "endpointNodeIds_csv"])
        out["ClusterEndpoints"] = [{
            "clusterId": r["clusterId"],
            "endpointNodeIds": _split_csv(r.get("endpointNodeIds_csv","")),
        } for r in df.fillna("").to_dict(orient="records") if str(r.get("clusterId","")).strip()]

    # K8s
    for key in ["K8sNamespaces","K8sWorkloads"]:
        recs = records(key)
        if recs:
            out[key] = recs

    df = _read_sheet_optional(xls, "K8sServices")
    if not df.empty:
        _require_columns(
            df,
            "K8sServices",
            ["clusterId", "namespaceName", "serviceName", "type", "routesToKind", "routesToWorkloadName"],
        )
        rows = df.fillna("").to_dict(orient="records")
        services = []
        for r in rows:
            if not str(r.get("clusterId","")).strip():
                continue
            item = {
                "clusterId": r.get("clusterId",""),
                "namespaceName": r.get("namespaceName",""),
                "serviceName": r.get("serviceName",""),
                "type": r.get("type",""),
            }
            kind = str(r.get("routesToKind","")).strip()
            wn = str(r.get("routesToWorkloadName","")).strip()
            if kind and wn:
                item["routesToWorkload"] = {"kind": kind, "workloadName": wn}
            elif kind or wn:
                raise ValueError(
                    "K8sServices row has partial routesToWorkload data; provide both routesToKind and routesToWorkloadName."
                )
            services.append(item)
        if services:
            out["K8sServices"] = services

    df = _read_sheet_optional(xls, "K8sPods")
    if not df.empty:
        _require_columns(df, "K8sPods", ["clusterId", "namespaceName", "podNames_csv"])
        out["K8sPods"] = [{
            "clusterId": r["clusterId"],
            "namespaceName": r["namespaceName"],
            "podNames": _split_csv(r.get("podNames_csv","")),
        } for r in df.fillna("").to_dict(orient="records") if str(r.get("clusterId","")).strip()]

    # Mounts
    df = _read_sheet_optional(xls, "Mounts")
    if not df.empty:
        out["Mounts"] = df.fillna("").to_dict(orient="records")

    # Deployments + target sheets
    dep_rows = records("Deployments")
    if dep_rows:
        dep_df = pd.DataFrame(dep_rows)
        _require_columns(dep_df, "Deployments", ["deploymentId"])
    node_targets: Dict[str, List[str]] = {}
    grid_targets: Dict[str, List[str]] = {}
    k8s_targets: Dict[str, List[Dict[str,str]]] = {}

    df = _read_sheet_optional(xls, "DeploymentTargets_Nodes")
    if not df.empty:
        _require_columns(df, "DeploymentTargets_Nodes", ["deploymentId", "nodeId"])
        for r in df.fillna("").to_dict(orient="records"):
            did = str(r.get("deploymentId","")).strip()
            nid = str(r.get("nodeId","")).strip()
            if did and nid:
                node_targets.setdefault(did, []).append(nid)

    df = _read_sheet_optional(xls, "DeploymentTargets_GridClusters")
    if not df.empty:
        _require_columns(df, "DeploymentTargets_GridClusters", ["deploymentId", "clusterId"])
        for r in df.fillna("").to_dict(orient="records"):
            did = str(r.get("deploymentId","")).strip()
            cid = str(r.get("clusterId","")).strip()
            if did and cid:
                grid_targets.setdefault(did, []).append(cid)

    df = _read_sheet_optional(xls, "DeploymentTargets_K8sWorkloads")
    if not df.empty:
        _require_columns(
            df,
            "DeploymentTargets_K8sWorkloads",
            ["deploymentId", "clusterId", "namespaceName", "kind", "workloadName"],
        )
        for r in df.fillna("").to_dict(orient="records"):
            did = str(r.get("deploymentId","")).strip()
            if not did:
                continue
            item = {
                "clusterId": str(r.get("clusterId","")).strip(),
                "namespaceName": str(r.get("namespaceName","")).strip(),
                "kind": str(r.get("kind","")).strip(),
                "workloadName": str(r.get("workloadName","")).strip(),
            }
            if all(item.values()):
                k8s_targets.setdefault(did, []).append(item)

    if dep_rows:
        for d in dep_rows:
            did = str(d.get("deploymentId","")).strip()
            targets: Dict[str, Any] = {}
            if did in node_targets:
                targets["nodes"] = node_targets[did]
            if did in grid_targets:
                targets["gridClusters"] = grid_targets[did]
            if did in k8s_targets:
                targets["k8sWorkloads"] = k8s_targets[did]
            if targets:
                d["targets"] = targets
        out["Deployments"] = dep_rows

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True)

    print(f"Wrote {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert deployment mapper workbook to YAML manifest.")
    parser.add_argument("--input", default=INPUT_FILE, help="Path to source Excel workbook.")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Path to output YAML file.")
    args = parser.parse_args()

    input_file = str(Path(args.input))
    output_file = str(Path(args.output))
    convert_excel_to_manifest(input_file, output_file)

if __name__ == "__main__":
    main()

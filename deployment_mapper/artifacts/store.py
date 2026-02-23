from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class ArtifactMetadata:
    created_at: str
    content_type: str
    source_schema_id: str | None
    source_schema_version: str | None
    request_id: str
    schema_hash: str


@dataclass(slots=True)
class StoredArtifact:
    path: Path
    metadata_path: Path
    metadata: ArtifactMetadata


class ArtifactStore(Protocol):
    def write_text(
        self,
        *,
        request_id: str,
        schema_payload: dict[str, object],
        content: str,
        content_type: str,
    ) -> StoredArtifact:
        """Persist text content and metadata for an artifact."""


class LocalArtifactStore:
    def __init__(
        self,
        base_dir: str | Path = "deployment_mapper/artifacts",
        ttl_seconds: int | None = None,
        max_count: int | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.ttl_seconds = ttl_seconds
        self.max_count = max_count
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_text(
        self,
        *,
        request_id: str,
        schema_payload: dict[str, object],
        content: str,
        content_type: str,
    ) -> StoredArtifact:
        schema_hash = self._schema_hash(schema_payload)
        extension = self._extension_for_content_type(content_type)

        artifact_dir = self.base_dir / request_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = artifact_dir / f"{schema_hash}{extension}"
        metadata_path = artifact_dir / f"{schema_hash}.metadata.json"

        metadata = ArtifactMetadata(
            created_at=datetime.now(UTC).isoformat(),
            content_type=content_type,
            source_schema_id=self._source_schema_id(schema_payload),
            source_schema_version=self._source_schema_version(schema_payload),
            request_id=request_id,
            schema_hash=schema_hash,
        )

        artifact_path.write_text(content, encoding="utf-8")
        metadata_path.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")

        self._cleanup()
        return StoredArtifact(path=artifact_path, metadata_path=metadata_path, metadata=metadata)

    def list_artifacts(self, request_id: str | None = None) -> list[StoredArtifact]:
        if request_id:
            candidates = [
                path
                for path in (self.base_dir / request_id).glob("*")
                if path.is_file() and not path.name.endswith(".metadata.json")
            ]
        else:
            candidates = self._list_artifacts_by_mtime()

        artifacts: list[StoredArtifact] = []
        for artifact_path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
            metadata_path = artifact_path.with_name(f"{artifact_path.stem}.metadata.json")
            if not metadata_path.exists():
                continue
            metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata = ArtifactMetadata(**metadata_payload)
            artifacts.append(StoredArtifact(path=artifact_path, metadata_path=metadata_path, metadata=metadata))
        return artifacts

    def read_text(self, request_id: str, artifact_name: str) -> StoredArtifact:
        artifact_path = (self.base_dir / request_id / artifact_name).resolve()
        if self.base_dir.resolve() not in artifact_path.parents or not artifact_path.exists() or artifact_path.is_dir():
            raise FileNotFoundError(artifact_name)

        metadata_path = artifact_path.with_name(f"{artifact_path.stem}.metadata.json")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found for {artifact_name}")

        metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = ArtifactMetadata(**metadata_payload)
        return StoredArtifact(path=artifact_path, metadata_path=metadata_path, metadata=metadata)

    def cleanup(self) -> int:
        before = len(self._list_artifacts_by_mtime())
        self._cleanup()
        after = len(self._list_artifacts_by_mtime())
        return max(before - after, 0)

    def _schema_hash(self, schema_payload: dict[str, object]) -> str:
        canonical_json = json.dumps(schema_payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def _source_schema_id(self, schema_payload: dict[str, object]) -> str | None:
        return str(schema_payload.get("schema_id") or schema_payload.get("id")) if (
            schema_payload.get("schema_id") or schema_payload.get("id")
        ) else None

    def _source_schema_version(self, schema_payload: dict[str, object]) -> str | None:
        return str(schema_payload.get("schema_version") or schema_payload.get("version")) if (
            schema_payload.get("schema_version") or schema_payload.get("version")
        ) else None

    def _cleanup(self) -> None:
        artifacts = self._list_artifacts_by_mtime()
        if self.ttl_seconds is not None:
            cutoff = datetime.now(UTC) - timedelta(seconds=self.ttl_seconds)
            for artifact_path in artifacts:
                modified_at = datetime.fromtimestamp(artifact_path.stat().st_mtime, tz=UTC)
                if modified_at < cutoff:
                    self._delete_artifact_pair(artifact_path)

            artifacts = self._list_artifacts_by_mtime()

        if self.max_count is not None and len(artifacts) > self.max_count:
            excess = len(artifacts) - self.max_count
            for artifact_path in artifacts[:excess]:
                self._delete_artifact_pair(artifact_path)

    def _list_artifacts_by_mtime(self) -> list[Path]:
        files = [
            path
            for path in self.base_dir.glob("*/*")
            if path.is_file() and not path.name.endswith(".metadata.json")
        ]
        return sorted(files, key=lambda p: p.stat().st_mtime)

    def _delete_artifact_pair(self, artifact_path: Path) -> None:
        metadata_path = artifact_path.with_name(f"{artifact_path.stem}.metadata.json")
        artifact_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)

    @staticmethod
    def _extension_for_content_type(content_type: str) -> str:
        mapping = {
            "text/plain": ".txt",
            "text/plantuml": ".puml",
            "image/png": ".png",
            "image/svg+xml": ".svg",
            "application/json": ".json",
        }
        return mapping.get(content_type, ".artifact")

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from deployment_mapper.artifacts import LocalArtifactStore


class LocalArtifactStoreTests(unittest.TestCase):
    def test_write_text_uses_deterministic_request_and_schema_hash_path(self) -> None:
        payload = {"schema_id": "orders", "schema_version": "2", "nodes": [{"id": "n1"}]}
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)
            first = store.write_text(
                request_id="req-123",
                schema_payload=payload,
                content="@startuml\n@enduml",
                content_type="text/plantuml",
            )
            second = store.write_text(
                request_id="req-123",
                schema_payload=payload,
                content="@startuml\n@enduml",
                content_type="text/plantuml",
            )

            self.assertEqual(first.path, second.path)
            self.assertEqual(first.path.parent.name, "req-123")
            self.assertEqual(first.path.suffix, ".puml")

    def test_write_text_persists_metadata(self) -> None:
        payload = {"schema_id": "orders", "schema_version": "2"}
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)
            stored = store.write_text(
                request_id="req-meta",
                schema_payload=payload,
                content="example",
                content_type="text/plain",
            )

            metadata = json.loads(stored.metadata_path.read_text(encoding="utf-8"))
            self.assertIn("created_at", metadata)
            self.assertEqual(metadata["content_type"], "text/plain")
            self.assertEqual(metadata["source_schema_id"], "orders")
            self.assertEqual(metadata["source_schema_version"], "2")

    def test_cleanup_max_count_removes_oldest_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp, max_count=1)
            store.write_text(
                request_id="one",
                schema_payload={"schema_id": "a"},
                content="first",
                content_type="text/plain",
            )
            time.sleep(0.01)
            latest = store.write_text(
                request_id="two",
                schema_payload={"schema_id": "b"},
                content="second",
                content_type="text/plain",
            )

            artifacts = [
                p
                for p in Path(tmp).glob("*/*")
                if p.is_file() and not p.name.endswith(".metadata.json")
            ]
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0], latest.path)

    def test_cleanup_ttl_removes_expired_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp, ttl_seconds=1)
            expired = store.write_text(
                request_id="old",
                schema_payload={"schema_id": "old"},
                content="old",
                content_type="text/plain",
            )
            stale_time = time.time() - 120
            os.utime(expired.path, (stale_time, stale_time))
            os.utime(expired.metadata_path, (stale_time, stale_time))

            fresh = store.write_text(
                request_id="fresh",
                schema_payload={"schema_id": "new"},
                content="new",
                content_type="text/plain",
            )

            self.assertFalse(expired.path.exists())
            self.assertFalse(expired.metadata_path.exists())
            self.assertTrue(fresh.path.exists())
            self.assertTrue(fresh.metadata_path.exists())

    def test_read_text_rejects_traversal_like_artifact_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)

            with self.assertRaises(FileNotFoundError):
                store.read_text("req-1", "../outside.txt")

    def test_read_text_raises_when_metadata_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)
            request_dir = Path(tmp) / "req-missing-meta"
            request_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = request_dir / "artifact.txt"
            artifact_path.write_text("payload", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                store.read_text("req-missing-meta", "artifact.txt")

    def test_list_artifacts_request_id_returns_only_artifact_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)
            stored = store.write_text(
                request_id="req-files-only",
                schema_payload={"schema_id": "id"},
                content="artifact content",
                content_type="text/plain",
            )
            stray_metadata = stored.path.parent / "extra.metadata.json"
            stray_metadata.write_text("{}", encoding="utf-8")

            artifacts = store.list_artifacts(request_id="req-files-only")

            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0].path, stored.path)
            self.assertFalse(artifacts[0].path.name.endswith(".metadata.json"))

    def test_list_artifacts_skips_orphan_artifacts_without_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp)
            stored = store.write_text(
                request_id="req-with-orphan",
                schema_payload={"schema_id": "valid"},
                content="ok",
                content_type="text/plain",
            )
            orphan_path = stored.path.parent / "orphan.txt"
            orphan_path.write_text("orphan", encoding="utf-8")

            artifacts = store.list_artifacts(request_id="req-with-orphan")

            self.assertEqual([artifact.path for artifact in artifacts], [stored.path])

    def test_cleanup_returns_count_of_removed_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(base_dir=tmp, max_count=1)
            old = store.write_text(
                request_id="cleanup-old",
                schema_payload={"schema_id": "old"},
                content="old",
                content_type="text/plain",
            )
            time.sleep(0.01)
            latest = store.write_text(
                request_id="cleanup-new",
                schema_payload={"schema_id": "new"},
                content="new",
                content_type="text/plain",
            )
            store.max_count = 0

            before = len(store.list_artifacts())
            removed_count = store.cleanup()
            after = len(store.list_artifacts())

            self.assertEqual(removed_count, before - after)
            self.assertEqual(removed_count, 1)
            self.assertFalse(old.path.exists())
            self.assertFalse(old.metadata_path.exists())
            self.assertFalse(latest.path.exists())
            self.assertFalse(latest.metadata_path.exists())


if __name__ == "__main__":
    unittest.main()

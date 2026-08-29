"""Content-addressed immutable snapshot storage."""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from stockballdb.snapshots.models import (
    SIDEcar_SCHEMA_VERSION,
    SnapshotReference,
    digest_from_snapshot_id,
    snapshot_id_from_digest,
)
from stockballdb.snapshots.sanitize import sanitize_request_identity, scan_object_for_secrets


class SnapshotError(Exception):
    """Base snapshot store error."""


class SnapshotCorruptionError(SnapshotError):
    """Existing payload content does not match its snapshot_id."""


class SnapshotStore:
    """Filesystem-backed content-addressed snapshot store."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or repo_snapshots_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def _relative_payload_path(self, payload_path: Path) -> str:
        rel = payload_path.relative_to(self.root).as_posix()
        if self.root.resolve() == repo_snapshots_root().resolve():
            return f"snapshots/{rel}"
        return rel

    def resolve_payload_path(self, relative: str) -> Path:
        rel = relative.replace("\\", "/")
        if rel.startswith("snapshots/"):
            return repo_root() / rel
        return self.root / rel

    def _digest(self, raw_bytes: bytes) -> str:
        return hashlib.sha256(raw_bytes).hexdigest()

    def _paths(self, digest_hex: str) -> tuple[Path, Path]:
        shard = digest_hex[:2]
        base = self.root / "sha256" / shard
        payload = base / f"{digest_hex}.gz"
        meta = base / f"{digest_hex}.meta.json"
        return payload, meta

    def store_snapshot(
        self,
        raw_bytes: bytes,
        *,
        provider: str,
        source_identifier: str,
        source_type: str,
        request_identity: dict[str, Any],
        retrieved_at: dt.datetime,
        content_type: str = "application/octet-stream",
        encoding: str = "utf-8",
        http_status: int | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> SnapshotReference:
        if not raw_bytes and source_type not in ("api_json", "html_page"):
            raise SnapshotError("refusing empty snapshot payload")

        clean_identity = sanitize_request_identity(request_identity)
        if scan_object_for_secrets(clean_identity):
            raise SnapshotError("request_identity contains secret-like keys")

        digest = self._digest(raw_bytes)
        snapshot_id = snapshot_id_from_digest(digest)
        payload_path, meta_path = self._paths(digest)

        if payload_path.exists():
            self._verify_existing(payload_path, digest)
            if not meta_path.exists():
                self._write_sidecar(
                    meta_path,
                    sha256=digest,
                    snapshot_id=snapshot_id,
                    provider=provider,
                    source_identifier=source_identifier,
                    source_type=source_type,
                    request_identity=clean_identity,
                    retrieved_at=retrieved_at,
                    content_type=content_type,
                    encoding=encoding,
                    byte_size_uncompressed=len(raw_bytes),
                    byte_size_compressed=payload_path.stat().st_size,
                    http_status=http_status,
                    etag=etag,
                    last_modified=last_modified,
                    payload_path=self._relative_payload_path(payload_path),
                )
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return self._ref_from_sidecar(meta)

        payload_path.parent.mkdir(parents=True, exist_ok=True)
        compressed = gzip.compress(raw_bytes, compresslevel=6, mtime=0)
        self._atomic_write_bytes(payload_path, compressed)
        self._verify_existing(payload_path, digest)

        rel = self._relative_payload_path(payload_path)
        self._write_sidecar(
            meta_path,
            sha256=digest,
            snapshot_id=snapshot_id,
            provider=provider,
            source_identifier=source_identifier,
            source_type=source_type,
            request_identity=clean_identity,
            retrieved_at=retrieved_at,
            content_type=content_type,
            encoding=encoding,
            byte_size_uncompressed=len(raw_bytes),
            byte_size_compressed=len(compressed),
            http_status=http_status,
            etag=etag,
            last_modified=last_modified,
            payload_path=rel,
        )
        return SnapshotReference(
            snapshot_id=snapshot_id,
            sha256=digest,
            provider=provider,
            source_identifier=source_identifier,
            source_type=source_type,
            retrieved_at=retrieved_at,
            request_identity=clean_identity,
            payload_path=rel,
            byte_size_uncompressed=len(raw_bytes),
            byte_size_compressed=len(compressed),
            content_type=content_type,
            encoding=encoding,
            http_status=http_status,
        )

    def load_snapshot(self, snapshot_id: str) -> bytes:
        digest = digest_from_snapshot_id(snapshot_id)
        payload_path, _ = self._paths(digest)
        if not payload_path.exists():
            raise SnapshotError(f"snapshot payload missing: {snapshot_id}")
        try:
            raw = gzip.decompress(payload_path.read_bytes())
        except OSError as exc:
            raise SnapshotCorruptionError(
                f"snapshot payload unreadable for {snapshot_id}: {exc}"
            ) from exc
        if self._digest(raw) != digest:
            raise SnapshotCorruptionError(
                f"snapshot hash mismatch for {snapshot_id}"
            )
        return raw

    def load_sidecar(self, snapshot_id: str) -> dict[str, Any]:
        digest = digest_from_snapshot_id(snapshot_id)
        _, meta_path = self._paths(digest)
        if not meta_path.exists():
            raise SnapshotError(f"snapshot metadata missing: {snapshot_id}")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _verify_existing(self, payload_path: Path, digest: str) -> None:
        try:
            raw = gzip.decompress(payload_path.read_bytes())
        except OSError as exc:
            raise SnapshotCorruptionError(
                f"existing snapshot corrupted at {payload_path}: {exc}"
            ) from exc
        if self._digest(raw) != digest:
            raise SnapshotCorruptionError(
                f"existing snapshot corrupted at {payload_path}"
            )

    def _atomic_write_bytes(self, dest: Path, data: bytes) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(dest.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, dest)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _write_sidecar(self, path: Path, **fields: Any) -> None:
        if isinstance(fields.get("retrieved_at"), dt.datetime):
            fields = {
                **fields,
                "retrieved_at": fields["retrieved_at"].isoformat(),
            }
        payload = {
            "schema_version": SIDEcar_SCHEMA_VERSION,
            **fields,
        }
        if scan_object_for_secrets(payload):
            raise SnapshotError("sidecar contains secret-like keys")
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self._atomic_write_bytes(path, text.encode("utf-8"))

    def _ref_from_sidecar(self, meta: dict[str, Any]) -> SnapshotReference:
        sha = meta.get("sha256") or meta.get("digest")
        return SnapshotReference(
            snapshot_id=meta["snapshot_id"],
            sha256=sha,
            provider=meta["provider"],
            source_identifier=meta["source_identifier"],
            source_type=meta["source_type"],
            retrieved_at=dt.datetime.fromisoformat(meta["retrieved_at"]),
            request_identity=meta["request_identity"],
            payload_path=meta["payload_path"],
            byte_size_uncompressed=meta["byte_size_uncompressed"],
            byte_size_compressed=meta.get("byte_size_compressed"),
            content_type=meta.get("content_type", "application/octet-stream"),
            encoding=meta.get("encoding", "utf-8"),
            http_status=meta.get("http_status"),
        )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def repo_snapshots_root() -> Path:
    return repo_root() / "snapshots"

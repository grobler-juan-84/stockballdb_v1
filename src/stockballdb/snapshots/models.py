"""Snapshot domain models."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceMode(str, Enum):
    LIVE = "live"
    SNAPSHOT = "snapshot"


SIDEcar_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SnapshotReference:
    snapshot_id: str
    sha256: str
    provider: str
    source_identifier: str
    source_type: str
    retrieved_at: dt.datetime
    request_identity: dict[str, Any]
    payload_path: str
    byte_size_uncompressed: int
    byte_size_compressed: int | None = None
    content_type: str = "application/octet-stream"
    encoding: str = "utf-8"
    http_status: int | None = None

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "sha256": self.sha256,
            "provider": self.provider,
            "source_identifier": self.source_identifier,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "request_identity": self.request_identity,
            "payload_path": self.payload_path,
            "byte_size_uncompressed": self.byte_size_uncompressed,
        }


@dataclass
class BuildSnapshotCollector:
    """Collects snapshot references during a LIVE build."""

    mode: SourceMode = SourceMode.LIVE
    references: list[SnapshotReference] = field(default_factory=list)
    retrieval_events: int = 0
    _lookup: dict[str, SnapshotReference] = field(default_factory=dict, repr=False)

    def register(self, ref: SnapshotReference) -> None:
        self.references.append(ref)
        self.retrieval_events += 1
        key = request_identity_key(ref.request_identity)
        self._lookup[key] = ref

    def resolve(self, request_identity: dict[str, Any]) -> SnapshotReference:
        key = request_identity_key(ref := request_identity)
        if key not in self._lookup:
            raise KeyError(f"no snapshot for request identity: {ref}")
        return self._lookup[key]

    @classmethod
    def from_manifest(cls, snapshots: list[dict[str, Any]]) -> BuildSnapshotCollector:
        collector = cls(mode=SourceMode.SNAPSHOT)
        for entry in snapshots:
            ref = SnapshotReference(
                snapshot_id=entry["snapshot_id"],
                sha256=entry["sha256"],
                provider=entry["provider"],
                source_identifier=entry["source_identifier"],
                source_type=entry["source_type"],
                retrieved_at=dt.datetime.fromisoformat(entry["retrieved_at"]),
                request_identity=entry["request_identity"],
                payload_path=entry["payload_path"],
                byte_size_uncompressed=entry.get("byte_size_uncompressed", 0),
            )
            collector.register(ref)
        return collector


def request_identity_key(request_identity: dict[str, Any]) -> str:
    import json

    return json.dumps(request_identity, sort_keys=True, separators=(",", ":"))


def snapshot_id_from_digest(digest_hex: str) -> str:
    return f"sha256:{digest_hex}"


def digest_from_snapshot_id(snapshot_id: str) -> str:
    prefix = "sha256:"
    if not snapshot_id.startswith(prefix):
        raise ValueError(f"invalid snapshot_id: {snapshot_id}")
    return snapshot_id[len(prefix) :]

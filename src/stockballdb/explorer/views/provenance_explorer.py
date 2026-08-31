"""Provenance Explorer page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from stockballdb.explorer.services import provenance as prov_service


def render() -> None:
    st.caption("Build-level provenance — not row-level snapshot lineage.")
    manifests = prov_service.list_manifests()
    runs = prov_service.list_run_reports()

    st.subheader("Manifests (newest first)")
    for rec in manifests[:20]:
        label = rec.artifact_id
        if rec.error:
            st.warning(f"{label} — unreadable: {rec.error}")
            continue
        if st.button(f"View manifest {label}", key=f"m_{label}"):
            st.session_state["manifest_path"] = str(rec.path)

    st.subheader("Operational runs (newest first)")
    for rec in runs[:20]:
        if rec.error:
            st.warning(f"{rec.artifact_id} — {rec.error}")
            continue
        payload = rec.payload or {}
        st.write(
            f"`{rec.artifact_id}` — **{payload.get('status')}** | "
            f"{payload.get('failure_kind') or payload.get('change_classification') or '—'}"
        )

    path_str = st.session_state.get("manifest_path")
    if path_str:
        try:
            detail = prov_service.manifest_detail(Path(path_str))
            st.subheader("Manifest detail")
            st.json(
                {
                    k: v
                    for k, v in detail.items()
                    if k not in {"snapshots", "stages", "datasets", "table_fingerprints"}
                }
            )
            snaps = prov_service.snapshot_metadata_list(detail)
            st.write(f"Snapshots referenced: {len(snaps)}")
            if snaps:
                st.dataframe(snaps[:50], use_container_width=True)
        except Exception as exc:
            st.error(f"Manifest detail failed: {exc}")

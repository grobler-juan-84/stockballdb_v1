"""Provenance Explorer page — compact selection + detail (Phase 11D)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from stockballdb.explorer.services import provenance as prov_service
from stockballdb.explorer.ui.components import dataframe_dense, kv_table, page_header, section_heading


def render() -> None:
    page_header("Provenance", "Build-level provenance — not row-level snapshot lineage.", icon="◷")
    manifests = prov_service.list_manifests()
    runs = prov_service.list_run_reports()

    left, right = st.columns(2)
    with left:
        section_heading("Manifests (newest first)")
        readable = [m for m in manifests[:40] if not m.error]
        unreadable = [m for m in manifests[:40] if m.error]
        for bad in unreadable[:5]:
            st.warning(f"{bad.artifact_id} — unreadable: {bad.error}")
        if not readable:
            st.caption("No readable manifests.")
        else:
            labels = [m.artifact_id for m in readable]
            choice = st.selectbox("Select manifest", options=labels, key="prov_manifest_sel")
            selected = next(m for m in readable if m.artifact_id == choice)
            st.session_state["manifest_path"] = str(selected.path)
            man_rows = [
                {
                    "id": m.artifact_id,
                    "started": str(m.started_at or "—"),
                }
                for m in readable[:20]
            ]
            dataframe_dense(man_rows, height=240)

    with right:
        section_heading("Operational runs (newest first)")
        run_rows = []
        for rec in runs[:20]:
            if rec.error:
                run_rows.append({"id": rec.artifact_id, "status": "ERROR", "detail": rec.error})
                continue
            payload = rec.payload or {}
            run_rows.append(
                {
                    "id": rec.artifact_id,
                    "status": payload.get("status"),
                    "detail": payload.get("failure_kind")
                    or payload.get("change_classification")
                    or "—",
                }
            )
        if run_rows:
            dataframe_dense(run_rows, height=320)
        else:
            st.caption("No run reports.")

    path_str = st.session_state.get("manifest_path")
    if not path_str:
        return

    try:
        detail = prov_service.manifest_detail(Path(path_str))
    except Exception as exc:
        st.error(f"Manifest detail failed: {exc}")
        return

    section_heading("Selected manifest detail")
    classification = detail.get("classification") if isinstance(detail.get("classification"), dict) else {}
    git = detail.get("git") if isinstance(detail.get("git"), dict) else {}
    providers = detail.get("providers") if isinstance(detail.get("providers"), dict) else detail.get("provider")

    c1, c2, c3 = st.columns(3)
    with c1:
        kv_table(
            {
                "build_id": detail.get("build_id"),
                "schema_version": detail.get("schema_version") or detail.get("manifest_schema_version"),
                "started_at": detail.get("build_started_at") or detail.get("started_at"),
                "finished_at": detail.get("build_finished_at") or detail.get("finished_at"),
            },
            title="Build",
        )
    with c2:
        fp = detail.get("database_fingerprint")
        kv_table(
            {
                "database_fingerprint": fp if isinstance(fp, str) else (fp or {}),
                "exact_rebuild_capable": classification.get("exact_rebuild_capable"),
                "alembic_head": detail.get("alembic_head") or git.get("alembic_head"),
            },
            title="Database / rebuild",
        )
    with c3:
        kv_table(
            {
                "git_commit": git.get("commit") or detail.get("git_commit"),
                "git_dirty": git.get("dirty"),
                "providers": providers,
            },
            title="Git / providers",
        )

    snaps = prov_service.snapshot_metadata_list(detail)
    st.caption(f"Snapshots referenced: {len(snaps)}")
    if snaps:
        dataframe_dense(snaps[:50], height=260)

    with st.expander("Raw manifest (filtered)"):
        st.json(
            {
                k: v
                for k, v in detail.items()
                if k not in {"snapshots", "stages", "datasets", "table_fingerprints"}
            }
        )

"""Validation Center page — compact action bar (Phase 11D)."""

from __future__ import annotations

import streamlit as st

from stockballdb.explorer.artifacts import discover_manifests
from stockballdb.explorer.db import get_explorer_engine
from stockballdb.explorer.services import validation as val_service
from stockballdb.explorer.ui.components import page_header, panel, section_heading, status_badge


def render() -> None:
    page_header("Validation", "On-demand read-only validation — does not mutate the database.", icon="☑")
    engine = get_explorer_engine()

    with panel():
        b1, b2, b3, b4 = st.columns(4, gap="small")
        run_health = b1.button("Run Health", type="primary", width="stretch")
        run_v1 = b2.button("Run validate_v1", width="stretch")
        run_fp = b3.button("Compute Fingerprint", width="stretch")
        run_ver = b4.button("Verify Latest Manifest", width="stretch")

    if run_health:
        try:
            report = val_service.run_health_check(engine)
            st.session_state["val_health"] = val_service.health_as_dict(report)
        except Exception as exc:
            st.error(f"Health failed: {exc}")

    if run_v1:
        try:
            result = val_service.run_validate_v1(engine)
            st.session_state["val_v1"] = result
        except Exception as exc:
            st.error(f"validate_v1 failed: {exc}")

    if run_fp:
        try:
            fp = val_service.run_fingerprint(engine)
            st.session_state["val_fp"] = fp.as_dict()
        except Exception as exc:
            st.error(f"Fingerprint failed: {exc}")

    if run_ver:
        manifests = discover_manifests()
        latest = next((m for m in manifests if m.payload and not m.error), None)
        if not latest:
            st.warning("No readable manifest found.")
        else:
            try:
                rep = val_service.verify_manifest_file(latest.path)
                st.session_state["val_verify"] = {
                    "manifest": latest.artifact_id,
                    "checked": rep.checked,
                    "missing": rep.missing,
                    "corrupt": rep.corrupt,
                    "ok": rep.ok,
                }
            except Exception as exc:
                st.error(f"Verify failed: {exc}")

    if "val_health" in st.session_state:
        section_heading("Health")
        h = st.session_state["val_health"]
        status = h.get("status") or h.get("health_status") or "—"
        kind = "ok" if str(status).upper() == "HEALTHY" else ("warn" if "WARN" in str(status).upper() else "bad")
        st.markdown(f"{status_badge(kind, str(status))}", unsafe_allow_html=True)
        with st.expander("Health details (raw)"):
            st.json(h)

    if "val_v1" in st.session_state:
        section_heading("validate_v1")
        r = st.session_state["val_v1"]
        kind = "ok" if r.passed else "bad"
        st.markdown(
            f"{status_badge(kind, 'PASS' if r.passed else 'FAIL')}",
            unsafe_allow_html=True,
        )
        if r.error:
            st.error(r.error)
        with st.expander("Diagnostics", expanded=not r.passed):
            for line in r.diagnostics[:40]:
                st.text(line)

    if "val_fp" in st.session_state:
        section_heading("Fingerprint")
        fp = st.session_state["val_fp"]
        st.code(fp.get("database_fingerprint") or fp)
        with st.expander("Fingerprint details (raw)"):
            st.json(fp)

    if "val_verify" in st.session_state:
        section_heading("Snapshot verification")
        v = st.session_state["val_verify"]
        kind = "ok" if v.get("ok") else "bad"
        st.markdown(
            f"{status_badge(kind, 'PASS' if v.get('ok') else 'FAIL')} "
            f"checked={v.get('checked')} missing={v.get('missing')} corrupt={v.get('corrupt')}"
            + (f" · manifest `{v.get('manifest')}`" if v.get("manifest") else ""),
            unsafe_allow_html=True,
        )
        with st.expander("Verify details (raw)"):
            st.json(v)

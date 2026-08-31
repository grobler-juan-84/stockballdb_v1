"""Validation Center page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from stockballdb.explorer.artifacts import discover_manifests
from stockballdb.explorer.db import get_explorer_engine
from stockballdb.explorer.services import validation as val_service


def render() -> None:
    st.caption("On-demand read-only validation — does not mutate the database.")
    engine = get_explorer_engine()

    if st.button("Run health", type="primary"):
        try:
            report = val_service.run_health_check(engine)
            st.session_state["val_health"] = val_service.health_as_dict(report)
        except Exception as exc:
            st.error(f"Health failed: {exc}")

    if st.button("Run validate_v1"):
        try:
            result = val_service.run_validate_v1(engine)
            st.session_state["val_v1"] = result
        except Exception as exc:
            st.error(f"validate_v1 failed: {exc}")

    if st.button("Compute fingerprint"):
        try:
            fp = val_service.run_fingerprint(engine)
            st.session_state["val_fp"] = fp.as_dict()
        except Exception as exc:
            st.error(f"Fingerprint failed: {exc}")

    if st.button("Verify latest manifest"):
        manifests = discover_manifests()
        latest = next((m for m in manifests if m.payload and not m.error), None)
        if not latest:
            st.warning("No readable manifest found.")
        else:
            try:
                rep = val_service.verify_manifest_file(latest.path)
                st.session_state["val_verify"] = {
                    "checked": rep.checked,
                    "missing": rep.missing,
                    "corrupt": rep.corrupt,
                    "ok": rep.ok,
                }
            except Exception as exc:
                st.error(f"Verify failed: {exc}")

    if "val_health" in st.session_state:
        st.subheader("Health")
        st.json(st.session_state["val_health"])

    if "val_v1" in st.session_state:
        st.subheader("validate_v1")
        r = st.session_state["val_v1"]
        st.write("PASS" if r.passed else "FAIL")
        if r.error:
            st.error(r.error)
        for line in r.diagnostics[:30]:
            st.text(line)

    if "val_fp" in st.session_state:
        st.subheader("Fingerprint")
        st.json(st.session_state["val_fp"])

    if "val_verify" in st.session_state:
        st.subheader("Snapshot verification")
        st.json(st.session_state["val_verify"])

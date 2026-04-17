from __future__ import annotations

from src.ui._compat import st
from src.ui.api_client import api_get, api_post_form, api_post_multipart
from src.ui.components.image_viewer import render_capture_pair
from src.ui.components.result_card import render_overall_result, render_side_result

st.title("Runtime Inspection")

# ── Config bar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Config")
    base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")
    template_id = st.text_input("Template ID", value="")
    scan_job_id = st.text_input("Scan Job ID", value="JOB_001")
    live_mode = st.toggle("Live Camera Mode", value=False)
    st.caption("Live mode: chụp từ camera thật qua /live routes")

st.divider()

# ── Side 1 ────────────────────────────────────────────────────────────────────
st.subheader("Side 1")

if live_mode:
    if st.button("Capture & Inspect Side1 (Live)", type="primary"):
        resp = api_post_form(
            base_url,
            "/inspection/side1/live",
            {"scan_job_id": scan_job_id, "template_id": template_id},
        )
        st.session_state["side1_result"] = resp
else:
    with st.form("side1-upload"):
        col1, col2 = st.columns(2)
        with col1:
            s1_cam1 = st.file_uploader("Cam1 image", key="s1c1")
        with col2:
            s1_cam2 = st.file_uploader("Cam2 image", key="s1c2")
        submit_s1 = st.form_submit_button("Inspect Side1")

    if submit_s1:
        if not (s1_cam1 and s1_cam2):
            st.error("Cần upload cả cam1 và cam2.")
        else:
            resp = api_post_multipart(
                base_url,
                "/inspection/side1",
                data={"scan_job_id": scan_job_id, "template_id": template_id},
                files={
                    "cam1_file": (s1_cam1.name, s1_cam1.getvalue(), s1_cam1.type or "image/png"),
                    "cam2_file": (s1_cam2.name, s1_cam2.getvalue(), s1_cam2.type or "image/png"),
                },
            )
            st.session_state["side1_result"] = resp

side1_result = st.session_state.get("side1_result")
if side1_result:
    render_side_result(side1_result, "Side1")
    render_capture_pair(side1_result, "Side1")

st.divider()

# ── Confirm Side2 ─────────────────────────────────────────────────────────────
st.subheader("Xác nhận chuyển mặt 2")
confirm_disabled = side1_result is None
if st.button("Xác nhận chuyển mặt 2", disabled=confirm_disabled, type="primary"):
    resp = api_post_form(base_url, f"/inspection/{scan_job_id}/confirm-side2", {})
    st.session_state["side2_confirmed"] = True
    st.success(f"Confirmed — state: {resp.get('state')}")

if confirm_disabled:
    st.caption("Nút sẽ mở sau khi Side1 hoàn thành.")

st.divider()

# ── Side 2 ────────────────────────────────────────────────────────────────────
st.subheader("Side 2")
side2_ready = st.session_state.get("side2_confirmed", False)

if not side2_ready:
    st.info("Chờ xác nhận chuyển mặt 2.")
else:
    if live_mode:
        if st.button("Capture & Inspect Side2 (Live)", type="primary"):
            resp = api_post_form(
                base_url,
                "/inspection/side2/live",
                {"scan_job_id": scan_job_id, "template_id": template_id},
            )
            st.session_state["side2_result"] = resp
    else:
        with st.form("side2-upload"):
            col1, col2 = st.columns(2)
            with col1:
                s2_cam1 = st.file_uploader("Cam1 image", key="s2c1")
            with col2:
                s2_cam2 = st.file_uploader("Cam2 image", key="s2c2")
            submit_s2 = st.form_submit_button("Inspect Side2")

        if submit_s2:
            if not (s2_cam1 and s2_cam2):
                st.error("Cần upload cả cam1 và cam2.")
            else:
                resp = api_post_multipart(
                    base_url,
                    "/inspection/side2",
                    data={"scan_job_id": scan_job_id, "template_id": template_id},
                    files={
                        "cam1_file": (s2_cam1.name, s2_cam1.getvalue(), s2_cam1.type or "image/png"),
                        "cam2_file": (s2_cam2.name, s2_cam2.getvalue(), s2_cam2.type or "image/png"),
                    },
                )
                st.session_state["side2_result"] = resp

side2_result = st.session_state.get("side2_result")
if side2_result:
    render_side_result(side2_result, "Side2")
    render_capture_pair(side2_result, "Side2")

st.divider()

# ── Overall ───────────────────────────────────────────────────────────────────
st.subheader("Overall Result")
if st.button("Load Final Result") and side2_result:
    st.session_state["overall_result"] = api_get(
        base_url, f"/inspection/{scan_job_id}/result"
    )

overall = st.session_state.get("overall_result")
if overall:
    render_overall_result(overall)
    with st.expander("Raw JSON"):
        st.json(overall)

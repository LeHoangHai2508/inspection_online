from __future__ import annotations

from src.ui._compat import st
from src.ui.api_client import api_get
from src.ui.components.filters import apply_job_filters, render_job_filters
from src.ui.components.image_viewer import render_capture_pair
from src.ui.components.result_card import render_overall_result, render_side_result

st.title("Bad Cases")
st.caption("Lọc và xem lại các lần kiểm NG / UNCERTAIN.")

with st.sidebar:
    base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")

# ── Filters ───────────────────────────────────────────────────────────────────
filters = render_job_filters()
# Force only NG / UNCERTAIN
if filters["status"] == "OK" or filters["status"] is None:
    filters["status"] = None  # show NG + UNCERTAIN both

if st.button("Load Bad Cases"):
    raw = api_get(base_url, f"/results/?limit={filters['limit'] * 3}")
    if isinstance(raw, list):
        # keep only NG / UNCERTAIN
        bad = [j for j in raw if j.get("overall_status") in ("NG", "UNCERTAIN")]
        bad = apply_job_filters(bad, {**filters, "status": None})
        st.session_state["bad_cases"] = bad
    else:
        st.session_state["bad_cases"] = []

cases = st.session_state.get("bad_cases", [])
if not cases:
    st.info("Không có bad case nào hoặc chưa load.")
else:
    st.markdown(f"**{len(cases)} case(s) found**")
    for job in cases:
        job_id = job.get("scan_job_id", "—")
        tpl = job.get("template_id", "—")
        status = job.get("overall_status", "—")
        icon = "🔴" if status == "NG" else "🟡"
        with st.expander(f"{icon} {job_id} | {tpl} | {status}"):
            # Load full result on demand
            if st.button("Load Detail", key=f"detail_{job_id}"):
                try:
                    detail = api_get(base_url, f"/results/{job_id}")
                    st.session_state[f"detail_{job_id}"] = detail
                except Exception as exc:
                    st.error(str(exc))

            detail = st.session_state.get(f"detail_{job_id}")
            if detail:
                render_overall_result(detail)
                s1 = detail.get("side1_result") or {}
                s2 = detail.get("side2_result") or {}
                render_side_result(s1, "Side1")
                render_capture_pair(s1, "Side1")
                render_side_result(s2, "Side2")
                render_capture_pair(s2, "Side2")

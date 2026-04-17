from __future__ import annotations

from src.ui._compat import st
from src.ui.api_client import api_get
from src.ui.components.filters import apply_job_filters, render_job_filters
from src.ui.components.image_viewer import render_capture_pair
from src.ui.components.result_card import render_overall_result, render_side_result

st.title("Inspection History")

with st.sidebar:
    base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")

filters = render_job_filters()

if st.button("Load History"):
    raw = api_get(base_url, f"/counter/recent?limit={filters['limit']}")
    jobs = raw if isinstance(raw, list) else []
    st.session_state["history_jobs"] = apply_job_filters(jobs, filters)

jobs: list[dict] = st.session_state.get("history_jobs", [])
if not jobs:
    st.info("Nhấn Load History để tải dữ liệu.")
else:
    display_cols = ["scan_job_id", "template_id", "line_id", "overall_status", "operator_action_required", "created_at"]
    st.dataframe(
        [{c: j.get(c, "") for c in display_cols} for j in jobs],
        use_container_width=True,
    )

    st.divider()
    st.subheader("Chi tiết")
    job_id = st.text_input("Nhập Scan Job ID để xem chi tiết", value="")
    if st.button("Load Detail") and job_id:
        try:
            st.session_state["history_detail"] = api_get(base_url, f"/results/{job_id}")
        except Exception as exc:
            st.error(str(exc))

    detail = st.session_state.get("history_detail")
    if detail:
        render_overall_result(detail)
        s1 = detail.get("side1_result") or {}
        s2 = detail.get("side2_result") or {}
        render_side_result(s1, "Side1")
        render_capture_pair(s1, "Side1")
        render_side_result(s2, "Side2")
        render_capture_pair(s2, "Side2")
        with st.expander("Raw JSON"):
            st.json(detail)

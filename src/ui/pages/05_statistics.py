from __future__ import annotations

from collections import Counter

from src.ui._compat import st
from src.ui.api_client import api_get

st.title("Statistics")
st.caption("Thống kê tổng hợp kết quả kiểm tra.")

with st.sidebar:
    base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")

if st.button("Refresh"):
    try:
        st.session_state["summary"] = api_get(base_url, "/counter/summary")
        st.session_state["recent"] = api_get(base_url, "/counter/recent?limit=200")
    except Exception as exc:
        st.error(str(exc))

summary = st.session_state.get("summary")
recent: list[dict] = st.session_state.get("recent") or []

# ── KPI cards ─────────────────────────────────────────────────────────────────
if summary:
    total = summary.get("total", 0)
    ok = summary.get("ok", 0)
    ng = summary.get("ng", 0)
    uncertain = summary.get("uncertain", 0)
    error_rate = summary.get("error_rate_pct", 0.0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("OK", ok)
    c3.metric("NG", ng)
    c4.metric("UNCERTAIN", uncertain)
    c5.metric("Error Rate", f"{error_rate:.1f}%")

st.divider()

# ── Error breakdown by field ───────────────────────────────────────────────────
if recent:
    field_errors: Counter = Counter()
    template_ng: Counter = Counter()
    for job in recent:
        tpl = job.get("template_id", "unknown")
        status = job.get("overall_status")
        if status in ("NG", "UNCERTAIN"):
            template_ng[tpl] += 1

    st.subheader("NG / UNCERTAIN by Template")
    if template_ng:
        rows = [{"template_id": k, "ng_count": v} for k, v in template_ng.most_common(20)]
        st.table(rows)
    else:
        st.info("Không có NG/UNCERTAIN nào.")

    st.subheader("Recent Jobs")
    display_cols = ["scan_job_id", "template_id", "overall_status", "operator_action_required", "created_at"]
    table_rows = [{c: j.get(c, "") for c in display_cols} for j in recent[:50]]
    st.dataframe(table_rows, use_container_width=True)
else:
    st.info("Nhấn Refresh để tải dữ liệu.")

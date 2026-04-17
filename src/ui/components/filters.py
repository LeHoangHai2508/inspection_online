from __future__ import annotations

from src.ui._compat import st


def render_job_filters() -> dict:
    """Render filter widgets and return the selected filter values."""
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=["All", "OK", "NG", "UNCERTAIN"],
            index=0,
        )
    with col2:
        template_filter = st.text_input("Template ID contains", value="")
    with col3:
        limit = st.number_input("Max rows", min_value=1, max_value=200, value=20)

    return {
        "status": None if status_filter == "All" else status_filter,
        "template_id": template_filter.strip() or None,
        "limit": int(limit),
    }


def apply_job_filters(jobs: list[dict], filters: dict) -> list[dict]:
    result = jobs
    if filters.get("status"):
        result = [j for j in result if j.get("overall_status") == filters["status"]]
    if filters.get("template_id"):
        q = filters["template_id"].lower()
        result = [j for j in result if q in (j.get("template_id") or "").lower()]
    return result[: filters.get("limit", 20)]

from __future__ import annotations

from src.ui._compat import st

_STATUS_COLOR = {"OK": "🟢", "NG": "🔴", "UNCERTAIN": "🟡"}
_SEVERITY_COLOR = {"critical": "🔴", "major": "🟠", "minor": "🟡"}


def render_side_result(result: dict, title: str) -> None:
    """Render one side inspection result (side1 or side2)."""
    if not result:
        return
    status = result.get("status", "—")
    icon = _STATUS_COLOR.get(status, "⚪")
    st.markdown(f"**{title}** — {icon} `{status}`")

    proc_ms = result.get("processing_time_ms")
    if proc_ms is not None:
        st.caption(f"Processing time: {proc_ms} ms")

    raw_text = result.get("raw_text", "")
    if raw_text:
        with st.expander("OCR Text"):
            st.text(raw_text)

    errors = result.get("errors") or []
    if errors:
        st.markdown(f"**Errors ({len(errors)})**")
        for err in errors:
            sev = err.get("severity", "")
            sev_icon = _SEVERITY_COLOR.get(sev, "⚪")
            field = err.get("field_name") or err.get("field", "—")
            etype = err.get("error_type", "—")
            expected = err.get("expected_value", "")
            actual = err.get("actual_value", "")
            st.markdown(
                f"- {sev_icon} `{field}` — **{etype}**"
                + (f"  expected: `{expected}` → actual: `{actual}`" if expected or actual else "")
            )
    else:
        st.success("No errors.")


def render_overall_result(result: dict) -> None:
    """Render the overall inspection result panel."""
    if not result:
        return
    status = result.get("overall_status", "—")
    icon = _STATUS_COLOR.get(status, "⚪")
    action = result.get("operator_action_required", "—")
    severity = result.get("highest_severity", "—")

    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Status", f"{icon} {status}")
    col2.metric("Operator Action", action)
    col3.metric("Highest Severity", severity)

    iot = result.get("publish_to_iot")
    if iot is not None:
        st.caption(f"IoT publish: {'✓ sent' if iot else '✗ not sent'}")

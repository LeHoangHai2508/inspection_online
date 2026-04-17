from __future__ import annotations

from src.ui._compat import st
from src.ui.api_client import api_get, api_post_form, api_post_multipart, api_put_json
from src.ui.components.image_viewer import render_capture_pair

st.title("Template Upload / Review")

base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")

# ── Upload ────────────────────────────────────────────────────────────────────
st.subheader("1. Upload Template")
with st.form("template-upload"):
    col1, col2 = st.columns(2)
    with col1:
        template_name = st.text_input("Template Name", value="")
        product_code = st.text_input("Product Code", value="")
        created_by = st.text_input("Created By", value="operator_01")
    with col2:
        side1_file = st.file_uploader("Side1 File (image/PDF)")
        side2_file = st.file_uploader("Side2 File (image/PDF)")
    submit_upload = st.form_submit_button("Upload")

if submit_upload:
    if not (template_name and product_code and side1_file and side2_file):
        st.error("Điền đủ Template Name, Product Code và 2 file.")
    else:
        resp = api_post_multipart(
            base_url,
            "/templates/upload",
            data={"template_name": template_name, "product_code": product_code, "created_by": created_by},
            files={
                "side1_file": (side1_file.name, side1_file.getvalue(), side1_file.type or "application/octet-stream"),
                "side2_file": (side2_file.name, side2_file.getvalue(), side2_file.type or "application/octet-stream"),
            },
        )
        st.session_state["tpl_id"] = resp.get("template_id", "")
        st.success(f"Uploaded → template_id: `{st.session_state['tpl_id']}`")

# ── Load Preview ──────────────────────────────────────────────────────────────
st.subheader("2. Review Template")
tpl_id = st.text_input("Template ID", value=st.session_state.get("tpl_id", ""))

if st.button("Load Preview") and tpl_id:
    st.session_state["preview"] = api_get(base_url, f"/templates/{tpl_id}/preview")

preview = st.session_state.get("preview")
if preview:
    status = preview.get("status", "")
    st.caption(f"Status: `{status}`")

    # OCR text
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Side1 OCR Text**")
        st.text(preview.get("side1_raw_text", "") or "(empty)")
    with col_r:
        st.markdown("**Side2 OCR Text**")
        st.text(preview.get("side2_raw_text", "") or "(empty)")

    # Unmapped / low-confidence blocks
    unmapped = preview.get("unmapped_blocks", {})
    low_conf = preview.get("low_confidence_blocks", {})
    for side_key in ("side1", "side2"):
        ub = unmapped.get(side_key, [])
        lc = low_conf.get(side_key, [])
        if ub:
            st.warning(f"{side_key}: {len(ub)} unmapped block(s) — {[b['text'][:40] for b in ub]}")
        if lc:
            st.warning(f"{side_key}: {len(lc)} low-confidence block(s)")

    # ── Field editor (form/table, not raw JSON) ───────────────────────────────
    st.subheader("3. Edit Fields")
    fields_by_side = preview.get("fields_by_side", {"side1": [], "side2": []})
    all_fields: list[dict] = []
    for side_key in ("side1", "side2"):
        for f in fields_by_side.get(side_key, []):
            all_fields.append({**f, "side": side_key})

    # Seed session state once
    if "edit_fields" not in st.session_state or st.button("Reset Fields from Preview"):
        st.session_state["edit_fields"] = all_fields.copy()

    edited: list[dict] = []
    for i, field in enumerate(st.session_state["edit_fields"]):
        with st.expander(f"{field.get('side','?')} / {field.get('field_name','field_' + str(i))}", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                fn = st.text_input("field_name", value=field.get("field_name", ""), key=f"fn_{i}")
                ev = st.text_input("expected_value", value=field.get("expected_value", ""), key=f"ev_{i}")
            with c2:
                ct = st.selectbox(
                    "compare_type",
                    options=["exact", "regex", "fuzzy", "symbol_match"],
                    index=["exact", "regex", "fuzzy", "symbol_match"].index(field.get("compare_type", "exact")),
                    key=f"ct_{i}",
                )
                pr = st.selectbox(
                    "priority",
                    options=["critical", "major", "minor"],
                    index=["critical", "major", "minor"].index(field.get("priority", "major")),
                    key=f"pr_{i}",
                )
            with c3:
                req = st.checkbox("required", value=field.get("required", True), key=f"req_{i}")
                side_val = st.selectbox(
                    "side",
                    options=["side1", "side2"],
                    index=0 if field.get("side") == "side1" else 1,
                    key=f"sd_{i}",
                )
            edited.append({
                "side": side_val,
                "field_name": fn,
                "expected_value": ev,
                "field_type": field.get("field_type", "text"),
                "required": req,
                "compare_type": ct,
                "priority": pr,
            })

    if st.button("Add Field"):
        st.session_state["edit_fields"].append({
            "side": "side1", "field_name": "", "expected_value": "",
            "field_type": "text", "required": True,
            "compare_type": "exact", "priority": "major",
        })
        st.experimental_rerun()

    if st.button("Save Fields") and tpl_id:
        resp = api_put_json(
            base_url,
            f"/templates/{tpl_id}/fields",
            {"fields": edited, "review_notes": "reviewed via UI form"},
        )
        st.success("Fields saved.")
        st.session_state["preview"] = api_get(base_url, f"/templates/{tpl_id}/preview")

# ── Approve / Reject ──────────────────────────────────────────────────────────
st.subheader("4. Approve / Reject")
with st.form("approve-form"):
    approved_by = st.text_input("Approved By", value="reviewer_01")
    col_a, col_b = st.columns(2)
    with col_a:
        do_approve = st.form_submit_button("Approve Template")
    with col_b:
        do_reject = st.form_submit_button("Reject Template")

if do_approve and tpl_id:
    resp = api_post_form(base_url, f"/templates/{tpl_id}/approve", {"approved_by": approved_by})
    st.success(f"Approved — status: {resp.get('status')}")

if do_reject and tpl_id:
    resp = api_post_form(base_url, f"/templates/{tpl_id}/reject", {"rejected_by": approved_by})
    st.warning(f"Rejected — status: {resp.get('status')}")

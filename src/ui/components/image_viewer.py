from __future__ import annotations

from src.ui._compat import st


def render_capture_pair(result: dict, label: str) -> None:
    """Show cam1 / cam2 annotated images from a side result dict."""
    if not result:
        return
    assets = result.get("annotated_assets") or {}
    cam1_path = assets.get("cam1")
    cam2_path = assets.get("cam2")

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"{label} — Cam1")
        if cam1_path:
            try:
                with open(cam1_path, "rb") as f:
                    st.image(f.read(), use_column_width=True)
            except OSError:
                st.info(f"Image not found: {cam1_path}")
        else:
            st.info("No cam1 image.")

    with col2:
        st.caption(f"{label} — Cam2")
        if cam2_path:
            try:
                with open(cam2_path, "rb") as f:
                    st.image(f.read(), use_column_width=True)
            except OSError:
                st.info(f"Image not found: {cam2_path}")
        else:
            st.info("No cam2 image.")

from __future__ import annotations

from src.ui._compat import st

st.set_page_config(page_title="Garment Label Inspection", layout="wide")
st.title("Garment Label Inspection")
st.write(
    "UI scaffold cho 3 luồng chính: template review, runtime inspection và history."
)
st.info(
    "Trong môi trường local chưa cài Streamlit, file này vẫn được giữ import-safe để repo không gãy."
)

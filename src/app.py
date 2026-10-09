"""Retail floor intelligence. No facial recognition."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.retail_features import detect_persons_yolo, dwell_heatmap, queue_wait_estimate, shelf_occupancy, shopper_count_series
from src.ui_theme import theme_css

@st.cache_data
def _detect():
    info = detect_persons_yolo(None)
    return info["backend"], info["frame_counts"]

def main() -> None:
    st.set_page_config(page_title="Retail intelligence", layout="wide")
    st.markdown(theme_css("#e2b15a"), unsafe_allow_html=True)
    backend, counts = _detect()
    series = shopper_count_series(counts)
    heat = dwell_heatmap(counts)
    peak = int(series["persons"].max()) if len(series) else 0
    queue = queue_wait_estimate(max(peak - 1, 0))
    shelves = shelf_occupancy({"aisle-a-milk": 0.72, "aisle-b-bread": 0.18, "aisle-c-produce": 0.41, "checkout-snacks": 0.09})
    st.markdown(f'<div class="top"><div><div class="kicker">Store overview</div><p class="title">{peak} people in the busiest frame</p></div><div class="pill">{backend} detector · no faces stored</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Frames", len(counts))
    c2.metric("Est. wait", f'{queue["est_wait_minutes"]} min')
    c3.metric("Low shelves", sum(1 for s in shelves if s["low_stock"]))
    fig = go.Figure(go.Bar(x=series["frame"], y=series["persons"], marker_color="#e2b15a"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf3", height=280, title="Shoppers by frame")
    st.plotly_chart(fig, width="stretch")
    left, right = st.columns(2)
    with left:
        hm = px.imshow(heat, color_continuous_scale="YlOrRd", title="Relative dwell")
        hm.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e7ecf3", height=360)
        st.plotly_chart(hm, width="stretch")
        if queue["alert"]:
            st.warning(queue["message"])
        else:
            st.success(queue["message"])
    with right:
        st.markdown("### Inventory")
        st.dataframe(shelves, hide_index=True, width="stretch")
        st.caption("Shelf levels are a demo inventory table, not a camera measurement.")

if __name__ == "__main__":
    main()

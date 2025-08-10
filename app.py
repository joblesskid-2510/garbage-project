
import os
import io
import numpy as np
import rasterio
from rasterio.transform import xy
import streamlit as st
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Trash Change Dashboard", layout="wide")

st.title("🗺️ Trash Detection & Change Dashboard")
st.markdown("Visualize Sentinel‑2 trash masks for multiple time windows and see **new/cleaned** areas.")

# ---------------------- Sidebar: path + file selection ----------------------
st.sidebar.header("📂 Data Source")
default_base = st.session_state.get("base_path", "/content/drive/My Drive/GEE_Images")
base_path = st.sidebar.text_input("Folder with your GeoTIFFs (.tif)", value=default_base)
st.session_state["base_path"] = base_path

if not os.path.exists(base_path):
    st.warning(f"Path does not exist: {base_path}")
    st.stop()

tifs = sorted([f for f in os.listdir(base_path) if f.lower().endswith(".tif")])
if not tifs:
    st.warning("No .tif files found in the folder.")
    st.stop()

st.sidebar.write("**Found files:**")
for f in tifs:
    st.sidebar.caption(f"• {f}")

# Helper to pick files by keyword default
def guess_file(keyword):
    for f in tifs:
        if keyword in f.lower():
            return f
    return None

st.sidebar.header("🕒 Pick time windows")
five_y = st.sidebar.selectbox("5-year mask", options=["(none)"] + tifs, index=(tifs.index(guess_file("5y"))+1 if guess_file("5y") in tifs else 0))
two_y  = st.sidebar.selectbox("2-year mask", options=["(none)"] + tifs, index=(tifs.index(guess_file("2y"))+1 if guess_file("2y") in tifs else 0))
three_m = st.sidebar.selectbox("3-month mask", options=["(none)"] + tifs, index=(tifs.index(guess_file("3m"))+1 if guess_file("3m") in tifs else 0))

# Load mask utility
@st.cache_data(show_spinner=False)
def load_mask(path):
    src = rasterio.open(path)
    arr = src.read(1)
    return arr, src.transform, src.bounds

def show_mask_image(arr, title, cmap):
    fig, ax = plt.subplots(figsize=(5,5))
    ax.imshow(arr, cmap=cmap)
    ax.set_title(title)
    ax.axis("off")
    st.pyplot(fig)
    plt.close(fig)

# Convert boolean mask to lat/lon points (subsample for responsiveness)
def mask_to_points(mask, transform, step=8, max_points=50000):
    rows, cols = mask.shape
    pts = []
    count = 0
    for r in range(0, rows, step):
        row_slice = mask[r, ::step]
        if not row_slice.any():
            continue
        for c in range(0, cols, step):
            if mask[r, c]:
                x, y = xy(transform, r, c)  # lon, lat
                pts.append((y, x))
                count += 1
                if count >= max_points:
                    return pts
    return pts

def points_to_dataframe(points):
    if not points:
        return pd.DataFrame(columns=["latitude","longitude"])
    lat, lon = zip(*points)
    return pd.DataFrame({"latitude": lat, "longitude": lon})

# Load selected masks
loaded = {}
for label, fname in [("5y", five_y), ("2y", two_y), ("3m", three_m)]:
    if fname != "(none)":
        arr, transform, bounds = load_mask(os.path.join(base_path, fname))
        loaded[label] = {"arr": arr, "transform": transform, "bounds": bounds, "name": fname}

# Show selected masks
cols = st.columns(3)
for i, key in enumerate(["5y","2y","3m"]):
    if key in loaded:
        with cols[i]:
            show_mask_image(loaded[key]["arr"], f"Mask — {key} ({loaded[key]['name']})", cmap=("Reds" if key=="5y" else "Blues" if key=="2y" else "Greens"))

# Change computations
st.header("🔁 Change Detection")
st.caption("New trash = 0 → 1, Cleaned = 1 → 0")

def compute_changes(a, b):
    return (a==0) & (b>0), (a>0) & (b==0)

pairs = []
if "5y" in loaded and "2y" in loaded:
    pairs.append(("5y → 2y", "5y", "2y"))
if "2y" in loaded and "3m" in loaded:
    pairs.append(("2y → 3m", "2y", "3m"))

for title, a_key, b_key in pairs:
    a = loaded[a_key]["arr"]
    b = loaded[b_key]["arr"]
    t = loaded[b_key]["transform"]  # use newer transform
    if a.shape != b.shape:
        st.error(f"Shape mismatch for {title}: {a.shape} vs {b.shape}. Ensure same export region/scale.")
        continue
    new_mask, cleaned_mask = compute_changes(a, b)

    c1, c2 = st.columns(2)
    with c1:
        show_mask_image(new_mask, f"NEW Trash ({title})", cmap="gray")
    with c2:
        show_mask_image(cleaned_mask, f"CLEANED ({title})", cmap="gray")

    # Points + map
    st.subheader(f"🗺️ Map — {title}")
    step = st.slider(f"Sampling step for markers — {title}", min_value=4, max_value=32, value=8, step=2)
    max_pts = st.number_input(f"Max points — {title}", min_value=1000, max_value=200000, value=50000, step=1000)
    which = st.radio(f"Show which layer on map — {title}", ["NEW", "CLEANED"], horizontal=True, index=0, key=f"mapopt_{title}")
    use_mask = new_mask if which=="NEW" else cleaned_mask
    color = "red" if which=="NEW" else "green"
    pts = mask_to_points(use_mask, t, step=step, max_points=int(max_pts))

    # Center map around bounds
    b = loaded[b_key]["bounds"]
    center_lat = (b.top + b.bottom)/2.0
    center_lon = (b.left + b.right)/2.0
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    for (lat, lon) in pts:
        folium.CircleMarker(location=[lat, lon], radius=2, color=color, fill=True).add_to(fmap)

    st_data = st_folium(fmap, height=500, width=None)

    # Downloads
    st.markdown("**Downloads**")
    df = points_to_dataframe(pts)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(f"⬇️ Download {which} points CSV — {title}", data=csv_bytes,
                       file_name=f"{which.lower()}_{title.replace(' ','_')}_points.csv",
                       mime="text/csv")

st.info("Tip: Keep the same *region* and *scale* in Earth Engine exports so rasters align.")

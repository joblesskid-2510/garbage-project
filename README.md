
# Trash Change Dashboard

Streamlit app to visualize Sentinel-2 trash masks for multiple time windows (5y / 2y / 3m), compute **NEW** and **CLEANED** areas, explore them on an interactive Folium map with clustering, and export CSV/GeoJSON.

## 📦 Folder Structure
```
trash-change-dashboard/
├─ app.py
├─ requirements.txt
└─ README.md
```

## 🚀 Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Then in the app sidebar set your data folder path, e.g.:
```
/content/drive/My Drive/GEE_Images
```

## ☁️ Deploy on Streamlit Community Cloud
1. Create a new GitHub repo (e.g., `trash-change-dashboard`) and push these files.
2. Go to https://share.streamlit.io
3. Connect GitHub, pick your repo + branch + `app.py` as entry point.
4. Add the app secret `MAPBOX_TOKEN` only if you ever switch to Mapbox tiles (optional).
5. Click **Deploy**.

## 📂 Data requirements
Export your masks from Google Earth Engine with **identical region & scale (10m)** so rasters align:
- `trash_mask_5y.tif`
- `trash_mask_2y.tif`
- `trash_mask_3m.tif`
Optionally an RGB `.tif` for overlay.

## 🧭 Tips
- Adjust thresholds in GEE if the mask is too sparse/dense.
- Increase the sampling step in the map if it feels slow (defaults to 8).
- Use the GeoJSON export for loading into QGIS or other GIS tools.

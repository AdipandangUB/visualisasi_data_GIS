import os
import tempfile
import zipfile
import shutil
import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd

# ------------------------------
# KONFIGURASI HALAMAN
# ------------------------------
st.set_page_config(
    page_title="Geoportal Sederhana",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Platform Visualisasi Data Geospasial Berbasis WebGIS")
st.markdown("---")

# ------------------------------
# SIDEBAR
# ------------------------------
with st.sidebar:
    st.header("Konfigurasi Peta")
    uploaded_file = st.file_uploader(
        "Unggah File Geospasial",
        type=['geojson', 'kml', 'gpkg', 'zip'],
        help="Format yang didukung: GeoJSON, KML, GPKG, atau Shapefile (ZIP)"
    )

    basemap = st.selectbox(
        "Pilih Base Map",
        ["OpenStreetMap", "CartoDB Positron", "Stamen Terrain"]
    )

# ------------------------------
# BASEMAP DEFINISI
# ------------------------------
TILE_MAP = {
    "OpenStreetMap": {
        "tiles": "OpenStreetMap",
        "attr": "© OpenStreetMap contributors"
    },
    "CartoDB Positron": {
        "tiles": "CartoDB Positron",
        "attr": "© OpenStreetMap contributors © CartoDB"
    },
    "Stamen Terrain": {
        "tiles": "Stamen Terrain",
        "attr": "Map tiles by Stamen Design, under CC BY 3.0. Data © OpenStreetMap contributors"
    }
}

# ------------------------------
# PEMBACA DATA (ZIP FIXED 100%)
# ------------------------------
def load_data(uploaded_file):
    if uploaded_file is None:
        return None

    tmp_path = None
    extract_dir = None

    try:
        # Simpan file upload ke disk
        suffix = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        # Jika ZIP (untuk shapefile)
        if suffix == ".zip":
            extract_dir = tempfile.mkdtemp()

            # Ekstrak isi ZIP
            try:
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                st.error(f"❌ File ZIP tidak dapat diekstrak: {e}")
                return None

            # Cari file .shp di seluruh folder
            shp_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(".shp"):
                        shp_files.append(os.path.join(root, file))

            if not shp_files:
                st.error("❌ File ZIP tidak mengandung file .shp yang valid.")
                return None

            # Gunakan shapefile pertama yang ditemukan
            shp_path = shp_files[0]

            # Gunakan driver ESRI Shapefile secara eksplisit
            gdf = gpd.read_file(shp_path, driver="ESRI Shapefile")

        else:
            # Format lain
            gdf = gpd.read_file(tmp_path)

        # Pastikan geometri ada
        if gdf.empty or "geometry" not in gdf.columns:
            st.error("❌ File terbaca tetapi tidak memiliki kolom geometri.")
            return None

        # Pastikan CRS adalah WGS84
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)

        return gdf

    except Exception as e:
        st.error(f"⚠️ Gagal memuat file: {e}")
        return None

    finally:
        # Bersihkan file sementara
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)

# ------------------------------
# PEMBUAT PETA
# ------------------------------
def create_map(gdf=None, basemap="OpenStreetMap"):
    default_center = [-6.2088, 106.8456]  # Jakarta
    center = default_center

    if gdf is not None and not gdf.empty:
        try:
            centroid = gdf.geometry.centroid.unary_union.centroid
            center = [centroid.y, centroid.x]
        except Exception:
            pass

    tile_info = TILE_MAP.get(basemap, TILE_MAP["OpenStreetMap"])

    m = folium.Map(
        location=center,
        zoom_start=10,
        tiles=tile_info["tiles"],
        attr=tile_info["attr"]
    )

    if gdf is not None and not gdf.empty:
        try:
            folium.GeoJson(
                gdf.to_json(),
                name="Data Geospasial",
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in gdf.columns if c != "geometry"]
                )
            ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Tidak dapat menambahkan layer: {e}")

    folium.LayerControl().add_to(m)
    return m

# ------------------------------
# TAMPILAN UTAMA
# ------------------------------
col1, col2 = st.columns([3, 1])

with col1:
    if uploaded_file:
        with st.spinner("📥 Memuat data..."):
            gdf = load_data(uploaded_file)
            if gdf is not None:
                st.success(f"✅ Data berhasil dimuat ({len(gdf)} fitur)")
                m = create_map(gdf, basemap)
                st_folium(m, width=750, height=500, key="map")
            else:
                st.warning("⚠️ Tidak ada data geospasial valid.")
    else:
        m = create_map()
        st_folium(m, width=750, height=500, key="default_map")

with col2:
    st.header("📊 Informasi Data")
    if uploaded_file and 'gdf' in locals() and gdf is not None:
        st.write(f"Jumlah fitur: {len(gdf)}")
        st.write(f"Kolom: {', '.join(gdf.columns)}")
        st.dataframe(gdf.head(5))

        geojson = gdf.to_json()
        st.download_button(
            label="💾 Download GeoJSON",
            data=geojson,
            file_name="data.geojson",
            mime="application/json"
        )
    else:
        st.info("Unggah file untuk melihat informasi data.")

st.markdown("---")
st.markdown("Dibuat dengan ❤️ oleh Adipandang Yudono | © 2025 Geoportal Sederhana")

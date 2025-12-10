import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Live Monitor", page_icon="⚡", layout="wide")

# File Penyimpanan
FILE_DATA = "data_monitoring.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 2. FUNGSI DATABASE ---
def init_db():
    if not os.path.exists(FILE_DATA):
        # Data dummy awal agar tidak error saat pertama run
        data_awal = [{"url": "https://google.com", "status": "PENDING", "code": "-", "latency": 0, "last_check": "-"}]
        simpan_db(data_awal)
        return data_awal
    return baca_db()

def baca_db():
    try:
        with open(FILE_DATA, "r") as f:
            return json.load(f)
    except:
        return []

def simpan_db(data):
    with open(FILE_DATA, "w") as f:
        json.dump(data, f, indent=4)

# Cek apakah User adalah Admin
query_params = st.query_params
is_admin = query_params.get("mode") == "admin"

# --- 3. LOGIKA SIDEBAR (HANYA ADMIN) ---
# Penonton tidak melihat sidebar ini
if is_admin:
    st.sidebar.header("🔧 Panel Admin")
    st.sidebar.success("Mode: ADMIN (Pengecek)")
    
    current_data = init_db()
    current_urls = "\n".join([item.get('url', '') for item in current_data])
    
    new_urls_text = st.sidebar.text_area("Edit Daftar Link:", value=current_urls, height=200)
    
    if st.sidebar.button("💾 Simpan Link Baru"):
        url_list = [u.strip() for u in new_urls_text.split('\n') if u.strip()]
        new_data = []
        for url in url_list:
            if not url.startswith("http"): url = "https://" + url
            # Cek data lama
            old_item = next((item for item in current_data if item.get('url') == url), None)
            if old_item:
                new_data.append(old_item)
            else:
                new_data.append({"url": url, "status": "PENDING", "code": "-", "latency": 0, "last_check": "-"})
        
        simpan_db(new_data)
        st.toast("Daftar link diperbarui!")
        time.sleep(1)
        st.rerun()
    
    st.sidebar.divider()
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN", value=False)

# --- 4. TAMPILAN UTAMA (WAJIB DITARUH SEBELUM LOGIKA REFRESH) ---
st.title("⚡ Dashboard Monitoring Real-Time")

# Baca data dari file JSON (yang diupdate oleh admin)
data_display = baca_db()

if not data_display:
    st.warning("Belum ada data link. Admin harap mengisi daftar link.")
else:
    df = pd.DataFrame(data_display)

    # Pastikan kolom ada (untuk menghindari error KeyError)
    if 'status' not in df.columns: df['status'] = "PENDING"
    
    # Metrik
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Link", len(df))
    c2.metric("Online (UP)", len(df[df['status'] == 'UP']))
    c3.metric("Down/Error", len(df[df['status'] != 'UP']), delta_color="inverse")
    
    if is_admin:
        c4.info("Status: 👨‍💻 ADMIN")
    else:
        c4.success("Status: 👀 LIVE VIEW")

    # Tabel
    def warnai_row(val):
        s = str(val)
        if s == 'UP': return 'color: #4CAF50; font-weight: bold'
        if '429' in s: return 'color: orange; font-weight: bold'
        if s == 'PENDING': return 'color: gray'
        return 'color: #FF5252; font-weight: bold'

    st.dataframe(
        df.style.map(warnai_row, subset=['status']),
        use_container_width=True,
        column_config={
            "url": "Link Website",
            "status": "Status",
            "code": "Kode Respon",
            "latency": "Latency (ms)",
            "last_check": "Waktu Cek (Server)"
        },
        height=600
    )

# --- 5. LOGIKA REFRESH VIEWER (DITARUH DI BAWAH) ---
if not is_admin:
    # Penonton akan refresh halaman setiap 2 detik untuk mengambil data JSON terbaru
    time.sleep(2)
    st.rerun()

# --- 6. LOGIKA BACKGROUND PROCESS ADMIN (DITARUH DI BAWAH) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    bar = st.progress(0)
    
    data_proc = baca_db()
    total = len(data_proc)
    
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 Admin sedang mengecek: {url}...")
        
        try:
            start = time.time()
            r = requests.get(url, headers=HEADERS, timeout=5)
            lat = round((time.time() - start) * 1000)
            
            if r.status_code == 200:
                stat = "UP"
            elif r.status_code == 429:
                stat = "BUSY (429)"
            else:
                stat = f"ERR {r.status_code}"
            code = r.status_code
        except:
            stat = "DOWN"
            code = "ERR"
            lat = 0
            
        # Update data baris ini
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = datetime.now().strftime("%H:%M:%S")
        
        # Simpan ke JSON langsung (agar Penonton melihat update per baris)
        simpan_db(data_proc)
        
        # Jeda anti-blokir
        wait = random.uniform(5, 8) if "429" in stat else random.uniform(1.5, 3)
        time.sleep(wait)
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success("Siklus selesai. Mengulang...")
    time.sleep(1)
    st.rerun()
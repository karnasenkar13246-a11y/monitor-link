import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Live Monitor WIB", page_icon="⚡", layout="wide")

# File Penyimpanan
FILE_DATA = "data_monitoring.json"

# Header Palsu (Anti Blokir)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 2. FUNGSI DATABASE & WAKTU ---
def get_wib_time():
    # Mengambil waktu UTC dan menambah 7 jam untuk WIB
    wib_time = datetime.utcnow() + timedelta(hours=7)
    return wib_time.strftime("%H:%M:%S")

def init_db():
    if not os.path.exists(FILE_DATA):
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

# Cek Mode Admin
query_params = st.query_params
is_admin = query_params.get("mode") == "admin"

# --- 3. LOGIKA SIDEBAR (ADMIN) ---
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
            old_item = next((item for item in current_data if item.get('url') == url), None)
            if old_item:
                new_data.append(old_item)
            else:
                new_data.append({"url": url, "status": "PENDING", "code": "-", "latency": 0, "last_check": "-"})
        
        simpan_db(new_data)
        st.toast("Database berhasil diperbarui!")
        time.sleep(1)
        st.rerun()
    
    st.sidebar.divider()
    
    # Pengaturan Loop
    st.sidebar.subheader("⚙️ Kontrol Pengecekan")
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN (Real-time)", value=False)
    
    if auto_loop:
        st.sidebar.warning("⚠️ Sistem berjalan terus-menerus tanpa henti.")
    else:
        st.sidebar.info("Centang kotak di atas untuk memulai.")

# --- 4. TAMPILAN UTAMA (TABS MENU) ---
st.title("⚡ Dashboard Monitoring Real-Time (WIB)")

# Load Data
data_display = baca_db()
df = pd.DataFrame(data_display)
if 'status' not in df.columns: df['status'] = "PENDING"

# --- MEMBUAT MENU TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Monitoring Live", "📈 Statistik", "ℹ️ Panduan Status"])

# === TAB 1: TABEL MONITORING ===
with tab1:
    if not data_display:
        st.warning("Data kosong.")
    else:
        # Metrik
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Link", len(df))
        c2.metric("Online (AMAN)", len(df[df['status'] == 'AMAN']))
        c3.metric("Kendala / Blokir", len(df[df['status'] != 'AMAN']), delta_color="inverse")
        
        if is_admin:
            c4.info("👨‍💻 ADMIN MODE")
        else:
            c4.success("👀 VIEW MODE")
            st.caption(f"🕒 Waktu Server: {get_wib_time()} WIB")

        # Styling Tabel
        def warnai_row(val):
            s = str(val)
            if s == 'AMAN': return 'color: #4CAF50; font-weight: bold' # Hijau
            if 'PENDING' in s: return 'color: gray'
            return 'color: #FF0000; font-weight: bold' # Merah untuk sisanya

        st.dataframe(
            df.style.map(warnai_row, subset=['status']),
            use_container_width=True,
            column_config={
                "url": "Link Website",
                "status": "Status Terkini",
                "code": "Kode Respon",
                "latency": "Latency (ms)",
                "last_check": "Waktu Cek (WIB)"
            },
            height=600
        )

# === TAB 2: STATISTIK ===
with tab2:
    st.subheader("Analisis Kondisi Link")
    if not df.empty:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            status_counts = df['status'].value_counts()
            st.bar_chart(status_counts)
        with col_chart2:
            st.write("Rincian Status:")
            st.dataframe(status_counts, use_container_width=True)
    else:
        st.info("Belum ada data.")

# === TAB 3: PANDUAN ===
with tab3:
    st.subheader("Keterangan Status & Warna")
    st.markdown("""
    | Status | Warna | Arti |
    | :--- | :--- | :--- |
    | **AMAN** | 🟢 **HIJAU** | Website dapat diakses normal (Kode 200). |
    | **CEK BY BK / NAWALA** | 🔴 **MERAH** | Terindikasi blokir (429/403) atau internet positif. |
    | **ERR / DOWN** | 🔴 **MERAH** | Error server atau mati total. |
    """)

# --- 5. LOGIKA REFRESH VIEWER ---
if not is_admin:
    # Penonton refresh cepat (3 detik) agar terasa real-time
    time.sleep(3) 
    st.rerun()

# --- 6. LOGIKA BACKGROUND PROCESS (ADMIN ONLY - REALTIME LOOP) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    bar = st.progress(0)
    
    data_proc = baca_db()
    total = len(data_proc)
    
    # --- LOOP PENGECEKAN ---
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 [{i+1}/{total}] Mengecek: {url}...")
        
        try:
            # Request timeout 5 detik
            r = requests.get(url, headers=HEADERS, timeout=5)
            lat = round(r.elapsed.total_seconds() * 1000)
            
            if r.status_code == 200:
                stat = "AMAN"
            elif r.status_code == 429:
                stat = "CEK BY BK / NAWALA"
            else:
                stat = f"ERR {r.status_code}"
            code = r.status_code
        except:
            stat = "DOWN"
            code = "ERR"
            lat = 0
            
        # Simpan Data dengan Waktu WIB
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_time() # <--- Menggunakan fungsi WIB
        
        simpan_db(data_proc)
        
        # Jeda "napas" singkat 1 detik agar tidak dianggap spammer brutal
        # Tapi ini akan terasa continue (real-time loop)
        time.sleep(1) 
        
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success("✅ Satu putaran selesai! Mengulang seketika...")
    
    # Hapus jeda panjang. Langsung restart.
    time.sleep(1) 
    st.rerun()
import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitor Link WIB", page_icon="⚡", layout="wide")

# File Penyimpanan
FILE_DATA = "data_monitoring.json"

# Header Palsu (Anti Blokir)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 2. FUNGSI DATABASE & WAKTU WIB ---
def get_wib_now():
    # Mengambil waktu UTC dan menambah 7 jam (WIB)
    wib_time = datetime.utcnow() + timedelta(hours=7)
    return wib_time

def get_wib_str():
    # Format string jam:menit:detik
    return get_wib_now().strftime("%H:%M:%S")

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
    
    # Pengaturan Waktu (Default 10 Menit)
    st.sidebar.subheader("⏱️ Pengaturan Interval")
    interval_menit = st.sidebar.number_input("Jeda Pengecekan (Menit):", min_value=1, value=10)
    interval_detik = interval_menit * 60
    
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN", value=False)
    
    # Menampilkan Jam Server saat ini (WIB)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"🕒 Jam Server: {get_wib_str()} WIB")

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
            c4.caption(f"Update Terakhir: {get_wib_str()} WIB")

        # Styling Tabel
        def warnai_row(val):
            s = str(val)
            if s == 'AMAN': return 'color: #4CAF50; font-weight: bold' # Hijau
            if 'PENDING' in s: return 'color: gray'
            return 'color: #FF0000; font-weight: bold' # Merah

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
    time.sleep(5) # Refresh otomatis untuk penonton
    st.rerun()

# --- 6. LOGIKA BACKGROUND PROCESS (ADMIN ONLY) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    countdown_placeholder = st.empty()
    bar = st.progress(0)
    
    # Catat waktu mulai (untuk perhitungan 10 menit)
    batch_start_time = time.time()
    
    data_proc = baca_db()
    total = len(data_proc)
    
    # --- LOOP PENGECEKAN LINK ---
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 [Proses {i+1}/{total}] Mengecek: {url}...")
        
        try:
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
            
        # Update Data dengan Waktu WIB
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str() # Pakai Jam WIB
        
        simpan_db(data_proc)
        
        # Jeda "sopan" 1 detik
        time.sleep(1) 
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success(f"✅ Pengecekan selesai pada pukul {get_wib_str()} WIB.")
    
    # --- LOGIKA TUNGGU SISA WAKTU (INTERVAL 10 MENIT) ---
    durasi_kerja = time.time() - batch_start_time
    sisa_waktu = interval_detik - durasi_kerja
    
    if sisa_waktu > 0:
        # Loop countdown sampai sisa waktu habis
        for s in range(int(sisa_waktu), 0, -1):
            menit = s // 60
            detik = s % 60
            
            # Tampilkan jam WIB yang berjalan + Countdown
            jam_sekarang = get_wib_str()
            countdown_placeholder.warning(
                f"🕒 Jam: {jam_sekarang} WIB | ⏳ Menunggu pengecekan berikutnya: {menit}m {detik}s lagi..."
            )
            time.sleep(1)
            
    countdown_placeholder.empty()
    st.rerun() # Ulangi proses
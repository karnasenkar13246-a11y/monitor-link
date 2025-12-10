import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitor Link Pro", page_icon="🌐", layout="wide")

# File Penyimpanan
FILE_DATA = "data_monitoring.json"

# Header Palsu (Anti Blokir)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 2. FUNGSI DATABASE & WAKTU WIB ---
def get_wib_now():
    return datetime.utcnow() + timedelta(hours=7)

def get_wib_str():
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
# Variabel Proxy Global (Default Kosong)
proxies = None 

if is_admin:
    st.sidebar.header("🔧 Panel Admin")
    st.sidebar.success("Mode: ADMIN (Pengecek)")
    
    current_data = init_db()
    current_urls = "\n".join([item.get('url', '') for item in current_data])
    
    new_urls_text = st.sidebar.text_area("Edit Daftar Link:", value=current_urls, height=150)
    
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
    
    # --- FITUR BARU: PROXY SETTING ---
    st.sidebar.subheader("🌍 Pengaturan Proxy (Opsional)")
    st.sidebar.info("Gunakan ini jika ingin mengecek link yang diblokir di lokasi server tapi aktif di luar negeri.")
    
    # Input Proxy
    proxy_input = st.sidebar.text_input("Masukkan Proxy (http://ip:port):", placeholder="Contoh: http://103.10.10.1:8080")
    
    # Simpan Proxy ke logic (Sementara)
    if proxy_input:
        proxies = {
            "http": proxy_input,
            "https": proxy_input
        }
        st.sidebar.warning(f"⚠️ Menggunakan Proxy: {proxy_input}")
    
    st.sidebar.divider()
    
    # Pengaturan Loop
    st.sidebar.subheader("⏱️ Kontrol Pengecekan")
    interval_menit = st.sidebar.number_input("Jeda Pengecekan (Menit):", min_value=1, value=10)
    interval_detik = interval_menit * 60
    
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN", value=False)
    st.sidebar.caption(f"🕒 Jam Server: {get_wib_str()} WIB")

# --- 4. TAMPILAN UTAMA ---
st.title("🌐 Dashboard Monitoring Link Pro")

data_display = baca_db()
df = pd.DataFrame(data_display)
if 'status' not in df.columns: df['status'] = "PENDING"

tab1, tab2, tab3 = st.tabs(["📊 Monitoring Live", "📈 Statistik", "ℹ️ Panduan"])

# === TAB 1: TABEL ===
with tab1:
    if not data_display:
        st.warning("Data kosong.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Link", len(df))
        c2.metric("Online (AMAN)", len(df[df['status'] == 'AMAN']))
        c3.metric("Kendala", len(df[df['status'] != 'AMAN']), delta_color="inverse")
        
        if is_admin:
            c4.info("👨‍💻 ADMIN MODE")
            if proxies:
                st.caption(f"Running via Proxy")
        else:
            c4.success("👀 VIEW MODE")
            c4.caption(f"Update: {get_wib_str()} WIB")

        def warnai_row(val):
            s = str(val)
            if s == 'AMAN': return 'color: #4CAF50; font-weight: bold'
            if 'PENDING' in s: return 'color: gray'
            return 'color: #FF0000; font-weight: bold'

        st.dataframe(
            df.style.map(warnai_row, subset=['status']),
            use_container_width=True,
            column_config={
                "url": "Link Website",
                "status": "Status",
                "code": "Kode",
                "latency": "Latency (ms)",
                "last_check": "Waktu Cek (WIB)"
            },
            height=600
        )

# === TAB 2: STATISTIK ===
with tab2:
    if not df.empty:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.bar_chart(df['status'].value_counts())
        with col_chart2:
            st.dataframe(df['status'].value_counts(), use_container_width=True)

# === TAB 3: PANDUAN ===
with tab3:
    st.markdown("""
    **Cara Menggunakan Proxy:**
    1. Cari proxy gratis/berbayar (Format: `http://ip_address:port`).
    2. Masukkan di menu Admin sidebar.
    3. Script akan mencoba mengakses website MELALUI proxy tersebut.
    
    **Status:**
    *   🟢 **AMAN**: Website aktif.
    *   🔴 **CEK BY BK / NAWALA**: Terindikasi blokir.
    *   🔴 **PROXY ERROR**: Proxy mati/lambat (Ganti proxy lain).
    """)

# --- 5. LOGIKA REFRESH VIEWER ---
if not is_admin:
    time.sleep(5)
    st.rerun()

# --- 6. LOGIKA BACKGROUND PROCESS (ADMIN ONLY) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    countdown_placeholder = st.empty()
    bar = st.progress(0)
    
    batch_start_time = time.time()
    data_proc = baca_db()
    total = len(data_proc)
    
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 [{i+1}/{total}] Mengecek: {url}...")
        
        try:
            # --- UPDATE: REQUEST DENGAN PROXY ---
            # Timeout diperpanjang jadi 10 detik karena Proxy biasanya lambat
            r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=10)
            lat = round(r.elapsed.total_seconds() * 1000)
            
            if r.status_code == 200:
                stat = "AMAN"
            elif r.status_code == 429:
                stat = "CEK BY BK / NAWALA"
            else:
                stat = f"ERR {r.status_code}"
            code = r.status_code
            
        except requests.exceptions.ProxyError:
            stat = "PROXY ERROR"
            code = "ERR"
            lat = 0
        except requests.exceptions.ConnectTimeout:
            stat = "TIMEOUT (LAMBAT)"
            code = "TO"
            lat = 0
        except:
            stat = "DOWN"
            code = "ERR"
            lat = 0
            
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str()
        
        simpan_db(data_proc)
        time.sleep(1) 
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success(f"✅ Selesai pukul {get_wib_str()} WIB.")
    
    durasi_kerja = time.time() - batch_start_time
    sisa_waktu = interval_detik - durasi_kerja
    
    if sisa_waktu > 0:
        for s in range(int(sisa_waktu), 0, -1):
            menit = s // 60
            detik = s % 60
            jam_sekarang = get_wib_str()
            countdown_placeholder.warning(f"🕒 {jam_sekarang} WIB | ⏳ Menunggu: {menit}m {detik}s...")
            time.sleep(1)
            
    countdown_placeholder.empty()
    st.rerun()
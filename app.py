import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime, timedelta
from urllib.parse import quote_plus

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitor Link Pro", page_icon="🌐", layout="wide")

FILE_DATA = "data_monitoring.json"
FILE_STATUS = "status_info.json" # FILE BARU: Untuk komunikasi waktu ke penonton

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 2. FUNGSI UTILITIES ---
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

# --- FUNGSI BARU: SIMPAN STATUS SISTEM (WAKTU NEXT RUN) ---
def simpan_status_system(status, next_run_timestamp=None):
    info = {
        "status_mesin": status, # 'WORKING' atau 'WAITING'
        "next_run": next_run_timestamp # Format Timestamp
    }
    with open(FILE_STATUS, "w") as f:
        json.dump(info, f)

def baca_status_system():
    try:
        with open(FILE_STATUS, "r") as f:
            return json.load(f)
    except:
        return {"status_mesin": "UNKNOWN", "next_run": 0}

# --- FUNGSI PROXY FORMATTER ---
def format_proxy_url(proxy_str):
    if not proxy_str: return None
    try:
        proxy_str = proxy_str.strip()
        if not proxy_str.startswith("http"):
            proxy_str = "http://" + proxy_str
        if "@" in proxy_str:
            protocol_split = proxy_str.split("://")
            base = protocol_split[1] if len(protocol_split) > 1 else protocol_split[0]
            auth_part, ip_part = base.split("@")
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                password_safe = quote_plus(password)
                final_url = f"http://{user}:{password_safe}@{ip_part}"
                return {"http": final_url, "https": final_url}
        return {"http": proxy_str, "https": proxy_str}
    except:
        return {"http": proxy_str, "https": proxy_str}

# --- 3. SIDEBAR ADMIN ---
query_params = st.query_params
is_admin = query_params.get("mode") == "admin"
proxies = None 

if is_admin:
    st.sidebar.header("🔧 Panel Admin")
    st.sidebar.success("Mode: ADMIN")
    
    current_data = init_db()
    current_urls = "\n".join([item.get('url', '') for item in current_data])
    
    new_urls_text = st.sidebar.text_area("Edit Daftar Link:", value=current_urls, height=150)
    
    if st.sidebar.button("💾 Simpan Link"):
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
        st.toast("Database update!")
        time.sleep(1)
        st.rerun()
    
    st.sidebar.divider()
    
    st.sidebar.subheader("🌍 Pengaturan Proxy")
    raw_proxy_input = st.sidebar.text_input("Masukkan Proxy (Webshare):", placeholder="http://user:pass@ip:port", value="")
    if raw_proxy_input:
        proxies = format_proxy_url(raw_proxy_input)
        st.sidebar.warning("✅ Proxy Aktif")
    
    st.sidebar.divider()
    
    st.sidebar.subheader("⏱️ Kontrol")
    interval_menit = st.sidebar.number_input("Jeda (Menit):", min_value=1, value=10)
    interval_detik = interval_menit * 60
    
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN", value=False)
    st.sidebar.caption(f"Server Time: {get_wib_str()} WIB")

# --- 4. TAMPILAN UTAMA ---
st.title("🌐 Dashboard Monitoring Link Pro")

# LOGIKA TAMPILAN HITUNG MUNDUR UNTUK PENONTON
if not is_admin:
    sys_info = baca_status_system()
    status_mesin = sys_info.get("status_mesin", "UNKNOWN")
    next_run_ts = sys_info.get("next_run", 0)
    
    if status_mesin == "WORKING":
        st.info("🔄 Sistem sedang melakukan pengecekan data terbaru... Mohon tunggu.")
    elif status_mesin == "WAITING" and next_run_ts:
        # Hitung sisa waktu
        sekarang_ts = datetime.utcnow().timestamp()
        sisa_detik = int(next_run_ts - sekarang_ts)
        
        if sisa_detik > 0:
            menit = sisa_detik // 60
            detik = sisa_detik % 60
            st.warning(f"⏳ Data akan diperbarui otomatis dalam: **{menit} menit {detik} detik**")
        else:
            st.success("✅ Memulai proses pembaruan data...")

# Load Data Tabel
data_display = baca_db()
df = pd.DataFrame(data_display)
if 'status' not in df.columns: df['status'] = "PENDING"

tab1, tab2, tab3 = st.tabs(["📊 Live", "📈 Statistik", "ℹ️ Info"])

with tab1:
    if not data_display:
        st.warning("Data kosong.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Link", len(df))
        c2.metric("Online (AMAN)", len(df[df['status'] == 'AMAN']))
        c3.metric("Kendala", len(df[df['status'] != 'AMAN']), delta_color="inverse")
        
        if is_admin:
            c4.info("👨‍💻 ADMIN")
        else:
            c4.success("👀 VIEWER")
            c4.caption(f"Last Update: {get_wib_str()} WIB")

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

with tab2:
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1: st.bar_chart(df['status'].value_counts())
        with col2: st.dataframe(df['status'].value_counts(), use_container_width=True)

with tab3:
    st.markdown("""
    **Fitur Terbaru:**
    - **Countdown Timer:** Penonton kini bisa melihat waktu hitung mundur menuju refresh berikutnya.
    - **Proxy Auto-Fix:** Support password proxy dengan simbol.
    """)

# --- 5. LOGIKA REFRESH VIEWER ---
if not is_admin:
    # Refresh setiap 1 detik agar countdown berjalan mulus (realtime detik)
    time.sleep(1) 
    st.rerun()

# --- 6. LOGIKA BACKGROUND (ADMIN) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    countdown_placeholder = st.empty()
    bar = st.progress(0)
    
    # [FASE 1] WORKING
    # Beri tahu sistem bahwa kita sedang bekerja
    simpan_status_system("WORKING", None)
    
    batch_start = time.time()
    data_proc = baca_db()
    total = len(data_proc)
    
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 [{i+1}/{total}] Cek: {url}...")
        
        stat = "DOWN"
        code = "ERR"
        lat = 0
        
        for attempt in range(3):
            try:
                r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=20)
                lat = round(r.elapsed.total_seconds() * 1000)
                if r.status_code == 200:
                    stat = "AMAN"
                elif r.status_code == 429:
                    stat = "CEK BY BK / NAWALA"
                else:
                    stat = f"ERR {r.status_code}"
                code = r.status_code
                break 
            except requests.exceptions.ProxyError:
                stat = "PROXY ERROR"
                code = "PRX"
                time.sleep(2)
            except Exception:
                stat = "DOWN"
                code = "ERR"
                time.sleep(1)
        
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str()
        
        simpan_db(data_proc)
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success(f"✅ Selesai: {get_wib_str()} WIB")
    
    # [FASE 2] WAITING
    # Hitung kapan next run akan terjadi
    durasi_kerja = time.time() - batch_start
    sisa_waktu = interval_detik - durasi_kerja
    
    if sisa_waktu > 0:
        # Simpan waktu target ke file agar Penonton bisa baca
        target_timestamp = datetime.utcnow().timestamp() + sisa_waktu
        simpan_status_system("WAITING", target_timestamp)
        
        for s in range(int(sisa_waktu), 0, -1):
            menit = s // 60
            detik = s % 60
            jam_now = get_wib_str()
            countdown_placeholder.warning(f"🕒 {jam_now} WIB | ⏳ Menunggu: {menit}m {detik}s")
            time.sleep(1)
            
    countdown_placeholder.empty()
    st.rerun()
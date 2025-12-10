import streamlit as st
import requests
import pandas as pd
import time
import os
import json
from datetime import datetime, timedelta
from urllib.parse import quote_plus

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitor Link 24H", page_icon="🌐", layout="wide")

FILE_DATA = "data_monitoring.json"
FILE_STATUS = "status_info.json" 

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

def simpan_status_system(status, next_run_timestamp=None):
    info = {
        "status_mesin": status, 
        "next_run": next_run_timestamp,
        "last_heartbeat": datetime.utcnow().timestamp()
    }
    with open(FILE_STATUS, "w") as f:
        json.dump(info, f)

def baca_status_system():
    try:
        with open(FILE_STATUS, "r") as f:
            return json.load(f)
    except:
        return {"status_mesin": "UNKNOWN", "next_run": 0, "last_heartbeat": 0}

# --- 3. LOGIKA UTAMA ---
query_params = st.query_params
mode = query_params.get("mode")

# Hardcode Proxy (Isi jika pakai Webshare)
# Format: {"http": "http://user:pass@ip:port", "https": "http://user:pass@ip:port"}
PROXY_SERVER = None 

# ==========================================
# MODE 1: ROBOT (AUTO TRIGGER via CRON-JOB)
# ==========================================
if mode == "robot_trigger":
    st.write("🤖 Robot sedang bekerja...")
    
    simpan_status_system("WORKING", None)
    
    data_proc = baca_db()
    
    for i, item in enumerate(data_proc):
        url = item['url']
        stat = "DOWN"
        code = "ERR"
        lat = 0
        
        for attempt in range(3):
            try:
                r = requests.get(url, headers=HEADERS, proxies=PROXY_SERVER, timeout=20)
                lat = round(r.elapsed.total_seconds() * 1000)
                if r.status_code == 200:
                    stat = "AMAN"
                elif r.status_code == 429:
                    stat = "CEK BY BK / NAWALA"
                else:
                    stat = f"ERR {r.status_code}"
                code = r.status_code
                break 
            except Exception:
                time.sleep(1)
        
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str()
        
        simpan_db(data_proc)
        # Heartbeat agar sistem dianggap hidup
        simpan_status_system("WORKING", None)

    # Set jadwal berikutnya (+10 menit)
    next_run = datetime.utcnow().timestamp() + 600 
    simpan_status_system("WAITING", next_run)
    
    st.success(f"✅ Selesai: {get_wib_str()}")
    st.stop()

# ==========================================
# MODE 2 & 3: ADMIN & PENONTON (VISUALISASI)
# ==========================================

# -- Sidebar Admin (Hanya muncul jika mode=admin) --
if mode == "admin":
    st.sidebar.header("🔧 Panel Admin")
    st.sidebar.info("Dashboard ini berjalan otomatis 24 Jam via Cron-job.")
    
    current_data = init_db()
    current_urls = "\n".join([item.get('url', '') for item in current_data])
    new_urls = st.sidebar.text_area("Edit Daftar Link:", value=current_urls, height=300)
    
    if st.sidebar.button("Simpan Perubahan"):
        u_list = [u.strip() for u in new_urls.split('\n') if u.strip()]
        n_data = []
        for u in u_list:
            if not u.startswith("http"): u = "https://" + u
            # Pertahankan data lama jika ada (agar tidak merah semua saat save)
            old_item = next((item for item in current_data if item.get('url') == u), None)
            if old_item:
                n_data.append(old_item)
            else:
                n_data.append({"url": u, "status": "PENDING", "code": "-", "latency": 0, "last_check": "-"})
        simpan_db(n_data)
        st.toast("Daftar link berhasil disimpan!")
        time.sleep(1)
        st.rerun()

# -- Tampilan Utama (Admin & Penonton melihat ini) --
st.title("🌐 Dashboard Monitoring 24 Jam")

# Indikator Status Sistem
sys_info = baca_status_system()
status_mesin = sys_info.get("status_mesin", "UNKNOWN")
next_run_ts = sys_info.get("next_run", 0)
last_heartbeat = sys_info.get("last_heartbeat", 0)
sekarang_ts = datetime.utcnow().timestamp()

# Logika Offline (Jika Robot mati lebih dari 12 menit)
if (sekarang_ts - last_heartbeat) > 720: 
    st.error("🔴 **SYSTEM OFFLINE:** Robot pengecek tidak aktif. Pastikan Cron-job berjalan.")
elif status_mesin == "WORKING":
    st.info("🔄 **Robot Sedang Bekerja:** Melakukan update data...")
else:
    sisa = int(next_run_ts - sekarang_ts)
    if sisa > 0:
        m = sisa // 60
        s = sisa % 60
        st.warning(f"⏳ **Online:** Update berikutnya dalam {m}m {s}s")
    else:
        st.success("✅ Menunggu Robot bekerja...")

# Tabel Data
df = pd.DataFrame(baca_db())

tab1, tab2 = st.tabs(["📊 Live Data", "📈 Statistik"])

with tab1:
    if not df.empty:
        if 'status' not in df.columns: df['status'] = "PENDING"
        
        # Metrik Ringkas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Link", len(df))
        c2.metric("Aman", len(df[df['status'] == 'AMAN']))
        c3.metric("Kendala", len(df[df['status'] != 'AMAN']), delta_color="inverse")

        def warnai(val):
            s = str(val)
            if s == 'AMAN': return 'color: #4CAF50; font-weight: bold'
            if 'PENDING' in s: return 'color: gray'
            return 'color: #FF0000; font-weight: bold'

        st.dataframe(
            df.style.map(warnai, subset=['status']),
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
    else:
        st.info("Belum ada link. Masuk ke mode admin untuk menambahkan.")

with tab2:
    if not df.empty:
        st.bar_chart(df['status'].value_counts())

# Auto Refresh Tampilan setiap 5 detik (Agar hitung mundur jalan)
time.sleep(5)
st.rerun()
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

# --- 3. LOGIKA UTAMA ---
query_params = st.query_params
mode = query_params.get("mode")

# Hardcode Proxy di sini agar Robot bisa baca (Ganti dengan Proxy Anda yang benar)
# Contoh: "http://user:pass@ip:port"
PROXY_SERVER = None 
# Jika ingin pakai proxy untuk robot, isi di bawah ini:
# PROXY_SERVER = format_proxy_url("http://karnasenkar:passwordanda@1.2.3.4:8080")

# ==========================================
# MODE ROBOT (AUTO TRIGGER)
# ==========================================
if mode == "robot_trigger":
    st.title("🤖 Robot Worker Active")
    st.write("Sedang menjalankan pengecekan otomatis...")
    
    simpan_status_system("WORKING", None)
    
    data_proc = baca_db()
    total = len(data_proc)
    
    # Progress bar text
    progress_text = st.empty()
    bar = st.progress(0)

    for i, item in enumerate(data_proc):
        url = item['url']
        progress_text.text(f"Cek: {url}")
        
        stat = "DOWN"
        code = "ERR"
        lat = 0
        
        for attempt in range(3):
            try:
                # Robot pakai timeout 20s
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
                stat = "DOWN"
                code = "ERR"
                time.sleep(1)
        
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str()
        
        simpan_db(data_proc)
        bar.progress((i + 1) / total)
        
        # Simpan heartbeat agar penonton tahu sistem hidup
        simpan_status_system("WORKING", None)

    # Setelah selesai, set status WAITING + 10 Menit ke depan
    next_run = datetime.utcnow().timestamp() + 600 # 600 detik = 10 menit
    simpan_status_system("WAITING", next_run)
    
    st.success(f"✅ Robot Selesai pada {get_wib_str()}")
    st.stop() # Berhenti di sini, jangan load tampilan lain

# ==========================================
# MODE ADMIN (MANUAL)
# ==========================================
elif mode == "admin":
    # (Kode Admin Sidebar seperti biasa - dipersingkat untuk fokus)
    st.sidebar.header("🔧 Panel Admin")
    
    # Input Link
    current_data = init_db()
    current_urls = "\n".join([item.get('url', '') for item in current_data])
    new_urls = st.sidebar.text_area("Edit Link:", value=current_urls)
    if st.sidebar.button("Simpan"):
        # Logika simpan sederhana
        u_list = [u.strip() for u in new_urls.split('\n') if u.strip()]
        n_data = []
        for u in u_list:
            if not u.startswith("http"): u = "https://" + u
            n_data.append({"url": u, "status": "PENDING", "code": "-", "latency": 0, "last_check": "-"})
        simpan_db(n_data)
        st.rerun()

    st.sidebar.info("Untuk Otomatis 24 Jam: Gunakan cron-job.org untuk menembak link '?mode=robot_trigger'")
    st.title("🔧 Halaman Admin")
    st.write("Gunakan menu sidebar untuk mengedit link.")
    st.write("Untuk melihat hasil, buka mode penonton (hapus ?mode=admin).")

# ==========================================
# MODE PENONTON (VIEWER)
# ==========================================
else:
    st.title("🌐 Dashboard Monitoring Link Pro")
    
    # Indikator Status
    sys_info = baca_status_system()
    status_mesin = sys_info.get("status_mesin", "UNKNOWN")
    next_run_ts = sys_info.get("next_run", 0)
    last_heartbeat = sys_info.get("last_heartbeat", 0)
    sekarang_ts = datetime.utcnow().timestamp()
    
    # Logika Offline: Jika heartbeat terakhir lebih tua dari 12 menit (10 menit interval + 2 menit toleransi)
    if (sekarang_ts - last_heartbeat) > 720: 
        st.error("🔴 **SYSTEM OFFLINE:** Robot pengecek mati. Silakan aktifkan cron-job.")
    elif status_mesin == "WORKING":
        st.info("🔄 **Sedang Mengecek:** Robot sedang bekerja...")
    else:
        sisa = int(next_run_ts - sekarang_ts)
        if sisa > 0:
            m = sisa // 60
            s = sisa % 60
            st.warning(f"⏳ **Online:** Update berikutnya dalam {m}m {s}s")
        else:
            st.success("✅ Menunggu Robot bekerja...")
            
    # Tampilkan Tabel
    df = pd.DataFrame(baca_db())
    if not df.empty:
        if 'status' not in df.columns: df['status'] = "PENDING"
        
        def warnai(val):
            s = str(val)
            if s == 'AMAN': return 'color: #4CAF50; font-weight: bold'
            if 'PENDING' in s: return 'color: gray'
            return 'color: #FF0000; font-weight: bold'

        st.dataframe(df.style.map(warnai, subset=['status']), use_container_width=True, height=600)
    
    time.sleep(1)
    st.rerun()
import streamlit as st
import requests
import pandas as pd
import time
import os
import json
import random
from datetime import datetime, timedelta
from urllib.parse import quote_plus # PENTING: Untuk menangani password bersimbol

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitor Link Pro", page_icon="🌐", layout="wide")

FILE_DATA = "data_monitoring.json"

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

# --- FUNGSI PENTING: MEMBERSIHKAN FORMAT PROXY ---
def format_proxy_url(proxy_str):
    if not proxy_str: return None
    try:
        proxy_str = proxy_str.strip()
        
        # Tambahkan http jika belum ada
        if not proxy_str.startswith("http"):
            proxy_str = "http://" + proxy_str
            
        # Logika khusus: Jika ada password, kita encode passwordnya
        if "@" in proxy_str:
            # Memisahkan bagian http://
            protocol_split = proxy_str.split("://")
            base = protocol_split[1] if len(protocol_split) > 1 else protocol_split[0]
            
            # Memisahkan user:pass dengan ip:port
            auth_part, ip_part = base.split("@")
            
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # INI KUNCINYA: Mengubah simbol '!' menjadi kode aman '%21'
                password_safe = quote_plus(password)
                final_url = f"http://{user}:{password_safe}@{ip_part}"
                
                return {"http": final_url, "https": final_url}
        
        # Jika proxy biasa
        return {"http": proxy_str, "https": proxy_str}
    except:
        # Jika gagal parsing, kembalikan input mentah
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
    # Input Proxy
    raw_proxy_input = st.sidebar.text_input(
        "Masukkan Proxy (Webshare):", 
        placeholder="http://user:pass@ip:port",
        value=""
    )
    
    if raw_proxy_input:
        # Panggil fungsi format otomatis di sini
        proxies = format_proxy_url(raw_proxy_input)
        st.sidebar.warning("✅ Proxy Aktif (Auto-Formatted)")
    
    st.sidebar.divider()
    
    # Loop Control
    st.sidebar.subheader("⏱️ Kontrol")
    interval_menit = st.sidebar.number_input("Jeda (Menit):", min_value=1, value=10)
    interval_detik = interval_menit * 60
    
    auto_loop = st.sidebar.checkbox("🔄 JALANKAN PENGECEKAN", value=False)
    st.sidebar.caption(f"Server Time: {get_wib_str()} WIB")

# --- 4. TAMPILAN UTAMA ---
st.title("🌐 Dashboard Monitoring Link (Smart Proxy)")

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
            if proxies: st.caption("🌍 Proxy Mode")
        else:
            c4.success("👀 VIEWER")
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

with tab2:
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1: st.bar_chart(df['status'].value_counts())
        with col2: st.dataframe(df['status'].value_counts(), use_container_width=True)

with tab3:
    st.markdown("""
    **Fitur Baru:**
    1. **Auto-Fix Password:** Password proxy dengan simbol (!, @, #) kini otomatis diperbaiki.
    2. **Auto-Retry:** Jika koneksi proxy gagal, sistem mencoba 3x sebelum error.
    """)

# --- 5. LOGIKA REFRESH VIEWER ---
if not is_admin:
    time.sleep(5)
    st.rerun()

# --- 6. LOGIKA BACKGROUND (ADMIN) ---
if is_admin and auto_loop:
    status_placeholder = st.empty()
    countdown_placeholder = st.empty()
    bar = st.progress(0)
    
    batch_start = time.time()
    data_proc = baca_db()
    total = len(data_proc)
    
    for i, item in enumerate(data_proc):
        url = item['url']
        status_placeholder.info(f"🔍 [{i+1}/{total}] Cek: {url}...")
        
        stat = "DOWN"
        code = "ERR"
        lat = 0
        
        # --- PERBAIKAN: LOOPING RETRY 3 KALI ---
        # Ini penting agar proxy yang kadang gagal bisa dicoba lagi
        for attempt in range(3):
            try:
                # Timeout dinaikkan jadi 20 detik
                r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=20)
                lat = round(r.elapsed.total_seconds() * 1000)
                
                if r.status_code == 200:
                    stat = "AMAN"
                elif r.status_code == 429:
                    stat = "CEK BY BK / NAWALA"
                else:
                    stat = f"ERR {r.status_code}"
                code = r.status_code
                
                # Jika berhasil, keluar dari loop retry
                break 
                
            except requests.exceptions.ProxyError:
                stat = "PROXY ERROR"
                code = "PRX"
                time.sleep(2) # Tunggu 2 detik sebelum coba lagi
            except Exception:
                stat = "DOWN"
                code = "ERR"
                time.sleep(1)
        # ----------------------------------------
        
        data_proc[i]['status'] = stat
        data_proc[i]['code'] = str(code)
        data_proc[i]['latency'] = lat
        data_proc[i]['last_check'] = get_wib_str()
        
        simpan_db(data_proc)
        bar.progress((i + 1) / total)
        
    bar.empty()
    status_placeholder.success(f"✅ Selesai: {get_wib_str()} WIB")
    
    durasi = time.time() - batch_start
    sisa = interval_detik - durasi
    
    if sisa > 0:
        for s in range(int(sisa), 0, -1):
            menit = s // 60
            detik = s % 60
            countdown_placeholder.warning(f"🕒 {get_wib_str()} WIB | ⏳ Next: {menit}m {detik}s")
            time.sleep(1)
            
    countdown_placeholder.empty()
    st.rerun()
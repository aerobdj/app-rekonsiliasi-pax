import streamlit as st
import pandas as pd
import pdfplumber
import re
from rapidfuzz import fuzz, process
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN & BRANDING INJOURNEY
# -----------------------------------------------------------------------------
LOGO_WHITE = "https://www.injourneyairports.id/assets/injourney-logo-white-Dl4T6LNj.png" # Mode Gelap
LOGO_GREY = "https://www.injourneyairports.id/assets/injourney-logo-grey-BHunbWo1.png"   # Mode Terang
KAWUNG_ICON = "https://www.injourneyairports.id/assets/kawung-logo-side-CktPU2GK.png"

st.set_page_config(
    page_title="InJourney Airports - Pax Reconciliation System",
    page_icon=KAWUNG_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Gunakan st.logo bawaan Streamlit untuk menangani switcher gambar secara native
st.logo(
    image=LOGO_GREY,
    icon_image=KAWUNG_ICON,
)

# Custom CSS
st.markdown("""
    <style>
    /* PADDING ATAS SIDEBAR */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
    }

    /* KONTROL UKURAN LOGO STREAMLIT NATIVE */
    [data-testid="stSidebarHeader"] img {
        max-height: 45px !important;
        width: auto !important;
    }

    /* STYLE LOGO KUSTOM DI KONTEN UTAMA & SIDEBAR */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    .brand-logo{
        width:170px;
        height:auto;
        transition:0.25s ease;
    }
    
    /* ---------- LIGHT MODE ---------- */
    
    html[data-theme="light"] .brand-logo,
    body[class*="stLight"] .brand-logo{
        filter:none;
    }
    
    /* ---------- DARK MODE ---------- */
    
    html[data-theme="dark"] .brand-logo,
    body[class*="stDark"] .brand-logo{
        filter:brightness(0) invert(1);
    }
    
    /* ---------- LOGO STREAMLIT ---------- */
    
    [data-testid="stSidebarHeader"] img{
        max-height:45px !important;
        width:auto !important;
        transition:.25s ease;
    }
    
    /* Light */
    
    html[data-theme="light"] [data-testid="stSidebarHeader"] img,
    body[class*="stLight"] [data-testid="stSidebarHeader"] img{
        filter:none;
    }
    
    /* Dark */
    
    html[data-theme="dark"] [data-testid="stSidebarHeader"] img,
    body[class*="stDark"] [data-testid="stSidebarHeader"] img{
        filter:brightness(0) invert(1);
    }

    /* MENGGUNAKAN VARIABLE WARNA BAWAAN STREAMLIT UNTUK VISIBILITAS PASTI */
    /* Saat Light Mode: Background terang, logo di-invert ke warna abu-abu gelap */
    /* Saat Dark Mode: Background gelap, logo di-invert ke warna putih */

    .sidebar-mini-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        background-color: rgba(148, 163, 184, 0.15);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 20px;
        padding: 3px 10px;
        margin-top: 6px;
    }
    .sidebar-mini-icon {
        width: 14px;
        height: 14px;
    }
    .sidebar-mini-text {
        font-size: 11px;
        font-weight: 600;
        color: #94a3b8;
        letter-spacing: 0.5px;
    }

    /* HEADER KONTEN UTAMA */
    .main-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(148, 163, 184, 0.3);
        margin-bottom: 24px;
    }
    .main-title {
        font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
        font-weight: 700;
        font-size: 28px;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }

    /* WELCOME CARD */
    .welcome-card {
        background: rgba(30, 41, 59, 0.1);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 12px;
        padding: 28px;
        margin-top: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .welcome-title {
        font-size: 18px;
        font-weight: 600;
        color: #0284c7;
        margin-bottom: 8px;
    }
    .welcome-text {
        font-size: 14px;
        line-height: 1.6;
    }
    .step-badge {
        display: inline-block;
        background-color: #0284c7;
        color: white;
        font-size: 12px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 6px;
    }

    /* METRIC CARDS */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.05);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #94a3b8 !important;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
    }

    /* PRIMARY BUTTON */
    div.stButton > button:first-child {
        background-color: #0284c7;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #0369a1;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []

# -----------------------------------------------------------------------------
# 2. HELPER PARSER & RECONCILE ENGINE
# -----------------------------------------------------------------------------

def load_tapping_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()

    filename = uploaded_file.name.lower()
    df = None
    encodings = ["utf-8", "latin1", "iso-8859-1", "cp1252", "utf-16"]

    if filename.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(uploaded_file)
        except Exception:
            df = None

    if df is None or df.empty:
        for enc in encodings:
            for sep in ["\t", ",", ";", "|"]:
                try:
                    uploaded_file.seek(0)
                    temp_df = pd.read_csv(uploaded_file, sep=sep, encoding=enc, on_bad_lines="skip")
                    if temp_df is not None and len(temp_df.columns) > 1 and len(temp_df) > 0:
                        df = temp_df
                        break
                except Exception:
                    continue
            if df is not None and not df.empty:
                break

    if df is None or df.empty:
        try:
            uploaded_file.seek(0)
            tables = pd.read_html(uploaded_file)
            if tables:
                df = tables[0]
        except Exception:
            pass

    if df is not None and not df.empty:
        df.columns = [str(col).strip().upper() for col in df.columns]
        return df
    else:
        st.error(f"⚠️ File **{uploaded_file.name}** tidak terbaca atau kosong.")
        return pd.DataFrame()

def parse_manifest_pdf(pdf_file, airline):
    manifest_data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            for line in lines:
                pnr_match = re.search(r"\b([A-Z0-9]{6})\b", line)
                seat_match = re.search(r"\b([0-9]{1,2}[A-F])\b", line)
                name_match = re.search(r"([A-Z\s\/,\.-]+(?:MR|MRS|MS|MISS|MSTR|TITOHIR|PAX)?)", line)
                
                pnr = pnr_match.group(1) if pnr_match else None
                seat = seat_match.group(1) if seat_match else None
                
                if seat or pnr:
                    raw_name = name_match.group(1).strip() if name_match else line[:25].strip()
                    clean_name = re.sub(r"[^A-Z\s\/]", "", raw_name).strip()
                    if len(clean_name) > 3:
                        manifest_data.append({
                            "nama_manifest": clean_name,
                            "seat_manifest": seat if seat else "NO_SEAT",
                            "pnr_manifest": pnr if pnr else ("NO_PNR_LION" if "LION" in airline.upper() else "NO_PNR")
                        })
    return pd.DataFrame(manifest_data)

def reconcile_engine(df_tapping, df_manifest, airline_name):
    empty_columns = ["Nama Tapping", "Seat Tapping", "PNR Tapping", "Type Pax", "Seat Manifest", "PNR Manifest", "Status", "Catatan"]
    if df_tapping.empty or df_manifest.empty:
        return pd.DataFrame(columns=empty_columns)

    results = []
    has_manifest_pnr = not df_manifest["pnr_manifest"].str.contains("NO_PNR").all()
    
    for idx, tap in df_tapping.iterrows():
        tap_nama = str(tap.get("NAMA", tap.get("NAMA PAX", ""))).strip()
        tap_seat = str(tap.get("SEAT", "")).strip()
        tap_pnr = str(tap.get("PNR", "")).strip()
        tap_type = str(tap.get("TYPE", "Adult")).strip()
        
        status = ""
        catatan = ""
        matched_seat_manifest = "-"
        matched_pnr_manifest = "-"
        
        manifest_names = df_manifest["nama_manifest"].tolist()
        best_match = process.extractOne(tap_nama, manifest_names, scorer=fuzz.token_sort_ratio)
        
        if best_match and best_match[1] >= 75:
            match_row = df_manifest[df_manifest["nama_manifest"] == best_match[0]].iloc[0]
            mnf_seat = match_row["seat_manifest"]
            mnf_pnr = match_row["pnr_manifest"]
            
            matched_seat_manifest = mnf_seat
            matched_pnr_manifest = mnf_pnr
            
            is_seat_same = (tap_seat == mnf_seat)
            is_pnr_same = (tap_pnr == mnf_pnr) if (has_manifest_pnr and tap_pnr != "") else False
            
            pnr_note = " (PNR diganti No Ticket)" if (not has_manifest_pnr and "LION" in airline_name.upper()) else ""

            if is_seat_same and is_pnr_same:
                status = "🟢 MATCH"
                catatan = "Match Perfect" + pnr_note
            elif is_seat_same and not is_pnr_same:
                status = "🟡 MATCH"
                catatan = "PNR Berbeda" + pnr_note
            elif not is_seat_same and is_pnr_same:
                status = "🟡 MATCH"
                catatan = f"Change Seat (Seat Manifest: {mnf_seat})" + pnr_note
            else:
                status = "🔴 NOT MATCH"
                catatan = "Nama beda / Perlu Validasi" + pnr_note
        else:
            status = "🚨 UNMATCHED"
            catatan = "Offload / Not in Manifest"
            
        results.append({
            "Nama Tapping": tap_nama,
            "Seat Tapping": tap_seat,
            "PNR Tapping": tap_pnr,
            "Type Pax": tap_type,
            "Seat Manifest": matched_seat_manifest,
            "PNR Manifest": matched_pnr_manifest,
            "Status": status,
            "Catatan": catatan
        })
        
    df_res = pd.DataFrame(results) if results else pd.DataFrame(columns=empty_columns)
    
    scanned_manifest_seats = df_res["Seat Manifest"].tolist() if "Seat Manifest" in df_res.columns else []
    no_show_list = []
    for idx, mnf in df_manifest.iterrows():
        if mnf["seat_manifest"] not in scanned_manifest_seats and mnf["seat_manifest"] != "NO_SEAT":
            no_show_list.append({
                "Nama Tapping": mnf["nama_manifest"] + " (Manifest Pax)",
                "Seat Tapping": "-",
                "PNR Tapping": "-",
                "Type Pax": "-",
                "Seat Manifest": mnf["seat_manifest"],
                "PNR Manifest": mnf["pnr_manifest"],
                "Status": "⚪ NO SHOW",
                "Catatan": "Not Scanned / Ghost Pax"
            })
            
    if no_show_list:
        df_res = pd.concat([df_res, pd.DataFrame(no_show_list)], ignore_index=True)
        
    return df_res

# -----------------------------------------------------------------------------
# 3. TAMPILAN SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
        <div class="logo-container">
            <img src="{LOGO_WHITE}" class="brand-logo" alt="InJourney Logo">
            <div class="sidebar-mini-badge">
                <img src="{KAWUNG_ICON}" class="sidebar-mini-icon" alt="Kawung">
                <span class="sidebar-mini-text">Pax Reconciliation System</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    menu = st.radio("Pilihan Menu:", ["📊 Rekonsiliasi Data", "📜 Histori Log"])
    st.divider()

if menu == "📊 Rekonsiliasi Data":
    with st.sidebar:
        st.subheader("1. Pengaturan Flight")
        airline = st.selectbox(
            "Pilih Maskapai:",
            ["Lion Group (JT/IW/ID)", "Garuda Indonesia (GA)", "Citilink (QG)", "Scoot (TR)", "Malaysia Airlines (MH)", "Lainnya"]
        )
        flight_mode = st.radio("Mode Penerbangan:", ["Single Flight", "Combine Flight"])
        st.divider()
        
        st.subheader("2. Upload Dokumen")
        allowed_types = ["txt", "csv", "xlsx", "xls"]
        
        if flight_mode == "Single Flight":
            file_tapping1 = st.file_uploader("Upload File Tapping:", type=allowed_types)
            file_tapping2 = None
        else:
            file_tapping1 = st.file_uploader("Upload Tapping Flight 1:", type=allowed_types, key="t1")
            file_tapping2 = st.file_uploader("Upload Tapping Flight 2:", type=allowed_types, key="t2")
            
        file_manifest = st.file_uploader("Upload Manifest PDF/TXT:", type=["pdf", "txt"])
        
        st.write("")
        btn_proses = st.button("🚀 MULAI REKONSILIASI", use_container_width=True)

    # -------------------------------------------------------------------------
    # 4. TAMPILAN KONTEN UTAMA (MAIN CONTENT AREA)
    # -------------------------------------------------------------------------
    
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.markdown("""
            <div class="main-header-container">
                <div>
                    <h1 class="main-title">Passenger Reconciliation System</h1>
                    <div class="sub-title">Sistem Rekonsiliasi Otomatis Data Gate Tapping vs Manifest Penumpang</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_head2:
        st.markdown(f'<img src="{LOGO_WHITE}" class="brand-logo" alt="InJourney Logo">', unsafe_allow_html=True)

    if btn_proses:
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload di sidebar sebelah kiri sebelum memproses!")
        else:
            with st.spinner("⏳ Memproses ekstraksi data & mencocokkan kriteria..."):
                df_tap1 = load_tapping_file(file_tapping1)
                
                if flight_mode == "Combine Flight":
                    df_tap2 = load_tapping_file(file_tapping2)
                    if not df_tap1.empty and not df_tap2.empty:
                        df_tapping = pd.concat([df_tap1, df_tap2], ignore_index=True)
                    else:
                        df_tapping = pd.DataFrame()
                else:
                    df_tapping = df_tap1
                
                df_manifest = parse_manifest_pdf(file_manifest, airline)
                
                if df_tapping.empty:
                    st.error("❌ Proses dibatalkan karena data Tapping tidak berhasil terbaca/kosong.")
                elif df_manifest.empty:
                    st.error("❌ Proses dibatalkan karena data Manifest PDF tidak berhasil terbaca/kosong.")
                else:
                    df_result = reconcile_engine(df_tapping, df_manifest, airline)
                    
                    st.session_state["history"].append({
                        "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "airline": airline,
                        "mode": flight_mode,
                        "total_pax": len(df_result),
                        "data": df_result
                    })

                    st.markdown("### 📈 Ringkasan Hasil Rekonsiliasi")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Penumpang", f"{len(df_result)} Pax")
                    col2.metric("🟢 Perfect Match", f"{len(df_result[df_result['Status'] == '🟢 MATCH'])} Pax")
                    col3.metric("🟡 Match Catatan", f"{len(df_result[df_result['Status'] == '🟡 MATCH'])} Pax")
                    col4.metric("🚨 Alert / Unmatched", f"{len(df_result[df_result['Status'].isin(['🔴 NOT MATCH', '🚨 UNMATCHED'])])} Pax")
                    
                    st.write("")
                    st.markdown("### 📋 Detail Pencocokan Data Penumpang")
                    st.dataframe(df_result, use_container_width=True, height=450)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df_result.to_excel(writer, index=False, sheet_name="Rekonsiliasi")
                    
                    st.download_button(
                        label="📥 Download Laporan Hasil (.XLSX)",
                        data=output.getvalue(),
                        file_name=f"InJourney_Rekonsiliasi_{airline.split()[0]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

    else:
        st.markdown("""
            <div class="welcome-card">
                <div class="welcome-title">Selamat Datang di Passenger Reconciliation System InJourney Airports</div>
                <div class="welcome-text">
                    Sistem ini dirancang untuk mempermudah pencocokan data penyeberangan/keberangkatan penumpang antara data log <b>Gate Tapping</b> dan <b>Passenger Manifest PDF</b> secara presisi dan akurat.
                </div>
                <hr style="border: 0; border-top: 1px solid rgba(148, 163, 184, 0.3); margin: 16px 0;">
                <div class="welcome-text">
                    <b>Panduan Penggunaan Singkat:</b><br>
                    <p style="margin-top: 8px; margin-bottom: 4px;"><span class="step-badge">1</span> Pilih maskapai penerbangan dan mode penerbangan di sidebar sebelah kiri.</p>
                    <p style="margin-bottom: 4px;"><span class="step-badge">2</span> Unggah file Tapping (CSV/XLSX/TXT/XLS) dan file Manifest PDF yang sesuai.</p>
                    <p style="margin-bottom: 0;"><span class="step-badge">3</span> Klik tombol <b>🚀 MULAI REKONSILIASI</b> untuk memulai analisis data secara otomatis.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

elif menu == "📜 Histori Log":
    st.title("📜 Histori Log Rekonsiliasi")
    st.caption("Daftar riwayat pemrosesan data rekonsiliasi pada sesi ini.")
    
    if len(st.session_state["history"]) == 0:
        st.warning("Belum ada riwayat rekonsiliasi yang dilakukan pada sesi ini.")
    else:
        for idx, item in enumerate(reversed(st.session_state["history"])):
            with st.expander(f"🕒 {item['time']} — {item['airline']} ({item['mode']}) — Total: {item['total_pax']} Pax"):
                st.dataframe(item["data"], use_container_width=True)

import streamlit as st
import pandas as pd
import pdfplumber
import re
from rapidfuzz import fuzz, process
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN & BRANDING INJOURNEY
# -----------------------------------------------------------------------------
LOGO_GREY = "https://www.injourneyairports.id/assets/injourney-logo-grey-BHunbWo1.png"
KAWUNG_ICON = "https://www.injourneyairports.id/assets/kawung-logo-side-CktPU2GK.png"

st.set_page_config(
    page_title="InJourney Airports - Pax Reconciliation System",
    page_icon=KAWUNG_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.logo(
    image=KAWUNG_ICON,
    icon_image=KAWUNG_ICON,
    size="large"
)

# Custom CSS termasuk pengaktifan Sticky Freeze yang aman untuk Light/Dark Mode
st.markdown("""
    <style>
    /* MENGATUR OVERFLOW PARENT AGAR STICKY BERHASIL DI STREAMLIT */
    [data-testid="stAppViewContainer"] {
        overflow: auto !important;
    }
    section.main {
        overflow: visible !important;
    }
    [data-testid="stMainBlockContainer"] {
        overflow: visible !important;
    }

    /* PADDING SIDEBAR */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] img {
        display: none !important;
    }
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        background: transparent !important;
    }

    /* SIDEBAR LOGO BADGE */
    .sidebar-logo-card {
        background-color: #ffffff !important;
        border-radius: 12px;
        padding: 10px 16px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12);
        margin-top: -10px;
        margin-bottom: 12px;
    }
    .brand-logo-card {
        width: 155px;
        height: auto;
        display: block;
        filter: none !important;
    }

    .sidebar-mini-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
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
        color: #334155;
        letter-spacing: 0.5px;
    }

    /* HEADER KONTEN UTAMA */
    .main-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(148, 163, 184, 0.3);
        margin-bottom: 16px;
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

    /* KARTU SERAGAM & ELEGAN (ROUNDED DESAIN) */
    .custom-card {
        background: rgba(30, 41, 59, 0.03);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-left: 4px solid #0284c7;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 6px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .custom-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .custom-card-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .custom-card-value {
        font-size: 15px;
        font-weight: 700;
        color: #0284c7;
    }

    /* TOMBOL FILTER METRIK BERGAYA CARD */
    div.stButton > button {
        background: rgba(30, 41, 59, 0.03) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 10px !important;
        padding: 10px !important;
        height: 100% !important;
        text-align: center !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        border-color: #0284c7 !important;
        background: rgba(2, 132, 199, 0.08) !important;
        transform: translateY(-2px);
    }

    /* FITUR FREEZE / STICKY KHUSUS BLOK DETAIL PENERBANGAN */
    div[data-testid="stVerticalBlock"] > div:has(#sticky-flight-marker) {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 3.5rem !important;
        z-index: 999 !important;
        background-color: var(--background-color, inherit) !important;
        backdrop-filter: blur(8px);
        padding-top: 14px !important;
        padding-bottom: 10px !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    }

    .section-header {
        font-size: 16px;
        font-weight: 700;
        margin-top: 8px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []
if "filter_status" not in st.session_state:
    st.session_state["filter_status"] = "ALL"

# -----------------------------------------------------------------------------
# 2. HELPER PARSER & RECONCILE ENGINE
# -----------------------------------------------------------------------------

def load_tapping_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame(), "-"

    filename = uploaded_file.name.lower()
    df = None
    flight_no = "-"
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
        
        for col in ["FLIGHT", "FLIGHT NO", "FLIGHT_NO", "FLIGHTNO", "NO FLIGHT"]:
            if col in df.columns:
                val = str(df[col].dropna().iloc[0]).strip() if not df[col].dropna().empty else "-"
                if val != "-":
                    flight_no = val
                    break
        return df, flight_no
    else:
        st.error(f"⚠️ File **{uploaded_file.name}** tidak terbaca atau kosong.")
        return pd.DataFrame(), "-"

def parse_manifest_pdf(pdf_file, airline):
    manifest_data = []
    flight_no_mnf = "-"
    flight_date_mnf = "-"
    flight_route_mnf = "-"
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            if flight_no_mnf == "-":
                fl_match = re.search(r"(?:FLIGHT|FLT|NO FLIGHT)\s*[:\.-]?\s*([A-Z0-9]{2,3}\s*\d{3,4})", text, re.IGNORECASE)
                if fl_match:
                    flight_no_mnf = fl_match.group(1).strip()
            
            if flight_date_mnf == "-":
                date_match = re.search(r"(?:DATE|TGL|TANGGAL)\s*[:\.-]?\s*(\d{1,2}[\/\-\s][A-Za-z0-9]{3,8}[\/\-\s]\d{2,4})", text, re.IGNORECASE)
                if date_match:
                    flight_date_mnf = date_match.group(1).strip()

            if flight_route_mnf == "-":
                route_match = re.search(r"(?:SECTOR|SEKTOR|ROUTE|RUTE)\s*[:\.-]?\s*([A-Z]{3}\s*[\-\/]\s*[A-Z]{3})", text, re.IGNORECASE)
                if route_match:
                    flight_route_mnf = route_match.group(1).replace(" ", "").strip()
                else:
                    alt_route = re.search(r"\b([A-Z]{3}[\-\/][A-Z]{3})\b", text)
                    if alt_route:
                        flight_route_mnf = alt_route.group(1).strip()

            lines = text.split("\n")
            for line in lines:
                pnr_match = re.search(r"\b([A-Z0-9]{6})\b", line)
                seat_match = re.search(r"\b([0-9]{1,2}[A-F])\b", line)
                name_match = re.search(r"([A-Z\s\/,\.-]+(?:MR|MRS|MS|MISS|MSTR|TITOHIR|PAX)?)", line)
                
                pnr = pnr_match.group(1) if pnr_match else None
                seat = seat_match.group(1) if seat_match else None
                
                type_pax = "Adult"
                if "CHD" in line or "CHILD" in line:
                    type_pax = "Child"
                elif "INF" in line or "INFANT" in line:
                    type_pax = "Infant"
                elif "TRANSIT" in line or "TRNS" in line:
                    type_pax = "Transit"

                if seat or pnr:
                    raw_name = name_match.group(1).strip() if name_match else line[:25].strip()
                    clean_name = re.sub(r"[^A-Z\s\/]", "", raw_name).strip()
                    if len(clean_name) > 3:
                        manifest_data.append({
                            "nama_manifest": clean_name,
                            "seat_manifest": seat if seat else "NO_SEAT",
                            "pnr_manifest": pnr if pnr else ("NO_PNR_LION" if "LION" in airline.upper() else "NO_PNR"),
                            "type_manifest": type_pax
                        })
                        
    return pd.DataFrame(manifest_data), flight_no_mnf, flight_date_mnf, flight_route_mnf

def reconcile_engine(df_tapping, df_manifest, airline_name):
    empty_columns = [
        "NO", "NAMA SCAN", "SEAT SCAN", "PNR SCAN", "TYPE SCAN",
        "NAMA MANIFEST", "SEAT MANIFEST", "PNR MANIFEST", "TYPE MANIFEST",
        "HASIL", "CATATAN"
    ]
    if df_tapping.empty and df_manifest.empty:
        return pd.DataFrame(columns=empty_columns)

    results = []
    has_manifest_pnr = not df_manifest["pnr_manifest"].str.contains("NO_PNR").all() if not df_manifest.empty else False
    
    no_counter = 1
    for idx, tap in df_tapping.iterrows():
        tap_nama = str(tap.get("NAMA", tap.get("NAMA PAX", tap.get("PASSENGER NAME", "")))).strip()
        tap_seat = str(tap.get("SEAT", tap.get("NO SEAT", ""))).strip()
        tap_pnr = str(tap.get("PNR", tap.get("NO PNR", ""))).strip()
        tap_type = str(tap.get("TYPE", tap.get("PAX TYPE", "Adult"))).strip()
        
        status = ""
        catatan = ""
        matched_nama_manifest = "-"
        matched_seat_manifest = "-"
        matched_pnr_manifest = "-"
        matched_type_manifest = "-"
        
        manifest_names = df_manifest["nama_manifest"].tolist() if not df_manifest.empty else []
        best_match = process.extractOne(tap_nama, manifest_names, scorer=fuzz.token_sort_ratio) if manifest_names else None
        
        if best_match and best_match[1] >= 75:
            match_row = df_manifest[df_manifest["nama_manifest"] == best_match[0]].iloc[0]
            mnf_nama = match_row["nama_manifest"]
            mnf_seat = match_row["seat_manifest"]
            mnf_pnr = match_row["pnr_manifest"]
            mnf_type = match_row["type_manifest"]
            
            matched_nama_manifest = mnf_nama
            matched_seat_manifest = mnf_seat
            matched_pnr_manifest = mnf_pnr
            matched_type_manifest = mnf_type
            
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
                status = "🟠 SEAT CONFLICT"
                catatan = f"Change Seat (Seat Manifest: {mnf_seat})" + pnr_note
            else:
                status = "🟠 SEAT CONFLICT"
                catatan = "Perlu Validasi Ground" + pnr_note
        else:
            status = "🔴 OFFLOAD"
            catatan = "Offload / Not in Manifest"
            
        results.append({
            "NO": no_counter,
            "NAMA SCAN": tap_nama,
            "SEAT SCAN": tap_seat,
            "PNR SCAN": tap_pnr,
            "TYPE SCAN": tap_type,
            "NAMA MANIFEST": matched_nama_manifest,
            "SEAT MANIFEST": matched_seat_manifest,
            "PNR MANIFEST": matched_pnr_manifest,
            "TYPE MANIFEST": matched_type_manifest,
            "HASIL": status,
            "CATATAN": catatan
        })
        no_counter += 1
        
    df_res = pd.DataFrame(results) if results else pd.DataFrame(columns=empty_columns)
    
    scanned_manifest_seats = df_res["SEAT MANIFEST"].tolist() if "SEAT MANIFEST" in df_res.columns else []
    no_show_list = []
    for idx, mnf in df_manifest.iterrows():
        if mnf["seat_manifest"] not in scanned_manifest_seats and mnf["seat_manifest"] != "NO_SEAT":
            no_show_list.append({
                "NO": no_counter,
                "NAMA SCAN": "-",
                "SEAT SCAN": "-",
                "PNR SCAN": "-",
                "TYPE SCAN": "-",
                "NAMA MANIFEST": mnf["nama_manifest"],
                "SEAT MANIFEST": mnf["seat_manifest"],
                "PNR MANIFEST": mnf["pnr_manifest"],
                "TYPE MANIFEST": mnf["type_manifest"],
                "HASIL": "⚪ NOT SCAN",
                "CATATAN": "Not Scanned / Ghost Pax"
            })
            no_counter += 1
            
    if no_show_list:
        df_res = pd.concat([df_res, pd.DataFrame(no_show_list)], ignore_index=True)
        
    return df_res

# -----------------------------------------------------------------------------
# 3. TAMPILAN SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
        <div class="sidebar-logo-card">
            <img src="{LOGO_GREY}" class="brand-logo-card" alt="InJourney Logo">
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
    # 4. TAMPILAN KONTEN UTAMA
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
        st.markdown(f'''
            <div class="sidebar-logo-card" style="margin-top: 0; padding: 8px 12px;">
                <img src="{LOGO_GREY}" class="brand-logo-card" style="width: 140px;" alt="InJourney Logo">
            </div>
        ''', unsafe_allow_html=True)

    if btn_proses:
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload di sidebar sebelah kiri sebelum memproses!")
        else:
            with st.spinner("⏳ Memproses ekstraksi data & mencocokkan kriteria..."):
                df_tap1, flight_scan1 = load_tapping_file(file_tapping1)
                
                if flight_mode == "Combine Flight":
                    df_tap2, flight_scan2 = load_tapping_file(file_tapping2)
                    if not df_tap1.empty and not df_tap2.empty:
                        df_tapping = pd.concat([df_tap1, df_tap2], ignore_index=True)
                    else:
                        df_tapping = pd.DataFrame()
                else:
                    df_tapping = df_tap1
                    flight_scan2 = "-"
                
                df_manifest, flight_no_mnf, flight_date_mnf, flight_route_mnf = parse_manifest_pdf(file_manifest, airline)
                
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

                    # =========================================================
                    # 1. DETAIL PENERBANGAN (STICKY FREEZE DENGAN MARKER AMAN)
                    # =========================================================
                    with st.container():
                        st.markdown('<div id="sticky-flight-marker"></div>', unsafe_allow_html=True)
                        st.markdown('<div class="section-header" style="margin-top:0;">✈️ Detail Penerbangan</div>', unsafe_allow_html=True)
                        
                        fc1, fc2, fc3, fc4, fc5, fc6, fc7 = st.columns(7)
                        with fc1:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">🏢 Airline</div>
                                    <div class="custom-card-value">{airline.split()[0]}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc2:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">📄 No Flight</div>
                                    <div class="custom-card-value">{flight_no_mnf}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc3:
                            st.markdown(f'''
                                <div class="custom-card" style="border-left-color: #eab308;">
                                    <div class="custom-card-label">📍 Rute</div>
                                    <div class="custom-card-value">{flight_route_mnf}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc4:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">📅 Tanggal</div>
                                    <div class="custom-card-value">{flight_date_mnf}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc5:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">📲 Scan 1</div>
                                    <div class="custom-card-value">{flight_scan1}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc6:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">📲 Scan 2</div>
                                    <div class="custom-card-value">{flight_scan2}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                        with fc7:
                            st.markdown(f'''
                                <div class="custom-card">
                                    <div class="custom-card-label">📌 Manifest</div>
                                    <div class="custom-card-value">{flight_no_mnf}</div>
                                </div>
                            ''', unsafe_allow_html=True)

                    st.write("")

                    # ---------------------------------------------------------
                    # 2. RINGKASAN HASIL REKONSILIASI
                    # ---------------------------------------------------------
                    st.markdown('<div class="section-header">📈 Ringkasan Hasil Rekonsiliasi</div>', unsafe_allow_html=True)
                    
                    cnt_scan = len(df_result[df_result["NAMA SCAN"] != "-"])
                    cnt_manifest = len(df_manifest)
                    cnt_match = len(df_result[df_result["HASIL"].str.contains("MATCH")])
                    cnt_offload = len(df_result[df_result["HASIL"].str.contains("OFFLOAD")])
                    cnt_seat_conflict = len(df_result[df_result["HASIL"].str.contains("SEAT CONFLICT")])
                    cnt_not_scan = len(df_result[df_result["HASIL"].str.contains("NOT SCAN")])

                    r_col1, r_col2, r_col3, r_col4, r_col5, r_col6 = st.columns(6)
                    with r_col1:
                        st.markdown(f'''
                            <div class="custom-card" style="border-left-color: #38bdf8;">
                                <div class="custom-card-label">📊 Pax Scan</div>
                                <div class="custom-card-value">{cnt_scan} Pax</div>
                            </div>
                        ''', unsafe_allow_html=True)
                    with r_col2:
                        st.markdown(f'''
                            <div class="custom-card" style="border-left-color: #a855f7;">
                                <div class="custom-card-label">📋 Pax Manifest</div>
                                <div class="custom-card-value">{cnt_manifest} Pax</div>
                            </div>
                        ''', unsafe_allow_html=True)
                    
                    if r_col3.button(f"🟢 MATCH\n\n{cnt_match} Pax", use_container_width=True):
                        st.session_state["filter_status"] = "MATCH"
                    if r_col4.button(f"🔴 OFFLOAD\n\n{cnt_offload} Pax", use_container_width=True):
                        st.session_state["filter_status"] = "OFFLOAD"
                    if r_col5.button(f"🟠 SEAT CONFLICT\n\n{cnt_seat_conflict} Pax", use_container_width=True):
                        st.session_state["filter_status"] = "SEAT CONFLICT"
                    if r_col6.button(f"⚪ NOT SCAN\n\n{cnt_not_scan} Pax", use_container_width=True):
                        st.session_state["filter_status"] = "NOT SCAN"

                    st.write("")

                    # ---------------------------------------------------------
                    # 3. RINGKASAN TYPE PAX
                    # ---------------------------------------------------------
                    st.markdown('<div class="section-header">👥 Ringkasan Type Pax</div>', unsafe_allow_html=True)
                    
                    scan_adult = len(df_result[(df_result["NAMA SCAN"] != "-") & (df_result["TYPE SCAN"].str.upper().str.contains("ADULT|ADT", na=False))])
                    scan_child = len(df_result[(df_result["NAMA SCAN"] != "-") & (df_result["TYPE SCAN"].str.upper().str.contains("CHILD|CHD", na=False))])
                    scan_infant = len(df_result[(df_result["NAMA SCAN"] != "-") & (df_result["TYPE SCAN"].str.upper().str.contains("INFANT|INF", na=False))])
                    scan_transit = len(df_result[(df_result["NAMA SCAN"] != "-") & (df_result["TYPE SCAN"].str.upper().str.contains("TRANSIT|TRNS", na=False))])

                    mnf_adult = len(df_manifest[df_manifest["type_manifest"].str.upper().str.contains("ADULT", na=False)])
                    mnf_child = len(df_manifest[df_manifest["type_manifest"].str.upper().str.contains("CHILD", na=False)])
                    mnf_infant = len(df_manifest[df_manifest["type_manifest"].str.upper().str.contains("INFANT", na=False)])
                    mnf_transit = len(df_manifest[df_manifest["type_manifest"].str.upper().str.contains("TRANSIT", na=False)])

                    pax_col1, pax_col2 = st.columns(2)
                    
                    with pax_col1:
                        with st.container(border=True):
                            st.markdown('<div style="font-size: 14px; font-weight: 700; color: #0284c7; margin-bottom: 8px;">📲 DATA SCAN</div>', unsafe_allow_html=True)
                            ps1, ps2, ps3, ps4 = st.columns(4)
                            ps1.metric("Adult Scan", f"{scan_adult}")
                            ps2.metric("Child Scan", f"{scan_child}")
                            ps3.metric("Infant Scan", f"{scan_infant}")
                            ps4.metric("Transit Scan", f"{scan_transit}")

                    with pax_col2:
                        with st.container(border=True):
                            st.markdown('<div style="font-size: 14px; font-weight: 700; color: #a855f7; margin-bottom: 8px;">📋 DATA MANIFEST</div>', unsafe_allow_html=True)
                            pm1, pm2, pm3, pm4 = st.columns(4)
                            pm1.metric("Adult Mnf", f"{mnf_adult}")
                            pm2.metric("Child Mnf", f"{mnf_child}")
                            pm3.metric("Infant Mnf", f"{mnf_infant}")
                            pm4.metric("Transit Mnf", f"{mnf_transit}")

                    # ---------------------------------------------------------
                    # 4. DETAIL PENCOCOKAN PENUMPANG (TABEL UTAMA)
                    # ---------------------------------------------------------
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.markdown(f'<div class="section-header">📋 Detail Pencocokan Penumpang <span style="font-size: 14px; font-weight: normal; color: #0284c7;">(Filter Active: {st.session_state["filter_status"]})</span></div>', unsafe_allow_html=True)
                    with col_t2:
                        if st.button("🔄 Reset Filter Tabel", use_container_width=True):
                            st.session_state["filter_status"] = "ALL"

                    df_display = df_result.copy()
                    if st.session_state["filter_status"] != "ALL":
                        df_display = df_display[df_display["HASIL"].str.contains(st.session_state["filter_status"])]

                    st.dataframe(df_display, use_container_width=True, height=500)
                    
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

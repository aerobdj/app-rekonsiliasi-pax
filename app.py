import streamlit as st
import pandas as pd
import pdfplumber
import re
from rapidfuzz import fuzz, process
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN & BRANDING INJOURNEY
# -----------------------------------------------------------------------------
LOGO_WHITE = "https://www.injourneyairports.id/assets/injourney-logo-white-Dl4T6LNj.png"
KAWUNG_ICON = "https://www.injourneyairports.id/assets/kawung-logo-side-CktPU2GK.png"

st.set_page_config(
    page_title="InJourney Airports - Pax Reconciliation System",
    page_icon=KAWUNG_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk Posisi Logo Center-Top & Tombol Collapse Pojok Kanan Sidebar
st.markdown("""
    <style>
    /* PADDING AWAL SIDEBAR */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }

    /* MENENGAHKAN LOGO DI PALING ATAS (CENTER-TOP) */
    [data-testid="stSidebarHeader"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding-top: 1.2rem !important;
        padding-bottom: 0.5rem !important;
        width: 100% !important;
    }
    
    /* UKURAN LOGO MEMBESAR GAGAH */
    [data-testid="stSidebarHeader"] img {
        max-height: 65px !important;
        width: auto !important;
        margin: 0 auto !important;
    }

    /* MEMINDAHKAN TOMBOL HIDE SIDEBAR (<<) KE POJOK KANAN DILUAR ALUR LOGO */
    [data-testid="stSidebarCollapseButton"] {
        position: absolute !important;
        right: 8px !important;
        top: 8px !important;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    }
    [data-testid="stSidebarCollapseButton"]:hover {
        opacity: 1.0;
    }

    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 15px;
        border-bottom: 2px solid #334155;
        margin-bottom: 20px;
    }
    .main-title {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
        font-size: 26px;
        margin: 0;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(30, 41, 59, 0.5);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
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
        border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []

# Menggunakan fitur resmi st.logo yang sekarang sudah diatur CSS-nya menjadi Center-Top
st.logo(
    image=LOGO_WHITE,
    icon_image=KAWUNG_ICON,
    size="large"
)

# -----------------------------------------------------------------------------
# 2. HELPER PARSER (PDF MANIFEST & MULTI-FORMAT TAPPING)
# -----------------------------------------------------------------------------

def parse_manifest_pdf(pdf_file, airline):
    """Mengekstrak data Nama, Seat, PNR dari PDF Manifest."""
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

def load_tapping_file(uploaded_file):
    """Membaca file Tapping dalam format CSV, XLSX, XLS, atau TXT."""
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        elif filename.endswith(".txt"):
            df = pd.read_csv(uploaded_file, sep="\t")
            if len(df.columns) <= 1:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=",")
            if len(df.columns) <= 1:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=";")
        else:
            st.error("Format file tapping tidak didukung!")
            return None
    except Exception as e:
        st.error(f"Gagal membaca file tapping ({filename}): {e}")
        return None
    
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df

# -----------------------------------------------------------------------------
# 3. ENGINE MATCHING
# -----------------------------------------------------------------------------

def reconcile_engine(df_tapping, df_manifest, airline_name):
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
            
            if not has_manifest_pnr:
                pnr_note = " (PNR diganti No Ticket)" if "LION" in airline_name.upper() else " (PNR di manifest tidak tersedia)"
            else:
                pnr_note = ""

            if is_seat_same and is_pnr_same:
                status = "🟢 MATCH"
                catatan = "Match Perfect" + pnr_note
            elif is_seat_same and not is_pnr_same:
                status = "🟡 MATCH"
                catatan = "PNR Berbeda" + pnr_note
            elif not is_seat_same and is_pnr_same:
                status = "🟡 MATCH"
                catatan = f"Change Seat (Seat Manifest: {mnf_seat})" + pnr_note
            elif not is_seat_same and not is_pnr_same:
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
        
    df_res = pd.DataFrame(results)
    
    scanned_manifest_seats = df_res["Seat Manifest"].tolist()
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
# 4. TAMPILAN SIDEBAR
# -----------------------------------------------------------------------------

with st.sidebar:
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
    # 5. HALAMAN UTAMA
    # -------------------------------------------------------------------------
    
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.markdown("""
            <div class="main-header">
                <div>
                    <h1 class="main-title">Passenger Reconciliation System</h1>
                    <div class="sub-title">Sistem Rekonsiliasi Data Tapping Gate vs Passenger Manifest</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_head2:
        st.image(LOGO_WHITE, width=200)

    if btn_proses:
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload di sidebar sebelum memproses!")
        else:
            with st.spinner("⏳ Memproses ekstraksi data & mencocokkan kriteria..."):
                df_tap1 = load_tapping_file(file_tapping1)
                if flight_mode == "Combine Flight":
                    df_tap2 = load_tapping_file(file_tapping2)
                    df_tapping = pd.concat([df_tap1, df_tap2], ignore_index=True)
                else:
                    df_tapping = df_tap1
                    
                df_manifest = parse_manifest_pdf(file_manifest, airline)
                df_result = reconcile_engine(df_tapping, df_manifest, airline)
                
                st.session_state["history"].append({
                    "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "airline": airline,
                    "mode": flight_mode,
                    "total_pax": len(df_result),
                    "data": df_result
                })

            st.markdown("### 📈 Ringkasan Rekonsiliasi")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Penumpang", f"{len(df_result)} Pax")
            col2.metric("🟢 Perfect Match", f"{len(df_result[df_result['Status'] == '🟢 MATCH'])} Pax")
            col3.metric("🟡 Match Catatan", f"{len(df_result[df_result['Status'] == '🟡 MATCH'])} Pax")
            col4.metric("🚨 Alert / Unmatched", f"{len(df_result[df_result['Status'].isin(['🔴 NOT MATCH', '🚨 UNMATCHED'])])} Pax")
            
            st.write("")
            st.markdown("### 📋 Detail Hasil Match")
            
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
        st.info("👈 Silakan atur maskapai, mode penerbangan, dan upload dokumen pada **Sidebar sebelah kiri**, lalu klik **MULAI REKONSILIASI**.")

elif menu == "📜 Histori Log":
    st.title("📜 Histori Log Rekonsiliasi")
    st.caption("Daftar riwayat pemrosesan data rekonsiliasi pada sesi ini.")
    
    if len(st.session_state["history"]) == 0:
        st.warning("Belum ada riwayat rekonsiliasi yang dilakukan.")
    else:
        for idx, item in enumerate(reversed(st.session_state["history"])):
            with st.expander(f"🕒 {item['time']} — {item['airline']} ({item['mode']}) — Total: {item['total_pax']} Pax"):
                st.dataframe(item["data"], use_container_width=True)

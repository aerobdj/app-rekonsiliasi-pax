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

# Custom CSS
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        overflow: auto !important;
    }
    section.main {
        overflow: visible !important;
    }
    [data-testid="stMainBlockContainer"] {
        overflow: visible !important;
    }

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

    div[data-testid="stVerticalBlock"] > div:has(#sticky-flight-marker) {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 3.5rem !important;
        z-index: 999 !important;
        background-color: var(--background-color, inherit) !important;
        backdrop-filter: blur(12px);
        padding-top: 14px !important;
        padding-bottom: 10px !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    }

    .section-header {
        font-size: 16px;
        font-weight: 700;
        margin-top: 4px;
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
if "reconcile_done" not in st.session_state:
    st.session_state["reconcile_done"] = False

# -----------------------------------------------------------------------------
# 2. HELPER NAMA & PARSER DOKUMEN
# -----------------------------------------------------------------------------

def clean_passenger_name(name):
    """
    Pembersihan Gelar Penumpang (MR, MRS, MS, MSTR, MISS, SE, dll) dan Karakter Pengganggu.
    Mendukung pembalikan nama dari LASTNAME,FIRSTNAME -> FIRSTNAME LASTNAME
    """
    if not name or name == "-":
        return ""
    name_str = str(name).upper().strip()
    
    # Menangani format LASTNAME,FIRSTNAME
    if "," in name_str:
        parts = name_str.split(",")
        if len(parts) >= 2:
            lname = parts[0].strip()
            fname = parts[1].strip()
            name_str = f"{fname} {lname}"

    name_str = name_str.replace("/", " ")
    name_str = re.sub(r"([A-Z]+)(MR|MRS|MS|MSTR|MISS)\b", r"\1 ", name_str)
    
    titles = [
        r"\bMR\b", r"\bMRS\b", r"\bMS\b", r"\bMSTR\b", r"\bMISS\b", 
        r"\bMR\.\b", r"\bMRS\.\b", r"\bMS\.\b", r"\bSE\b", r"\bST\b"
    ]
    for t in titles:
        name_str = re.sub(t, "", name_str)
        
    name_str = re.sub(r"[^A-Z\s]", "", name_str)
    return " ".join(name_str.split())

def determine_pax_type(type_val, is_transit=False):
    """
    Penentuan Format Tipe Penumpang
    """
    t = str(type_val).strip().upper()
    if "INFANT" in t or "INF" in t:
        return "Infant (Transit)" if is_transit else "Infant"
    elif "CHILD" in t or "CHD" in t:
        return "Child (Transit)" if is_transit else "Child"
    else:
        return "Adult (Transit)" if is_transit else "Adult"

def load_tapping_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame(), "-"

    filename = uploaded_file.name.lower()
    df = None
    flight_no = "-"
    encodings = ["utf-8", "latin1", "iso-8859-1", "cp1252", "utf-16"]

    if filename.endswith((".xlsx", ".xls")):
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        except Exception:
            df = None

    if df is None or df.empty:
        try:
            uploaded_file.seek(0)
            tables = pd.read_html(uploaded_file)
            if tables and len(tables) > 0:
                df = tables[0]
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
        st.error(f"⚠️ File **{uploaded_file.name}** tidak berhasil terbaca atau kosong.")
        return pd.DataFrame(), "-"

# -----------------------------------------------------------------------------
# PARSER 1: LION GROUP
# -----------------------------------------------------------------------------

def parse_manifest_lion_group(pdf_file):
    manifest_data = []
    flight_no_mnf = "-"
    flight_date_mnf = "-"
    origin = "-"
    destination = "-"
    
    full_text = ""
    if hasattr(pdf_file, "name") and pdf_file.name.endswith(".txt"):
        full_text = pdf_file.getvalue().decode("utf-8", errors="ignore")
    else:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception:
            pdf_file.seek(0)
            full_text = pdf_file.read().decode("utf-8", errors="ignore")

    fl_match = re.search(r"FLIGHT\s*[:\.-]?\s*([A-Z0-9]{2,3}\s*\d{3,4})", full_text, re.IGNORECASE)
    if fl_match:
        flight_no_mnf = fl_match.group(1).strip()
        
    date_match = re.search(r"DATE\s*[:\.-]?\s*(\d{1,2}[A-Z]{3}\d{2})", full_text, re.IGNORECASE)
    if date_match:
        flight_date_mnf = date_match.group(1).strip()

    emb_match = re.search(r"PT\.OF\s*EMBARKATION\s*[:\.-]?\s*([A-Z]{3})", full_text, re.IGNORECASE)
    if emb_match:
        origin = emb_match.group(1).strip()

    dest_match = re.search(r"PT\.OF\s*DEST\s*[:\.-]?\s*([A-Z]{3})", full_text, re.IGNORECASE)
    if dest_match:
        destination = dest_match.group(1).strip()

    flight_route_mnf = f"{origin}-{destination}" if origin != "-" and destination != "-" else "-"

    lines = full_text.split("\n")
    for line in lines:
        parts = line.split("/")
        if len(parts) >= 8:
            lname = re.sub(r"^[0-9\s]+", "", parts[0]).strip()
            fname = parts[1].strip() if len(parts) > 1 else ""
            raw_full_name = f"{fname} {lname}".strip()
            
            if "FNAME" in fname.upper() or "LNAME" in lname.upper() or "TYPE" in line.upper():
                continue

            clean_name = clean_passenger_name(raw_full_name)
            
            seat = "-"
            for part in parts:
                p_str = part.strip().replace(".", "")
                if re.match(r"^[0-9]{1,2}[A-F]$", p_str):
                    seat = p_str
                    break

            tkt_no = "NO_PNR_LION"
            for part in parts:
                part_clean = part.strip()
                if part_clean.isdigit() and len(part_clean) >= 10:
                    tkt_no = part_clean
                    break

            in_flt = parts[8].strip() if len(parts) > 8 else "..."
            tr_org = parts[9].strip() if len(parts) > 9 else "..."
            special_val = parts[-1].strip() if len(parts) > 0 else ""

            is_in_flt_valid = (in_flt != "..." and not re.match(r"^\.+$", in_flt) and in_flt != "")
            is_tr_org_valid = (tr_org != "..." and not re.match(r"^\.+$", tr_org) and tr_org != "")
            is_transit = is_in_flt_valid or is_tr_org_valid

            base_type = "Adult"
            if "INF" in special_val or "INFANT" in line.upper():
                base_type = "Infant"
            elif "CHD" in special_val or "CHILD" in line.upper():
                base_type = "Child"

            type_pax_final = determine_pax_type(base_type, is_transit)

            if len(clean_name) > 2:
                manifest_data.append({
                    "raw_nama_manifest": raw_full_name,
                    "clean_nama_manifest": clean_name,
                    "seat_manifest": seat,
                    "pnr_manifest": tkt_no,
                    "type_manifest": type_pax_final,
                    "section": "BOARDED",
                    "is_matched": False
                })

    return pd.DataFrame(manifest_data), flight_no_mnf, flight_date_mnf, flight_route_mnf

# -----------------------------------------------------------------------------
# PARSER 2: CITILINK (QG)
# -----------------------------------------------------------------------------

def parse_manifest_citilink(pdf_file):
    manifest_data = []
    flight_no_mnf = "-"
    flight_date_mnf = "-"
    origin = "-"
    destination = "-"
    
    full_text = ""
    if hasattr(pdf_file, "name") and pdf_file.name.endswith(".txt"):
        full_text = pdf_file.getvalue().decode("utf-8", errors="ignore")
    else:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception:
            pdf_file.seek(0)
            full_text = pdf_file.read().decode("utf-8", errors="ignore")

    # Header Extraction Citilink
    # Contoh: Flight: 487 BDJSUB Date: 22Jul26/1155
    fl_match = re.search(r"Flight\s*[:\.-]?\s*(\d{3,4})\s+([A-Z]{6})", full_text, re.IGNORECASE)
    if fl_match:
        fl_num = fl_match.group(1).strip()
        route_raw = fl_match.group(2).strip()
        flight_no_mnf = f"QG {fl_num}"
        if len(route_raw) == 6:
            origin = route_raw[:3]
            destination = route_raw[3:]
    else:
        fl_simple = re.search(r"Flight\s*[:\.-]?\s*(\d{3,4})", full_text, re.IGNORECASE)
        if fl_simple:
            flight_no_mnf = f"QG {fl_simple.group(1).strip()}"

    date_match = re.search(r"Date\s*[:\.-]?\s*(\d{1,2}[A-Za-z]{3}\d{2})", full_text, re.IGNORECASE)
    if date_match:
        flight_date_mnf = date_match.group(1).upper()

    flight_route_mnf = f"{origin}-{destination}" if origin != "-" and destination != "-" else "-"

    # Parsing Line by Line Citilink
    lines = full_text.split("\n")
    current_section = "BOARDED"  # Default section
    
    for line in lines:
        line_str = line.strip()
        
        # Penentuan Section
        if "Checked-in/Boarded:" in line_str and "Thru" not in line_str:
            current_section = "BOARDED"
            continue
        elif "No Shows:" in line_str and "Thru" not in line_str:
            current_section = "NO_SHOW"
            continue
        elif "Thru Checked-in/Boarded" in line_str:
            current_section = "THRU_BOARDED"
            continue
        elif "Thru No Shows" in line_str:
            current_section = "THRU_NO_SHOW"
            continue

        # Parsing Baris Infant khusus Citilink: INFT: YUSRON,SHAQUIRA TSABINA
        if "INFT:" in line_str:
            infant_raw = line_str.replace("INFT:", "").strip()
            clean_name = clean_passenger_name(infant_raw)
            is_transit = (current_section in ["THRU_BOARDED", "THRU_NO_SHOW"])
            pax_type = determine_pax_type("Infant", is_transit)
            
            if len(clean_name) > 2:
                manifest_data.append({
                    "raw_nama_manifest": infant_raw,
                    "clean_nama_manifest": clean_name,
                    "seat_manifest": "INF",
                    "pnr_manifest": "NO_PNR_CITILINK",
                    "type_manifest": pax_type,
                    "section": current_section,
                    "is_matched": False
                })
            continue

        # Parsing Baris Penumpang Utama Citilink
        # Contoh: 1 RIKI,MUHAMMAD VG5L4Z P 34 21JUL26 1E 0SUB 487
        # Contoh Thru: 1 Abdullah,Dicky HF28ST L 89 30Jun26 29B 1SUB 771
        match_pax = re.search(r"^\d+\s+([A-Za-z\s,\.-]+?)\s+([A-Z0-9]{6})\s+[A-Z]\s+\d+\s+\d+[A-Za-z]{3}\d{2}\s*([0-9]{1,2}[A-F])?", line_str)
        if match_pax:
            raw_name = match_pax.group(1).strip()
            pnr_val = match_pax.group(2).strip()
            seat_val = match_pax.group(3).strip() if match_pax.group(3) else "-"

            clean_name = clean_passenger_name(raw_name)
            is_transit = (current_section in ["THRU_BOARDED", "THRU_NO_SHOW"])
            pax_type = determine_pax_type("Adult", is_transit)

            if len(clean_name) > 2:
                manifest_data.append({
                    "raw_nama_manifest": raw_name,
                    "clean_nama_manifest": clean_name,
                    "seat_manifest": seat_val,
                    "pnr_manifest": pnr_val,
                    "type_manifest": pax_type,
                    "section": current_section,
                    "is_matched": False
                })

    return pd.DataFrame(manifest_data), flight_no_mnf, flight_date_mnf, flight_route_mnf

# -----------------------------------------------------------------------------
# 3. RECONCILE ENGINE DENGAN PRESISI TINGGI & HANDLING CITILINK CONFIRMATION
# -----------------------------------------------------------------------------

def reconcile_engine(df_tapping, df_manifest, airline_name):
    empty_columns = [
        "NO", "NAMA SCAN", "SEAT SCAN", "PNR SCAN", "TYPE SCAN",
        "NAMA MANIFEST", "SEAT MANIFEST", "PNR MANIFEST", "TYPE MANIFEST",
        "HASIL", "CATATAN"
    ]
    if df_tapping.empty and df_manifest.empty:
        return pd.DataFrame(columns=empty_columns)

    results = []
    no_counter = 1
    
    df_manifest["is_matched"] = False
    is_citilink = "CITILINK" in airline_name.upper()

    for idx, tap in df_tapping.iterrows():
        tap_nama_raw = str(tap.get("NAME", tap.get("NAMA", tap.get("PASSENGER NAME", "")))).strip()
        tap_seat = str(tap.get("SEAT", tap.get("NO SEAT", ""))).strip().replace(".", "")
        tap_pnr = str(tap.get("PNR", tap.get("NO PNR", ""))).strip()
        
        raw_type = str(tap.get("TYPE", tap.get("PAX TYPE", "Adult"))).strip()
        raw_cat = str(tap.get("CATEGORY", "")).strip()
        
        is_transit = "TRANSIT" in raw_cat.upper() or "TRANSIT" in raw_type.upper()
        tap_type_final = determine_pax_type(raw_type, is_transit)
        tap_nama_clean = clean_passenger_name(tap_nama_raw)
        
        status = ""
        catatan = ""
        matched_idx = None
        
        available_manifest = df_manifest[~df_manifest["is_matched"]]
        
        # STRATEGI 1: Match Presisi via SEAT SAMA + FUZZY NAMA (Min. 70% Kemiripan)
        if tap_seat != "-" and tap_seat != "INF" and not available_manifest.empty:
            same_seat_rows = available_manifest[available_manifest["seat_manifest"] == tap_seat]
            for m_idx, m_row in same_seat_rows.iterrows():
                score = fuzz.token_set_ratio(tap_nama_clean, m_row["clean_nama_manifest"])
                if score >= 70:
                    matched_idx = m_idx
                    break
        
        # STRATEGI 2: Fuzzy Name Match Keseluruhan (Minimal 72% Kemiripan)
        if matched_idx is None and not available_manifest.empty:
            best_score = 0
            best_m_idx = None
            for m_idx, m_row in available_manifest.iterrows():
                score = fuzz.token_set_ratio(tap_nama_clean, m_row["clean_nama_manifest"])
                if score > best_score and score >= 72:
                    best_score = score
                    best_m_idx = m_idx
            if best_m_idx is not None:
                matched_idx = best_m_idx

        # OLAH HASIL PENCOCOKAN
        if matched_idx is not None:
            df_manifest.at[matched_idx, "is_matched"] = True
            match_row = df_manifest.loc[matched_idx]
            
            mnf_nama = match_row["clean_nama_manifest"]
            mnf_seat = match_row["seat_manifest"]
            mnf_pnr = match_row["pnr_manifest"]
            mnf_type = match_row["type_manifest"]
            mnf_section = match_row.get("section", "BOARDED")
            
            is_seat_same = (tap_seat == mnf_seat) or (tap_seat == "INF" and mnf_seat == "INF") or (tap_seat == "INF" and mnf_seat == "-")
            pnr_note = " (PNR diganti No Ticket)" if len(mnf_pnr) > 6 else ""

            # Khusus Citilink: Cek apakah penumpang ada di daftar No Shows / Thru No Shows
            if mnf_section in ["NO_SHOW", "THRU_NO_SHOW"]:
                status = "🔴 OFFLOAD"
                catatan = "Offload / No Show Manifest" if mnf_section == "NO_SHOW" else "Offload Transit"
            elif is_seat_same:
                status = "🟢 MATCH"
                catatan = "Match Perfect" + pnr_note
            else:
                status = "🟠 SEAT CONFLICT"
                catatan = f"Change Seat (Seat Manifest: {mnf_seat})" + pnr_note

            results.append({
                "NO": no_counter,
                "NAMA SCAN": tap_nama_raw,
                "SEAT SCAN": tap_seat,
                "PNR SCAN": tap_pnr,
                "TYPE SCAN": tap_type_final,
                "NAMA MANIFEST": mnf_nama,
                "SEAT MANIFEST": mnf_seat,
                "PNR MANIFEST": mnf_pnr,
                "TYPE MANIFEST": mnf_type,
                "HASIL": status,
                "CATATAN": catatan
            })
        else:
            # KETENTUAN KHUSUS SEAT INF (INFANT) ATAU CONFIRMATION CITILINK
            if tap_seat == "INF" or "INFANT" in tap_type_final.upper():
                status = "👶 INFANT"
                catatan = "Pax Infant"
            elif is_citilink:
                status = "🟨 CONFIRMATION"
                catatan = "Confirmation required"
            else:
                status = "🔴 OFFLOAD"
                catatan = "Offload / Not in Manifest"

            results.append({
                "NO": no_counter,
                "NAMA SCAN": tap_nama_raw,
                "SEAT SCAN": tap_seat,
                "PNR SCAN": tap_pnr,
                "TYPE SCAN": tap_type_final,
                "NAMA MANIFEST": "-",
                "SEAT MANIFEST": "-",
                "PNR MANIFEST": "-",
                "TYPE MANIFEST": "-",
                "HASIL": status,
                "CATATAN": catatan
            })
        no_counter += 1

    # TAMBAHKAN PENUMPANG MANIFEST YANG BELUM DI-SCAN (NOT SCAN)
    unscanned_manifest = df_manifest[~df_manifest["is_matched"]]
    for m_idx, mnf in unscanned_manifest.iterrows():
        mnf_sec = mnf.get("section", "BOARDED")
        cat_not_scan = "Passenger No Show and did not scan" if mnf_sec in ["NO_SHOW", "THRU_NO_SHOW"] else "Not Scanned / Ghost Pax"
        
        results.append({
            "NO": no_counter,
            "NAMA SCAN": "-",
            "SEAT SCAN": "-",
            "PNR SCAN": "-",
            "TYPE SCAN": "-",
            "NAMA MANIFEST": mnf["clean_nama_manifest"],
            "SEAT MANIFEST": mnf["seat_manifest"],
            "PNR MANIFEST": mnf["pnr_manifest"],
            "TYPE MANIFEST": mnf["type_manifest"],
            "HASIL": "⚪ NOT SCAN",
            "CATATAN": cat_not_scan
        })
        no_counter += 1

    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# 4. TAMPILAN SIDEBAR APLIKASI
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
        if st.button("🚀 MULAI REKONSILIASI", use_container_width=True):
            st.session_state["reconcile_done"] = True
            st.session_state["filter_status"] = "ALL"

    # -------------------------------------------------------------------------
    # 5. TAMPILAN KONTEN UTAMA
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

    if st.session_state.get("reconcile_done", False):
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload di sidebar sebelah kiri sebelum memproses!")
        else:
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
            
            if "CITILINK" in airline.upper() or "QG" in airline.upper():
                df_manifest, flight_no_mnf, flight_date_mnf, flight_route_mnf = parse_manifest_citilink(file_manifest)
            elif "LION" in airline.upper():
                df_manifest, flight_no_mnf, flight_date_mnf, flight_route_mnf = parse_manifest_lion_group(file_manifest)
            else:
                df_manifest, flight_no_mnf, flight_date_mnf, flight_route_mnf = parse_manifest_lion_group(file_manifest)
            
            if df_tapping.empty:
                st.error("❌ Proses dibatalkan karena data Tapping tidak berhasil terbaca/kosong.")
            elif df_manifest.empty:
                st.error("❌ Proses dibatalkan karena data Manifest PDF/TXT tidak berhasil terbaca/kosong.")
            else:
                df_result = reconcile_engine(df_tapping, df_manifest, airline)
                manifest_card_val = f"{flight_no_mnf} ({flight_route_mnf})"

                # DETAIL PENERBANGAN
                with st.container():
                    st.markdown('<div id="sticky-flight-marker"></div>', unsafe_allow_html=True)
                    st.markdown('<div class="section-header" style="margin-top:0;">✈️ Detail Penerbangan</div>', unsafe_allow_html=True)
                    
                    fc1, fc2, fc3, fc4, fc5, fc6, fc7 = st.columns(7)
                    with fc1:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">🏢 Airline</div><div class="custom-card-value">{airline.split()[0]}</div></div>', unsafe_allow_html=True)
                    with fc2:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">📄 No Flight</div><div class="custom-card-value">{flight_no_mnf}</div></div>', unsafe_allow_html=True)
                    with fc3:
                        st.markdown(f'<div class="custom-card" style="border-left-color: #eab308;"><div class="custom-card-label">📍 Rute</div><div class="custom-card-value">{flight_route_mnf}</div></div>', unsafe_allow_html=True)
                    with fc4:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">📅 Tanggal</div><div class="custom-card-value">{flight_date_mnf}</div></div>', unsafe_allow_html=True)
                    with fc5:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">📲 Scan 1</div><div class="custom-card-value">{flight_scan1}</div></div>', unsafe_allow_html=True)
                    with fc6:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">📲 Scan 2</div><div class="custom-card-value">{flight_scan2}</div></div>', unsafe_allow_html=True)
                    with fc7:
                        st.markdown(f'<div class="custom-card"><div class="custom-card-label">📌 Manifest</div><div class="custom-card-value">{manifest_card_val}</div></div>', unsafe_allow_html=True)

                st.write("")

                # RINGKASAN REKONSILIASI
                st.markdown('<div class="section-header">📈 Ringkasan Hasil Rekonsiliasi</div>', unsafe_allow_html=True)
                
                cnt_scan = len(df_result[df_result["NAMA SCAN"] != "-"])
                cnt_manifest = len(df_manifest)
                cnt_match = len(df_result[df_result["HASIL"].str.contains("MATCH")])
                cnt_offload = len(df_result[df_result["HASIL"].str.contains("OFFLOAD")])
                cnt_seat_conflict = len(df_result[df_result["HASIL"].str.contains("SEAT CONFLICT")])
                cnt_not_scan = len(df_result[df_result["HASIL"].str.contains("NOT SCAN")])
                cnt_infant = len(df_result[df_result["HASIL"].str.contains("INFANT")])
                cnt_confirm = len(df_result[df_result["HASIL"].str.contains("CONFIRMATION")])

                r_col1, r_col2, r_col3, r_col4, r_col5, r_col6, r_col7, r_col8 = st.columns(8)
                with r_col1:
                    st.markdown(f'<div class="custom-card" style="border-left-color: #38bdf8;"><div class="custom-card-label">📊 Pax Scan</div><div class="custom-card-value">{cnt_scan} Pax</div></div>', unsafe_allow_html=True)
                with r_col2:
                    st.markdown(f'<div class="custom-card" style="border-left-color: #a855f7;"><div class="custom-card-label">📋 Pax Manifest</div><div class="custom-card-value">{cnt_manifest} Pax</div></div>', unsafe_allow_html=True)
                
                if r_col3.button(f"🟢 MATCH\n\n{cnt_match} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "MATCH"
                    st.rerun()
                if r_col4.button(f"🔴 OFFLOAD\n\n{cnt_offload} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "OFFLOAD"
                    st.rerun()
                if r_col5.button(f"🟠 SEAT CONFLICT\n\n{cnt_seat_conflict} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "SEAT CONFLICT"
                    st.rerun()
                if r_col6.button(f"⚪ NOT SCAN\n\n{cnt_not_scan} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "NOT SCAN"
                    st.rerun()
                if r_col7.button(f"👶 INFANT\n\n{cnt_infant} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "INFANT"
                    st.rerun()
                if r_col8.button(f"🟨 CONFIRM\n\n{cnt_confirm} Pax", use_container_width=True):
                    st.session_state["filter_status"] = "CONFIRMATION"
                    st.rerun()

                st.write("")

                # RINGKASAN TYPE PAX
                st.markdown('<div class="section-header">👥 Ringkasan Type Pax</div>', unsafe_allow_html=True)
                
                df_scan_only = df_result[df_result["NAMA SCAN"] != "-"]
                scan_adult = len(df_scan_only[df_scan_only["TYPE SCAN"].str.contains("Adult")])
                scan_child = len(df_scan_only[df_scan_only["TYPE SCAN"].str.contains("Child")])
                scan_infant = len(df_scan_only[df_scan_only["TYPE SCAN"].str.contains("Infant")])
                scan_transit = len(df_scan_only[df_scan_only["TYPE SCAN"].str.contains("Transit")])

                mnf_adult = len(df_manifest[df_manifest["type_manifest"].str.contains("Adult")])
                mnf_child = len(df_manifest[df_manifest["type_manifest"].str.contains("Child")])
                mnf_infant = len(df_manifest[df_manifest["type_manifest"].str.contains("Infant")])
                mnf_transit = len(df_manifest[df_manifest["type_manifest"].str.contains("Transit")])

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

                # TABEL DETAIL UTAMA
                col_t1, col_t2 = st.columns([3, 1])
                with col_t1:
                    st.markdown(f'<div class="section-header">📋 Detail Pencocokan Penumpang <span style="font-size: 14px; font-weight: normal; color: #0284c7;">(Filter Active: {st.session_state["filter_status"]})</span></div>', unsafe_allow_html=True)
                with col_t2:
                    if st.button("🔄 Reset Filter Tabel", use_container_width=True):
                        st.session_state["filter_status"] = "ALL"
                        st.rerun()

                df_display = df_result.copy()
                if st.session_state["filter_status"] != "ALL":
                    df_display = df_display[df_display["HASIL"].str.contains(st.session_state["filter_status"])]

                st.dataframe(df_display, use_container_width=True, height=500, hide_index=True)
                
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
            </div>
        """, unsafe_allow_html=True)

elif menu == "📜 Histori Log":
    st.title("📜 Histori Log Rekonsiliasi")
    if len(st.session_state["history"]) == 0:
        st.warning("Belum ada riwayat rekonsiliasi yang dilakukan pada sesi ini.")
    else:
        for idx, item in enumerate(reversed(st.session_state["history"])):
            with st.expander(f"🕒 {item['time']} — {item['airline']} ({item['mode']}) — Total: {item['total_pax']} Pax"):
                st.dataframe(item["data"], use_container_width=True, hide_index=True)

import streamlit as st
import pandas as pd
import pdfplumber
import re
from rapidfuzz import fuzz, process
import io

# 1. KONFIGURASI HALAMAN STREAMLIT
st.set_page_config(
    page_title="App Rekonsiliasi Pax",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi Session State untuk Histori
if "history" not in st.session_state:
    st.session_state["history"] = []

# -----------------------------------------------------------------------------
# 2. HELPER & PARSER REGEX MANIFEST
# -----------------------------------------------------------------------------

def parse_manifest_pdf(pdf_file, airline):
    """Mengekstrak data Nama, Seat, PNR dari PDF Manifest menggunakan RegEx."""
    manifest_data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split("\n")
            for line in lines:
                # Pola Umum: Mencari Nama, PNR (6 karakter), dan Seat (misal: 12A, 017F)
                # Contoh: ABDILAH/SAYUTITOHIR MR M7DC5S 017F
                pnr_match = re.search(r"\b([A-Z0-9]{6})\b", line)
                seat_match = re.search(r"\b([0-9]{1,2}[A-F])\b", line)
                
                # Mengambil string nama (Pola umum nama maskapai: NAMA/DEPAN MR/MRS/MS atau NAMA, DEPAN)
                name_match = re.search(r"([A-Z\s\/,\.-]+(?:MR|MRS|MS|MISS|MSTR|TITOHIR|PAX)?)", line)
                
                pnr = pnr_match.group(1) if pnr_match else None
                seat = seat_match.group(1) if seat_match else None
                
                # Filter agar garis header/teks biasa tidak masuk sebagai nama
                if seat or pnr:
                    raw_name = name_match.group(1).strip() if name_match else line[:25].strip()
                    # Clean up nama dari karakter berlebih
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
    filename = uploaded_file.name
    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif filename.endswith(".txt"):
        df = pd.read_csv(uploaded_file, sep="\t")
    else:
        st.error("Format file tapping tidak didukung!")
        return None
    
    # Standarisasi Nama Kolom (Case-insensitive)
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df

# -----------------------------------------------------------------------------
# 3. ENGINE MATCHING (SESUAI HIRARKI ANDA)
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
        
        # Algoritma Fuzzy Matching untuk Mencari Nama Terdekat di Manifest
        manifest_names = df_manifest["nama_manifest"].tolist()
        best_match = process.extractOne(tap_nama, manifest_names, scorer=fuzz.token_sort_ratio)
        
        if best_match and best_match[1] >= 75: # Threshold kemiripan nama 75%
            match_row = df_manifest[df_manifest["nama_manifest"] == best_match[0]].iloc[0]
            mnf_seat = match_row["seat_manifest"]
            mnf_pnr = match_row["pnr_manifest"]
            
            matched_seat_manifest = mnf_seat
            matched_pnr_manifest = mnf_pnr
            
            # --- EVALUASI HIRARKI (a - e) ---
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
            # Poin g: Ada di Tapping tapi tidak ada di Manifest
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
    
    # Poin h: Ada di Manifest tetapi TIDAK ADA di Data Tapping (Not Scan / No Show)
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
# 4. TAMPILAN SIDEBAR (NAVIGATION & INPUTS)
# -----------------------------------------------------------------------------

with st.sidebar:
    st.title("✈️ Pax Reconciliation")
    menu = st.radio("Pilih Menu:", ["📊 Rekonsiliasi", "📜 Histori Log"])
    st.divider()

if menu == "📊 Rekonsiliasi":
    with st.sidebar:
        st.subheader("1. Setting Flight")
        airline = st.selectbox(
            "Pilih Maskapai:",
            ["Lion Group (JT/IW/ID)", "Garuda Indonesia (GA)", "Citilink (QG)", "Scoot (TR)", "Malaysia Airlines (MH)", "Lainnya"]
        )
        
        flight_mode = st.radio("Mode Flight:", ["Single Flight", "Combine Flight"])
        st.divider()
        
        st.subheader("2. Upload Files")
        
        if flight_mode == "Single Flight":
            file_tapping1 = st.file_uploader("Upload File Tapping (CSV/XLS/TXT):", type=["csv", "xlsx", "xls", "txt"])
            file_tapping2 = None
        else:
            file_tapping1 = st.file_uploader("Upload Tapping Flight 1:", type=["csv", "xlsx", "xls", "txt"], key="t1")
            file_tapping2 = st.file_uploader("Upload Tapping Flight 2:", type=["csv", "xlsx", "xls", "txt"], key="t2")
            
        file_manifest = st.file_uploader("Upload File Manifest (PDF/TXT):", type=["pdf", "txt"])
        
        btn_proses = st.button("🚀 MULAI PROSES", use_container_state_style=True)

    # -------------------------------------------------------------------------
    # 5. HALAMAN UTAMA (CONTENT AREA & PROCESSING)
    # -------------------------------------------------------------------------
    st.title("📊 Hasil Rekonsiliasi Pax")
    
    if btn_proses:
        # Validasi Input File
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload sebelum memproses!")
        else:
            with st.spinner("⏳ Memproses data manifest & membandingkan dengan RegEx..."):
                # Load Tapping Data
                df_tap1 = load_tapping_file(file_tapping1)
                if flight_mode == "Combine Flight":
                    df_tap2 = load_tapping_file(file_tapping2)
                    df_tapping = pd.concat([df_tap1, df_tap2], ignore_index=True)
                else:
                    df_tapping = df_tap1
                    
                # Load & Parse Manifest
                df_manifest = parse_manifest_pdf(file_manifest, airline)
                
                # Run Reconciliation
                df_result = reconcile_engine(df_tapping, df_manifest, airline)
                
                # Simpan ke Session History
                st.session_state["history"].append({
                    "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "airline": airline,
                    "mode": flight_mode,
                    "total_pax": len(df_result),
                    "data": df_result
                })

            # Display Ringkasan Metrik
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Pax", len(df_result))
            col2.metric("🟢 Perfect Match", len(df_result[df_result["Status"] == "🟢 MATCH"]))
            col3.metric("🟡 Match Catatan", len(df_result[df_result["Status"] == "🟡 MATCH"]))
            col4.metric("🚨 Alert/Unmatched", len(df_result[df_result["Status"].isin(["🔴 NOT MATCH", "🚨 UNMATCHED"])]))
            
            st.divider()
            
            # Tampilkan Tabel
            st.dataframe(df_result, use_container_width=True, height=500)
            
            # Button Download Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_result.to_excel(writer, index=False, sheet_name="Hasil Rekonsiliasi")
            
            st.download_button(
                label="📥 Download Hasil (.XLSX)",
                data=output.getvalue(),
                file_name=f"Hasil_Rekonsiliasi_{airline.split()[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    else:
        st.info("👈 Silakan atur maskapai, upload file di **Sidebar sebelah kiri**, lalu klik tombol **MULAI PROSES**.")

elif menu == "📜 Histori Log":
    st.title("📜 Histori Log Rekonsiliasi")
    
    if len(st.session_state["history"]) == 0:
        st.warning("Belum ada riwayat rekonsiliasi pada sesi ini.")
    else:
        for idx, item in enumerate(reversed(st.session_state["history"])):
            with st.expander(f"🕒 {item['time']} - {item['airline']} ({item['mode']}) - Total: {item['total_pax']} Pax"):
                st.dataframe(item["data"], use_container_width=True)
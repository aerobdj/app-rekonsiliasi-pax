import streamlit as st
import pandas as pd
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN & BRANDING
# -----------------------------------------------------------------------------
LOGO_WHITE = "https://www.injourneyairports.id/assets/injourney-logo-white-Dl4T6LNj.png"
KAWUNG_ICON = "https://www.injourneyairports.id/assets/kawung-logo-side-CktPU2GK.png"

st.set_page_config(
    page_title="InJourney Airports - Pax Reconciliation System",
    page_icon=KAWUNG_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. CUSTOM CSS - FOKUS KONTEN UTAMA & DASHBOARD METRICS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Styling Header Utama */
    .main-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        border-bottom: 2px solid #334155;
        margin-bottom: 24px;
    }
    .main-title {
        font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
        font-weight: 700;
        font-size: 28px;
        color: #f8fafc;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 4px;
    }
    
    /* Welcome / Empty State Card */
    .welcome-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 28px;
        margin-top: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .welcome-title {
        font-size: 18px;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 8px;
    }
    .welcome-text {
        font-size: 14px;
        color: #cbd5e1;
        line-height: 1.6;
    }
    
    /* Step Badge Styling */
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
    
    /* Metric Cards Redesign */
    div[data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
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
    
    /* Primary Button Styling */
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
# 3. TAMPILAN SIDEBAR (KONTROL INPUT)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h4 style='text-align: center; color: #f8fafc; margin-bottom: 0;'>InJourney Airports</h4>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 12px; color: #94a3b8;'>Pax Reconciliation System</p>", unsafe_allow_html=True)
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
    
    # --- HEADER KONTEN ---
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
        st.image(LOGO_WHITE, width=190)

    # --- KONTEN UTAMA (Awal / Setelah Tombol Ditekan) ---
    if btn_proses:
        if not file_manifest or not file_tapping1 or (flight_mode == "Combine Flight" and not file_tapping2):
            st.error("⚠️ Mohon lengkapi semua file upload di sidebar sebelah kiri sebelum memproses!")
        else:
            # Simulasi Tampilan Ringkasan KPI Dashboard
            st.markdown("### 📈 Ringkasan Hasil Rekonsiliasi")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Penumpang", "185 Pax", delta="Total Scanned")
            m2.metric("🟢 Perfect Match", "172 Pax", delta="93% Match")
            m3.metric("🟡 Match Catatan", "8 Pax", delta="Beda Seat/PNR")
            m4.metric("🚨 Alert / Unmatch", "5 Pax", delta="Perlu Cek Ground", delta_color="inverse")
            
            st.write("")
            st.markdown("### 📋 Detail Pencocokan Data Penumpang")
            
            # Dummy DataFrame untuk Preview Tampilan Tabel Hasil
            dummy_data = {
                "Nama Tapping": ["BUDI SANTOSO", "SITI AMINAH", "JOHN DOE", "AHMAD BADAWI"],
                "Seat Tapping": ["12A", "12B", "15C", "18A"],
                "PNR Tapping": ["X7Y8Z9", "A1B2C3", "K4L5M6", "P7Q8R9"],
                "Type Pax": ["Adult", "Adult", "Adult", "Child"],
                "Seat Manifest": ["12A", "12B", "15D", "-"],
                "PNR Manifest": ["X7Y8Z9", "A1B2C3", "K4L5M6", "-"],
                "Status": ["🟢 MATCH", "🟢 MATCH", "🟡 MATCH", "🚨 UNMATCHED"],
                "Catatan": ["Match Perfect", "Match Perfect", "Change Seat (Manifest: 15D)", "Offload / Not in Manifest"]
            }
            df_preview = pd.DataFrame(dummy_data)
            
            # Tabel Tampilan Interaktif
            st.dataframe(df_preview, use_container_width=True, height=350)
            
            # Area Tombol Aksi Laporan
            col_act1, col_act2 = st.columns([2, 1])
            with col_act2:
                output = io.BytesIO()
                st.download_button(
                    label="📥 Download Laporan Hasil (.XLSX)",
                    data=output.getvalue(),
                    file_name="Laporan_Rekonsiliasi_InJourney.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    else:
        # --- WELCOME / EMPTY STATE CARD (Tampilan Awal) ---
        st.markdown("""
            <div class="welcome-card">
                <div class="welcome-title">Selamat Datang di System Passenger Reconciliation InJourney Airports</div>
                <div class="welcome-text">
                    Sistem ini dirancang untuk mempermudah pencocokan data penyeberangan/keberangkatan penumpang antara data log <b>Gate Tapping</b> dan <b>Passenger Manifest PDF</b> secara presisi dan akurat.
                </div>
                <hr style="border: 0; border-top: 1px solid #334155; margin: 16px 0;">
                <div class="welcome-text">
                    <b>Panduan Penggunaan Singkat:</b><br>
                    <p style="margin-top: 8px; margin-bottom: 4px;"><span class="step-badge">1</span> Pilih maskapai penerbangan dan mode penerbangan di sidebar sebelah kiri.</p>
                    <p style="margin-bottom: 4px;"><span class="step-badge">2</span> Unggah file Tapping (CSV/XLSX/TXT) dan file Manifest PDF yang sesuai.</p>
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
            with st.expander(f"🕒 {item['time']} — {item['airline']} ({item['mode']})"):
                st.dataframe(item["data"], use_container_width=True)

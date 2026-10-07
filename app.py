import io
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------
# 1. CONFIG & STYLING (GIAO DIỆN TỐI ƯU 2 HÀNG X 5 CỘT)
# ---------------------------------------------------------
st.set_page_config(
    page_title="4G RAN Dashboard",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main { background: #0b0e14; }
    div[data-testid="stSidebar"] { background: #11151f; }
    
    /* Thu gọn Card tối đa để xếp đẹp 5 cột */
    .kpi-card {
        background: #131823;
        border: 1px solid #1f2738;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 6px;
        color: #e0e6ed;
    }
    .kpi-hdr { display: flex; justify-content: space-between; align-items: flex-start; }
    .kpi-cat { font-size: 9px; color: #8b9bb4; font-weight: 500; }
    .kpi-ttl { font-size: 11px; font-weight: 700; color: #fff; line-height: 1.2; }
    .kpi-bdg { font-size: 8px; font-weight: 800; padding: 1px 4px; border-radius: 3px; }
    .bdg-excellent { background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; }
    .bdg-good { background: rgba(6,182,212,0.2); color: #06b6d4; border: 1px solid #06b6d4; }
    .bdg-warning { background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid #f59e0b; }
    .kpi-body { display: flex; justify-content: space-between; align-items: baseline; margin: 3px 0; }
    .kpi-val { font-size: 18px; font-weight: 800; }
    .val-excellent, .val-good { color: #10b981; }
    .val-warning { color: #f59e0b; }
    .kpi-tgt { font-size: 9px; color: #a0aec0; }
    .kpi-ftr { display: flex; justify-content: space-between; border-top: 1px solid #1a2233; padding-top: 3px; font-size: 8.5px; color: #718096; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. FILE MẪU & PDF REPORT ĐẦY ĐỦ CARDS + CHARTS
# ---------------------------------------------------------
@st.cache_data
def get_sample_csv():
    data = {
        "Hãng": ["ERICSSON"] * 10,
        "Tỉnh/Tp": ["DTP"] * 10,
        "Phường/xã": ["DTP022"] * 10,
        "Site Name": ["LN-CBE001M-TGG"] * 10,
        "Mã đối tượng": [f"ENM13/LN-CBE001M-TGG/{i}" for i in range(11, 21)],
        "Tên đối tượng": [f"4G-CBE001M{i}-TGG" for i in range(11, 21)],
        "Loại đối tượng": ["CELL"] * 10,
        "Thời gian": ["01/10/2026 00:00"] * 10,
        "Giờ": [0.0] * 10,
        "User Uplink Average Throughput (Kbps)": [1054.3, 2100.5, 3400.2, 1200.0, 2800.1, 3100.0, 1800.4, 2500.0, 2900.0, 1500.0],
        "User Downlink Average Throughput (Kbps)": [41647.3, 25000.0, 18000.5, 32000.0, 45000.0, 12000.0, 28000.0, 39000.0, 48000.0, 15000.0],
        "CQI_4G": [98.07, 95.50, 91.20, 96.80, 94.10, 88.50, 97.30, 93.20, 98.10, 89.40],
        "Call Setup Success Rate": [99.90, 99.85, 99.70, 99.95, 99.60, 99.10, 99.88, 99.92, 99.75, 99.30],
        "Inter-RAT HOSR (LTE to WCDMA) (%)": [94.83, 95.00, 92.10, 96.50, 93.80, 91.00, 95.20, 94.00, 96.00, 90.50],
        "Inter-frequency HO (%)": [98.50, 98.10, 97.60, 99.00, 98.20, 96.50, 98.80, 98.40, 99.10, 97.00],
        "Intra-frequency HO (%)": [99.64, 99.20, 98.80, 99.70, 99.10, 98.20, 99.50, 99.30, 99.80, 98.00],
        "Resource Block Untilizing Rate Downlink (%)": [9.33, 15.20, 22.40, 11.10, 18.50, 38.20, 12.80, 14.50, 8.90, 29.40],
        "Service Drop (all service)": [0.08, 0.12, 0.15, 0.05, 0.20, 0.45, 0.09, 0.11, 0.04, 0.35],
        "Total Data Traffic Volume (GB)": [12.5, 18.2, 25.4, 14.1, 20.8, 35.6, 16.3, 19.0, 11.2, 28.9],
        "Traffic Volumn DL (GB)": [11.2, 16.5, 23.1, 12.8, 18.9, 32.1, 14.8, 17.2, 10.1, 26.0],
        "Traffic Volume UL (GB)": [1.3, 1.7, 2.3, 1.3, 1.9, 3.5, 1.5, 1.8, 1.1, 2.9],
        "SRVCC Success Rate (LTE to WCDMA)": [97.75, 98.00, 96.50, 98.50, 95.80, 94.10, 97.90, 98.20, 98.80, 95.00],
        "Call Drop Rate (VoLTE)": [0.00, 0.05, 0.10, 0.00, 0.18, 0.35, 0.02, 0.04, 0.00, 0.25],
        "Inter-frequency HO Success Rates (VoLTE)": [100.0, 99.5, 98.0, 100.0, 99.0, 97.5, 100.0, 99.8, 100.0, 98.2],
        "Intra-frequency HO Success Rates (VoLTE)": [100.0, 100.0, 99.5, 100.0, 99.8, 98.5, 100.0, 100.0, 100.0, 99.0],
        "VoLTE E-RAB Call Setup Success Rate": [100.0, 99.9, 99.8, 100.0, 99.7, 99.2, 100.0, 100.0, 100.0, 99.5],
        "VoLTE Traffic (Erl)": [0.066, 0.120, 0.210, 0.080, 0.150, 0.310, 0.095, 0.110, 0.050, 0.240],
    }
    return pd.DataFrame(data).to_csv(index=False).encode("utf-8")


def generate_pdf_report(summary, hourly_df, bad_df, top_traffic_df):
    """Xuat PDF full Cards, Charts, Top Bad Cells va Top Traffic Sites/Cells"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    styles = getSampleStyleSheet()

    t_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    now_str = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")

    story.append(Paragraph("BÁO CÁO TỔNG QUAN TỐI ƯU HÓA MẠNG 4G/LTE", t_style))
    story.append(Paragraph(f"Thời gian xuất: {now_str} | Phòng Tối ưu hóa RAN", styles["Normal"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=10))

    # SECTION 1: BẢNG 10 CARDS KPI ĐẦY ĐỦ
    story.append(Paragraph("<b>I. BẢNG TỔNG HỢP KPI MẠNG (EXECUTIVE KPI CARDS)</b>", styles["Heading2"]))
    story.append(Spacer(1, 4))

    kpi_data = [
        ["Phân nhóm KPI", "Chỉ số KPI (Metric)", "Giá trị Trung bình", "Chỉ tiêu Benchmark", "Đánh giá"],
        ["Data Traffic", "Total Data Traffic Volume", f"{summary.get('tf',0):,.1f} GB", "N/A", "Tải tốt"],
        ["Accessibility", "Call Setup Success Rate (CSSR)", f"{summary.get('cssr',0):.2f}%", ">= 99.50%", "Tốt"],
        ["Retainability", "Service Drop Rate (CDR)", f"{summary.get('drop',0):.3f}%", "<= 0.100%", "Ổn định"],
        ["Integrity", "User Downlink Throughput", f"{summary.get('dl',0):.2f} Mbps", ">= 15.0 Mbps", "Đạt chuẩn"],
        ["Integrity", "User Uplink Throughput", f"{summary.get('ul',0):.2f} Mbps", ">= 1.5 Mbps", "Đạt chuẩn"],
        ["Radio Quality", "CQI 4G Index (CQI >= 7)", f"{summary.get('cqi',0):.2f}%", ">= 92.00%", "Tốt"],
        ["Capacity & Load", "PRB Utilization DL", f"{summary.get('prb',0):.2f}%", "<= 35.00%", "Dồi dào"],
        ["Mobility", "Intra-frequency HO SR", f"{summary.get('intra',0):.2f}%", ">= 99.00%", "Mượt"],
        ["Mobility", "Inter-RAT HOSR (LTE to 3G)", f"{summary.get('irat',0):.2f}%", ">= 95.00%", "Cần theo dõi"],
        ["Voice Continuity", "SRVCC Success Rate", f"{summary.get('srvcc',0):.2f}%", ">= 95.00%", "Đảm bảo"],
    ]

    t1 = Table(kpi_data, colWidths=[110, 170, 110, 110, 110])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # SECTION 2: BẢNG CHART XU HƯỚNG CÁC KPI THEO GIỜ
    story.append(Paragraph("<b>II. XU HƯỚNG CÁC CHỈ SỐ KPI THEO KHUNG GIỜ (HOURLY KPI TRENDS)</b>", styles["Heading2"]))
    story.append(Spacer(1, 4))

    if not hourly_df.empty:
        chart_data_list = [["Khung Giờ", "Traffic (GB)", "DL Thrp (M)", "Drop Rate (%)", "CSSR (%)", "CQI 4G (%)", "PRB Util (%)"]]
        for _, r in hourly_df.head(24).iterrows():
            chart_data_list.append([
                f"{int(r['Hour']):02d}:00",
                f"{r.get('Total Data Traffic Volume (GB)', 0):.1f}",
                f"{r.get('DL_Throughput_Mbps', 0):.2f}",
                f"{r.get('Service Drop (all service)', 0):.3f}",
                f"{r.get('Call Setup Success Rate', 0):.2f}",
                f"{r.get('CQI_4G', 0):.2f}",
                f"{r.get('Resource Block Untilizing Rate Downlink (%)', 0):.2f}"
            ])
        t_chart = Table(chart_data_list, colWidths=[80, 85, 85, 85, 85, 85, 85])
        t_chart.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ]))
        story.append(t_chart)
        story.append(Spacer(1, 10))

    # SECTION 3: TOP HIGH TRAFFIC SITES / CELLS
    if not top_traffic_df.empty:
        story.append(Paragraph("<b>III. DANH SÁCH TOP SITE/CELL CÓ LƯU LƯỢNG (TRAFFIC) CAO NHẤT</b>", styles["Heading2"]))
        story.append(Spacer(1, 4))
        tr_cols = list(top_traffic_df.columns)[:6]
        tr_sub = top_traffic_df[tr_cols].head(8)

        tr_data = [tr_cols]
        for _, row in tr_sub.iterrows():
            r_fmt = [f"{v:,.2f}" if isinstance(v, (float, int)) else str(v) for v in row]
            tr_data.append(r_fmt)

        t_tr = Table(tr_data, colWidths=[120, 150, 85, 85, 85, 85])
        t_tr.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#047857")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#6ee7b7")),
        ]))
        story.append(t_tr)
        story.append(Spacer(1, 10))

    # SECTION 4: TOP BAD CELLS
    if not bad_df.empty:
        story.append(Paragraph("<b>IV. DANH SÁCH TOP WORST CELLS CẦN TỐI ƯU CẤP THIẾT</b>", styles["Heading2"]))
        story.append(Spacer(1, 4))
        bcols = [c for c in bad_df.columns if c in ["Site Name", "Tên đối tượng"]] + [c for c in bad_df.columns if c not in ["Site Name", "Tên đối tượng"]][:4]
        sub = bad_df[bcols].head(8)

        bdata = [bcols]
        for _, row in sub.iterrows():
            r_fmt = [f"{v:.2f}" if isinstance(v, float) else str(v) for v in row]
            bdata.append(r_fmt)

        t2 = Table(bdata, colWidths=[120, 150, 85, 85, 85, 85])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#b91c1c")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#fca5a5")),
        ]))
        story.append(t2)

    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------------------------------------
# 3. DATA PROCESSING
# ---------------------------------------------------------
@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input)

    t_cols = ["Thời gian", "Time", "DateTime", "timestamp"]
    t_col = next((c for c in t_cols if c in df.columns), None)

    if t_col:
        df["DateTime"] = pd.to_datetime(df[t_col], dayfirst=True, errors="coerce")
        df["Date"] = df["DateTime"].dt.date
    else:
        st.error("❌ Thiếu cột Thời gian!")
        st.stop()

    h_cols = ["Giờ", "Hour", "hour"]
    h_col = next((c for c in h_cols if c in df.columns), None)
    if h_col:
        df["Hour"] = pd.to_numeric(df[h_col], errors="coerce").fillna(0).astype(int)
    else:
        df["Hour"] = df["DateTime"].dt.hour

    num_cols = [
        "User Downlink Average Throughput (Kbps)",
        "User Uplink Average Throughput (Kbps)",
        "CQI_4G",
        "Call Setup Success Rate",
        "Service Drop (all service)",
        "Resource Block Untilizing Rate Downlink (%)",
        "Total Data Traffic Volume (GB)",
        "Traffic Volumn DL (GB)",
        "Traffic Volume UL (GB)",
        "Intra-frequency HO (%)",
        "Inter-frequency HO (%)",
        "Inter-RAT HOSR (LTE to WCDMA) (%)",
        "SRVCC Success Rate (LTE to WCDMA)",
        "Call Drop Rate (VoLTE)",
        "VoLTE E-RAB Call Setup Success Rate",
        "VoLTE Traffic (Erl)",
    ]

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "User Downlink Average Throughput (Kbps)" in df.columns:
        df["DL_Throughput_Mbps"] = df["User Downlink Average Throughput (Kbps)"] / 1000.0
    if "User Uplink Average Throughput (Kbps)" in df.columns:
        df["UL_Throughput_Mbps"] = df["User Uplink Average Throughput (Kbps)"] / 1000.0

    return df


# ---------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("📶 Navigation")

st.sidebar.download_button(
    label="📥 Tải File Mẫu",
    data=get_sample_csv(),
    file_name="4G_Sample.csv",
    mime="text/csv",
)

st.sidebar.markdown("---")

up_file = st.sidebar.file_uploader("📂 Tải CSV KPI:", type=["csv"])

if up_file is not None:
    st.sidebar.success("✅ Đã tải file!")
    df = process_data(up_file)
elif os.path.exists("4G.csv"):
    st.sidebar.info("ℹ️ Dùng file mẫu 4G.csv")
    df = process_data("4G.csv")
else:
    st.info("👋 Vui lòng tải file CSV ở bên trái.")
    st.stop()

# Filters
st.sidebar.subheader("📅 Chọn Ngày")
all_dates = sorted(df["Date"].dropna().unique())

sel_dates = []
chk_all_d = st.sidebar.checkbox("Tất cả Ngày", value=True)
if chk_all_d:
    sel_dates = all_dates
else:
    for d in all_dates:
        if st.sidebar.checkbox(str(d), value=True, key=f"d_{d}"):
            sel_dates.append(d)

st.sidebar.subheader("📡 Chọn Site")
site_col = "Site Name" if "Site Name" in df.columns else None

sel_sites = []
if site_col:
    all_sites = sorted(df[site_col].dropna().unique())
    chk_all_s = st.sidebar.checkbox("Tất cả Site", value=True)
    if chk_all_s:
        sel_sites = all_sites
    else:
        for s in all_sites:
            if st.sidebar.checkbox(str(s), value=True, key=f"s_{s}"):
                sel_sites.append(s)

    filtered_df = df[(df["Date"].isin(sel_dates)) & (df[site_col].isin(sel_sites))]
else:
    filtered_df = df[df["Date"].isin(sel_dates)]

if filtered_df.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu!")
    st.stop()

# ---------------------------------------------------------
# 5. HEADER & CARDS (NHỎ GỌN CHUẨN 2 HÀNG X 5 CỘT)
# ---------------------------------------------------------
cell_col = "Tên đối tượng" if "Tên đối tượng" in df.columns else None
num_cells = filtered_df[cell_col].nunique() if cell_col else 0
num_sites = filtered_df[site_col].nunique() if site_col else 0

st.title("📡 4G/LTE RAN Dashboard")
st.markdown(f"**Records:** `{len(filtered_df):,}` | **Sites:** `{num_sites}` | **Cells:** `{num_cells}`")
st.markdown("---")


def render_card(cat, title, val, tgt, min_v, max_v, remark, stt="good"):
    s_low = stt.lower()
    html_str = (
        f'<div class="kpi-card"><div class="kpi-hdr"><div>'
        f'<div class="kpi-cat">{cat}</div><div class="kpi-ttl">{title}</div></div>'
        f'<span class="kpi-bdg bdg-{s_low}">{stt.upper()}</span></div>'
        f'<div class="kpi-body"><span class="kpi-val val-{s_low}">{val}</span>'
        f'<span class="kpi-tgt">Target: {tgt}</span></div>'
        f'<div class="kpi-ftr"><span>Min: {min_v} Max: {max_v}</span>'
        f'<span>{remark}</span></div></div>'
    )
    st.markdown(html_str, unsafe_allow_html=True)


s_tf = filtered_df.get("Total Data Traffic Volume (GB)", pd.Series([0]))
s_cssr = filtered_df.get("Call Setup Success Rate", pd.Series([0]))
s_cdr = filtered_df.get("Service Drop (all service)", pd.Series([0]))
s_dl = filtered_df.get("DL_Throughput_Mbps", pd.Series([0]))
s_ul = filtered_df.get("UL_Throughput_Mbps", pd.Series([0]))
s_cqi = filtered_df.get("CQI_4G", pd.Series([0]))
s_prb = filtered_df.get("Resource Block Untilizing Rate Downlink (%)", pd.Series([0]))
s_intra = filtered_df.get("Intra-frequency HO (%)", pd.Series([0]))
s_irat = filtered_df.get("Inter-RAT HOSR (LTE to WCDMA) (%)", pd.Series([0]))
s_srvcc = filtered_df.get("SRVCC Success Rate (LTE to WCDMA)", pd.Series([0]))

# HÀNG 1 (5 CỘT)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    v = s_tf.sum()
    render_card("Data Traffic", "Total Data Traffic", f"{v:,.0f} GB", "N/A", f"{s_tf.min():.1f}G", f"{s_tf.max():.1f}G", "Tải dữ liệu tổng", "EXCELLENT")
with c2:
    v = s_cssr.mean()
    render_card("Accessibility", "Call Setup SR", f"{v:.2f}%", ">=99.5%", f"{s_cssr.min():.1f}%", f"{s_cssr.max():.1f}%", "Rất ổn định", "GOOD" if v >= 99.5 else "WARNING")
with c3:
    v = s_cdr.mean()
    render_card("Retainability", "Service Drop Rate", f"{v:.3f}%", "<=0.1%", f"{s_cdr.min():.3f}%", f"{s_cdr.max():.3f}%", "Ổn định chung", "WARNING" if v > 0.1 else "GOOD")
with c4:
    v = s_dl.mean()
    render_card("Integrity", "User DL Throughput", f"{v:.2f} M", ">=15.0M", f"{s_dl.min():.1f}M", f"{s_dl.max():.1f}M", "+58% chuẩn", "EXCELLENT" if v >= 15.0 else "GOOD")
with c5:
    v = s_ul.mean()
    render_card("Integrity", "User UL Throughput", f"{v:.2f} M", ">=1.5M", f"{s_ul.min():.2f}M", f"{s_ul.max():.2f}M", "+92% chuẩn", "EXCELLENT" if v >= 1.5 else "GOOD")

# HÀNG 2 (5 CỘT)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    v = s_cqi.mean()
    render_card("Radio Quality", "CQI (CQI >= 7)", f"{v:.2f}%", ">=92.0%", f"{s_cqi.min():.1f}%", f"{s_cqi.max():.1f}%", "64QAM/256QAM tốt", "EXCELLENT" if v >= 92.0 else "WARNING")
with c2:
    v = s_prb.mean()
    render_card("Capacity & Load", "PRB Utilization DL", f"{v:.2f}%", "<=35.0%", f"{s_prb.min():.1f}%", f"{s_prb.max():.1f}%", "Dồi dào dự phòng", "EXCELLENT" if v <= 35.0 else "WARNING")
with c3:
    v = s_intra.mean()
    render_card("Mobility", "Intra-freq HO SR", f"{v:.2f}%", ">=99.0%", f"{s_intra.min():.1f}%", f"{s_intra.max():.1f}%", "Chuyển giao mượt", "WARNING" if v < 99.0 else "GOOD")
with c4:
    v = s_irat.mean()
    render_card("Mobility", "Inter-RAT HOSR", f"{v:.2f}%", ">=95.0%", f"{s_irat.min():.1f}%", f"{s_irat.max():.1f}%", "Chỉnh Event B2", "WARNING" if v < 95.0 else "GOOD")
with c5:
    v = s_srvcc.mean()
    render_card("Voice Continuity", "SRVCC Success Rate", f"{v:.2f}%", ">=95.0%", f"{s_srvcc.min():.1f}%", f"{s_srvcc.max():.1f}%", "Đảm bảo thoại 3G", "EXCELLENT" if v >= 95.0 else "WARNING")

st.markdown("---")

# ---------------------------------------------------------
# 6. UNIFIED DUAL-AXIS CHART
# ---------------------------------------------------------
st.subheader("📈 Biểu Đồ Tương Quan Xu Hướng KPI")

kpi_dict = {
    "DL Throughput (Mbps)": "DL_Throughput_Mbps",
    "UL Throughput (Mbps)": "UL_Throughput_Mbps",
    "CQI 4G Index (%)": "CQI_4G",
    "PRB DL Utilization (%)": "Resource Block Untilizing Rate Downlink (%)",
    "Service Drop Rate (%)": "Service Drop (all service)",
    "Call Setup SR (%)": "Call Setup Success Rate",
    "Intra-Freq HO SR (%)": "Intra-frequency HO (%)",
    "Inter-RAT HOSR (%)": "Inter-RAT HOSR (LTE to WCDMA) (%)",
    "VoLTE Traffic (Erl)": "VoLTE Traffic (Erl)",
    "VoLTE Drop Rate (%)": "Call Drop Rate (VoLTE)",
}

avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}

ctrl_col1, ctrl_col2 = st.columns([1, 1])
with ctrl_col1:
    time_mode = st.radio("⏱ Thời gian:", ["Chỉ theo giờ (24h Avg)", "Theo Ngày & Giờ (Timeline)"], horizontal=True)

with ctrl_col2:
    sel_kpi_lbl = st.selectbox("🎯 Chọn KPI kết hợp Traffic:", options=list(avail_kpis.keys()))

sel_kpi_col = avail_kpis[sel_kpi_lbl]
agg_func = "sum" if "Traffic" in sel_kpi_lbl or "Erl" in sel_kpi_lbl else "mean"

if time_mode == "Chỉ theo giờ (24h Avg)":
    c_data = filtered_df.groupby("Hour").agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: agg_func}).reset_index()
    x_axis = c_data["Hour"]
    x_title = "Giờ trong ngày (0h - 23h)"
else:
    c_data = filtered_df.groupby(["Date", "Hour", "DateTime"]).agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: agg_func}).reset_index().sort_values(by="DateTime")
    c_data["TimeLabel"] = c_data["DateTime"].dt.strftime("%d/%m %H:00")
    x_axis = c_data["TimeLabel"]
    x_title = "Thời Gian (Ngày/Giờ)"

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=x_axis, y=c_data["Total Data Traffic Volume (GB)"], name="Traffic (GB)", marker_color="rgba(53, 162, 235, 0.5)"), secondary_y=False)
fig.add_trace(go.Scatter(x=x_axis, y=c_data[sel_kpi_col], name=sel_kpi_lbl, mode="lines+markers", line=dict(color="#ff4d4f", width=2.5)), secondary_y=True)

fig.update_layout(title_text=f"📊 Biểu đồ Traffic và {sel_kpi_lbl}", template="plotly_dark", hovermode="x unified", height=420, margin=dict(l=10, r=10, t=40, b=10))
fig.update_xaxes(title_text=x_title, type="category" if time_mode != "Chỉ theo giờ (24h Avg)" else None)
fig.update_yaxes(title_text="Traffic (GB)", secondary_y=False, showgrid=False)
fig.update_yaxes(title_text=sel_kpi_lbl, secondary_y=True, showgrid=True, gridcolor="rgba(255,255,255,0.1)")

st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# ---------------------------------------------------------
# 7. TOP HIGH TRAFFIC SITES / CELLS (NHẬP SỐ N TRỰC TIẾP)
# ---------------------------------------------------------
st.subheader("🔥 Top Site / Cell Có Lưu Lượng (Traffic) Cao Nhất")

tr_col1, tr_col2 = st.columns([1, 1])
with tr_col1:
    tr_group_level = st.radio("📊 Nhóm theo Cấp độ:", ["Top Cell (Tên đối tượng)", "Top Site (Site Name)"], horizontal=True)
with tr_col2:
    # Cho phép user nhập số N trực tiếp bằng Textbox / NumberInput
    top_n_traffic = st.number_input("🔢 Nhập số lượng Top N cần hiển thị:", min_value=1, max_value=200, value=10, step=1)

if "Total Data Traffic Volume (GB)" in filtered_df.columns:
    if tr_group_level == "Top Site (Site Name)" and site_col:
        top_traffic_df = (
            filtered_df.groupby(site_col)
            .agg({
                "Total Data Traffic Volume (GB)": "sum",
                "Traffic Volumn DL (GB)": "sum" if "Traffic Volumn DL (GB)" in filtered_df.columns else "mean",
                "Traffic Volume UL (GB)": "sum" if "Traffic Volume UL (GB)" in filtered_df.columns else "mean",
                "DL_Throughput_Mbps": "mean",
                "Resource Block Untilizing Rate Downlink (%)": "mean",
            })
            .reset_index()
            .sort_values(by="Total Data Traffic Volume (GB)", ascending=False)
            .head(int(top_n_traffic))
        )
    else:
        grp_cols = [site_col, cell_col] if site_col and cell_col else ([cell_col] if cell_col else [site_col])
        top_traffic_df = (
            filtered_df.groupby(grp_cols)
            .agg({
                "Total Data Traffic Volume (GB)": "sum",
                "Traffic Volumn DL (GB)": "sum" if "Traffic Volumn DL (GB)" in filtered_df.columns else "mean",
                "Traffic Volume UL (GB)": "sum" if "Traffic Volume UL (GB)" in filtered_df.columns else "mean",
                "DL_Throughput_Mbps": "mean",
                "Resource Block Untilizing Rate Downlink (%)": "mean",
            })
            .reset_index()
            .sort_values(by="Total Data Traffic Volume (GB)", ascending=False)
            .head(int(top_n_traffic))
        )

    st.dataframe(top_traffic_df, use_container_width=True)
else:
    st.info("Không tìm thấy thông tin cột Total Data Traffic Volume (GB).")
    top_traffic_df = pd.DataFrame()

st.markdown("---")

# ---------------------------------------------------------
# 8. WORST CELLS MATRIX & PDF REPORT
# ---------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst Cells & Báo Cáo Cấp Trên")

if cell_col:
    kpi_col1, kpi_col2 = st.columns([2, 1])
    with kpi_col1:
        kpi_opt = st.selectbox("🎯 Lọc Worst Cells theo KPI:", ["Service Drop Rate (CDR)", "Low Downlink Throughput", "Low Uplink Throughput", "Low CQI (Poor RF Coverage)", "High PRB Congestion", "VoLTE Call Drop Rate"])
    with kpi_col2:
        top_n_worst = st.number_input("🔢 Nhập số lượng Worst Cells:", min_value=1, max_value=200, value=10, step=1)

    cell_agg = filtered_df.groupby([site_col, cell_col]).agg({
        col: "mean" for col in [
            "Service Drop (all service)", "DL_Throughput_Mbps", "UL_Throughput_Mbps",
            "CQI_4G", "Resource Block Untilizing Rate Downlink (%)",
            "Call Drop Rate (VoLTE)", "Total Data Traffic Volume (GB)"
        ] if col in filtered_df.columns
    }).reset_index()

    if kpi_opt == "Service Drop Rate (CDR)":
        res_df = cell_agg.sort_values(by="Service Drop (all service)", ascending=False).head(int(top_n_worst))
    elif kpi_opt == "Low Downlink Throughput":
        res_df = cell_agg.sort_values(by="DL_Throughput_Mbps", ascending=True).head(int(top_n_worst))
    elif kpi_opt == "Low Uplink Throughput":
        res_df = cell_agg.sort_values(by="UL_Throughput_Mbps", ascending=True).head(int(top_n_worst))
    elif kpi_opt == "Low CQI (Poor RF Coverage)":
        res_df = cell_agg.sort_values(by="CQI_4G", ascending=True).head(int(top_n_worst))
    elif kpi_opt == "High PRB Congestion":
        res_df = cell_agg.sort_values(by="Resource Block Untilizing Rate Downlink (%)", ascending=False).head(int(top_n_worst))
    else:
        res_df = cell_agg.sort_values(by="Call Drop Rate (VoLTE)", ascending=False).head(int(top_n_worst))

    st.dataframe(res_df, use_container_width=True)

    st.markdown("### 📄 Báo Cáo Cấp Trên (PDF Export)")
    summary_data = {
        "tf": s_tf.sum(),
        "cssr": s_cssr.mean(),
        "drop": s_cdr.mean(),
        "dl": s_dl.mean(),
        "ul": s_ul.mean(),
        "cqi": s_cqi.mean(),
        "prb": s_prb.mean(),
        "intra": s_intra.mean(),
        "irat": s_irat.mean(),
        "srvcc": s_srvcc.mean(),
    }

    # Bảng gom nhóm hourly cho toàn bộ KPI đưa vào PDF
    hourly_summary = filtered_df.groupby("Hour").agg({
        "Total Data Traffic Volume (GB)": "sum",
        "DL_Throughput_Mbps": "mean",
        "Service Drop (all service)": "mean",
        "Call Setup Success Rate": "mean",
        "CQI_4G": "mean",
        "Resource Block Untilizing Rate Downlink (%)": "mean"
    }).reset_index()

    pdf_buf = generate_pdf_report(summary_data, hourly_summary, res_df, top_traffic_df)

    st.download_button(
        label="📑 Xuất Báo Cáo PDF (Đầy Đủ Cards, Top Traffic & Worst Cells)",
        data=pdf_buf,
        file_name="Bao_Cao_Toi_Uu_Mang_4G.pdf",
        mime="application/pdf",
    )

st.caption("🚀 Universal 4G RAN Dashboard — Streamlit & ReportLab")

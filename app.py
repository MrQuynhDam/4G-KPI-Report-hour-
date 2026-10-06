import io
import os
from xml.sax.saxutils import escape
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import (
    make_subplots,
)
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import (
    A4,
    landscape,
)
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ----------------------------------
# 1. PAGE CONFIG
# ----------------------------------
st.set_page_config(
    page_title="4G RAN Dashboard",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.kpi-card {
    border-radius: 8px;
    padding: 7px 10px;
    margin-bottom: 8px;
    background: #1e293b;
    border: 1px solid #334155;
    border-left: 4px solid #22c55e;
    line-height: 1.25;
}
.kpi-card.warning { border-left-color: #f59e0b; }
.kpi-card.excellent { border-left-color: #3b82f6; }
.kpi-card.info { border-left-color: #64748b; }
.kpi-head { display: flex; justify-content: space-between; align-items: center; }
.kpi-cat { font-size: 9.5px; color: #94a3b8; text-transform: uppercase; letter-spacing: .4px; }
.kpi-title { font-size: 12px; font-weight: 600; color: #f1f5f9; margin: 1px 0 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi-badge { font-size: 8.5px; font-weight: 700; padding: 1px 6px; border-radius: 999px; color: #fff; background: #22c55e; }
.kpi-badge.warning { background: #f59e0b; }
.kpi-badge.excellent { background: #3b82f6; }
.kpi-badge.info { background: #64748b; }
.kpi-val { font-size: 19px; font-weight: 700; color: #f8fafc; }
.kpi-meta { font-size: 10px; color: #94a3b8; }
.kpi-remark { font-size: 10px; color: #cbd5e1; font-style: italic; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------
# 2. FILE MẪU & PDF REPORT
# ----------------------------------
@st.cache_data
def get_sample_csv():
    data = {
        "Hãng": ["ERICSSON"] * 10,
        "Tỉnh/Tp": ["DTP"] * 10,
        "Phường/xã": ["DTP022"] * 10,
        "Site Name": ["LN-CBE001M-TGG"] * 10,
        "Mã đối tượng": [
            f"ENM13/LN-CBE001M-TGG/{i}"
            for i in range(11, 21)
        ],
        "Tên đối tượng": [
            f"4G-CBE001M{i}-TGG"
            for i in range(11, 21)
        ],
        "Loại đối tượng": ["CELL"] * 10,
        "Thời gian": ["01/10/2026 00:00"] * 10,
        "Giờ": [0.0] * 10,
        "User Uplink Average Throughput (Kbps)": [
            1054.3, 2100.5, 3400.2,
            1200.0, 2800.1, 3100.0,
            1800.4, 2500.0, 2900.0,
            1500.0,
        ],
        "User Downlink Average Throughput (Kbps)": [
            41647.3, 25000.0, 18000.5,
            32000.0, 45000.0, 12000.0,
            28000.0, 39000.0, 48000.0,
            15000.0,
        ],
        "CQI_4G": [
            98.07, 95.50, 91.20,
            96.80, 94.10, 88.50,
            97.30, 93.20, 98.10,
            89.40,
        ],
        "Call Setup Success Rate": [
            99.90, 99.85, 99.70,
            99.95, 99.60, 99.10,
            99.88, 99.92, 99.75,
            99.30,
        ],
        "Inter-RAT HOSR (LTE to WCDMA) (%)": [
            94.83, 95.00, 92.10,
            96.50, 93.80, 91.00,
            95.20, 94.00, 96.00,
            90.50,
        ],
        "Inter-frequency HO (%)": [
            98.50, 98.10, 97.60,
            99.00, 98.20, 96.50,
            98.80, 98.40, 99.10,
            97.00,
        ],
        "Intra-frequency HO (%)": [
            99.64, 99.20, 98.80,
            99.70, 99.10, 98.20,
            99.50, 99.30, 99.80,
            98.00,
        ],
        "Resource Block Untilizing Rate Downlink (%)": [
            9.33, 15.20, 22.40,
            11.10, 18.50, 38.20,
            12.80, 14.50, 8.90,
            29.40,
        ],
        "Service Drop (all service)": [
            0.08, 0.12, 0.15,
            0.05, 0.20, 0.45,
            0.09, 0.11, 0.04,
            0.35,
        ],
        "Total Data Traffic Volume (GB)": [
            12.5, 18.2, 25.4,
            14.1, 20.8, 35.6,
            16.3, 19.0, 11.2,
            28.9,
        ],
        "Traffic Volumn DL (GB)": [
            11.2, 16.5, 23.1,
            12.8, 18.9, 32.1,
            14.8, 17.2, 10.1,
            26.0,
        ],
        "Traffic Volume UL (GB)": [
            1.3, 1.7, 2.3,
            1.3, 1.9, 3.5,
            1.5, 1.8, 1.1,
            2.9,
        ],
        "SRVCC Success Rate (LTE to WCDMA)": [
            97.75, 98.00, 96.50,
            98.50, 95.80, 94.10,
            97.90, 98.20, 98.80,
            95.00,
        ],
        "Call Drop Rate (VoLTE)": [
            0.00, 0.05, 0.10,
            0.00, 0.18, 0.35,
            0.02, 0.04, 0.00,
            0.25,
        ],
        "Inter-frequency HO Success Rates (VoLTE)": [
            100.0, 99.5, 98.0,
            100.0, 99.0, 97.5,
            100.0, 99.8, 100.0,
            98.2,
        ],
        "Intra-frequency HO Success Rates (VoLTE)": [
            100.0, 100.0, 99.5,
            100.0, 99.8, 98.5,
            100.0, 100.0, 100.0,
            99.0,
        ],
        "VoLTE E-RAB Call Setup Success Rate": [
            100.0, 99.9, 99.8,
            100.0, 99.7, 99.2,
            100.0, 100.0, 100.0,
            99.5,
        ],
        "VoLTE Traffic (Erl)": [
            0.066, 0.120, 0.210,
            0.080, 0.150, 0.310,
            0.095, 0.110, 0.050,
            0.240,
        ],
    }
    return pd.DataFrame(data).to_csv(
        index=False
    ).encode("utf-8")


def _register_pdf_fonts():
    """Đăng ký font Unicode để PDF hiển thị được tiếng Việt."""
    candidates = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/Library/Fonts/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ),
    ]
    for regular, bold in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("AppFont", regular))
                pdfmetrics.registerFont(TTFont("AppFont-Bold", bold))
                pdfmetrics.registerFontFamily(
                    "AppFont",
                    normal="AppFont",
                    bold="AppFont-Bold",
                    italic="AppFont",
                    boldItalic="AppFont-Bold",
                )
                return "AppFont", "AppFont-Bold"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def _chart_png(title, x, traffic, kpi=None, kpi_label=""):
    """Vẽ biểu đồ Traffic (cột) + KPI (đường) thành ảnh PNG cho PDF."""
    fig, ax1 = plt.subplots(figsize=(5.6, 2.4), dpi=160)
    ax1.bar(x, traffic, color="#93c5fd", width=0.7)
    ax1.set_ylabel("Traffic (GB)", fontsize=7)
    ax1.set_xlabel("Giờ", fontsize=7)
    ax1.tick_params(labelsize=7)
    ax1.set_xticks(list(x))
    ax1.grid(axis="y", alpha=0.25)
    if kpi is not None:
        ax2 = ax1.twinx()
        ax2.plot(x, kpi, color="#ef4444", marker="o", markersize=3, linewidth=1.5)
        ax2.set_ylabel(kpi_label, fontsize=7)
        ax2.tick_params(labelsize=7)
    ax1.set_title(title, fontsize=9, fontweight="bold")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


STATUS_COLORS = {
    "EXCELLENT": ("#dbeafe", "#3b82f6"),
    "GOOD": ("#dcfce7", "#22c55e"),
    "WARNING": ("#fef3c7", "#f59e0b"),
    "INFO": ("#f1f5f9", "#64748b"),
}


def generate_pdf_report(cards, charts, bad_df, info_line=""):
    font, font_b = _register_pdf_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )
    styles = getSampleStyleSheet()
    t_style = ParagraphStyle(
        "T", parent=styles["Heading1"], fontName=font_b,
        fontSize=15, textColor=colors.HexColor("#0f172a"), spaceAfter=5,
    )
    normal = ParagraphStyle("N", parent=styles["Normal"], fontName=font)
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName=font_b, spaceBefore=6
    )
    card_style = ParagraphStyle(
        "Card", parent=styles["Normal"], fontName=font, fontSize=7.5, leading=11
    )

    story = []
    now_str = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("BÁO CÁO TỐI ƯU MẠNG 4G", t_style))
    story.append(Paragraph(f"Thời gian: {now_str}", normal))
    if info_line:
        story.append(Paragraph(escape(info_line), normal))
    story.append(
        HRFlowable(
            width="100%", thickness=1, color=colors.HexColor("#3b82f6"),
            spaceBefore=4, spaceAfter=8,
        )
    )

    # ---- KPI cards (lưới 5 cột) ----
    story.append(Paragraph("TỔNG QUAN KPI", h2_style))
    per_row = 5
    rows, style_cmds = [], []
    for r, start in enumerate(range(0, len(cards), per_row)):
        row = []
        for c in range(per_row):
            if start + c >= len(cards):
                row.append("")
                continue
            k = {key: escape(str(v)) for key, v in cards[start + c].items()}
            bg, accent = STATUS_COLORS.get(
                cards[start + c]["status"].upper(), STATUS_COLORS["INFO"]
            )
            html = (
                f'<font size="6.5" color="#64748b">{k["cat"].upper()}</font> '
                f'<font size="6.5" color="{accent}"><b>[{k["status"].upper()}]</b></font><br/>'
                f'<b>{k["title"]}</b><br/>'
                f'<font size="12"><b>{k["val"]}</b></font><br/>'
                f'Mục tiêu: {k["tgt"]}<br/>'
                f'Min {k["min"]} | Max {k["max"]}<br/>'
                f'<i>{k["remark"]}</i>'
            )
            row.append(Paragraph(html, card_style))
            style_cmds.append(("BACKGROUND", (c, r), (c, r), colors.HexColor(bg)))
            style_cmds.append(
                ("LINEABOVE", (c, r), (c, r), 3, colors.HexColor(accent))
            )
        rows.append(row)
    cards_tbl = Table(rows, colWidths=[160] * per_row)
    cards_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 4, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
            + style_cmds
        )
    )
    story.append(cards_tbl)

    # ---- Biểu đồ từng KPI (2 biểu đồ / hàng) ----
    if charts:
        story.append(PageBreak())
        story.append(Paragraph("BIỂU ĐỒ KPI THEO GIỜ (TRUNG BÌNH 24H)", h2_style))
        imgs = []
        for ch in charts:
            png = _chart_png(
                ch["title"], ch["x"], ch["traffic"], ch.get("kpi"), ch.get("label", "")
            )
            imgs.append(Image(png, width=385, height=165))
        grid = [imgs[i:i + 2] for i in range(0, len(imgs), 2)]
        if len(grid[-1]) == 1:
            grid[-1].append("")
        chart_tbl = Table(grid, colWidths=[400, 400])
        chart_tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(chart_tbl)

    # ---- Worst cells ----
    if bad_df is not None and not bad_df.empty:
        story.append(PageBreak())
        story.append(Paragraph("TOP WORST CELLS", h2_style))
        key_cols = ["Site Name", "Tên đối tượng"]
        bcols = [c for c in bad_df.columns if c in key_cols] + [
            c for c in bad_df.columns if c not in key_cols
        ][:4]
        sub = bad_df[bcols].head(15)
        bdata = [bcols]
        for _, row in sub.iterrows():
            bdata.append(
                [f"{v:.2f}" if isinstance(v, float) else str(v) for v in row]
            )
        t2 = Table(bdata, repeatRows=1)
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b91c1c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 1), (-1, -1), font),
                    ("FONTNAME", (0, 0), (-1, 0), font_b),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
                ]
            )
        )
        story.append(t2)

    doc.build(story)
    buf.seek(0)
    return buf



# ----------------------------------
# 3. DATA PREPROCESSING
# ----------------------------------
@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input)

    t_cols = ["Thời gian", "Time", "DateTime", "timestamp"]
    t_col = next((c for c in t_cols if c in df.columns), None)

    if t_col:
        df["DateTime"] = pd.to_datetime(
            df[t_col], dayfirst=True, errors="coerce"
        )
        df["Date"] = df["DateTime"].dt.date
    else:
        st.error("❌ Thiếu cột Thời gian!")
        st.stop()

    h_cols = ["Giờ", "Hour", "hour"]
    h_col = next((c for c in h_cols if c in df.columns), None)
    if h_col:
        df["Hour"] = pd.to_numeric(
            df[h_col], errors="coerce"
        ).fillna(0).astype(int)
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
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            )

    if "User Downlink Average Throughput (Kbps)" in df.columns:
        df["DL_Throughput_Mbps"] = (
            df["User Downlink Average Throughput (Kbps)"] / 1000.0
        )
    if "User Uplink Average Throughput (Kbps)" in df.columns:
        df["UL_Throughput_Mbps"] = (
            df["User Uplink Average Throughput (Kbps)"] / 1000.0
        )

    return df


# ----------------------------------
# 4. SIDEBAR CONTROLS
# ----------------------------------
st.sidebar.title("📶 Navigation")

st.sidebar.download_button(
    label="📥 Tải File Mẫu",
    data=get_sample_csv(),
    file_name="4G_Sample.csv",
    mime="text/csv",
)

st.sidebar.markdown("---")

up_file = st.sidebar.file_uploader(
    "📂 Tải CSV KPI:", type=["csv"]
)

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

    filtered_df = df[
        (df["Date"].isin(sel_dates)) &
        (df[site_col].isin(sel_sites))
    ]
else:
    filtered_df = df[df["Date"].isin(sel_dates)]

if filtered_df.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu!")
    st.stop()

# ----------------------------------
# 5. HEADER & KPI CARDS
# ----------------------------------
cell_col = "Tên đối tượng" if "Tên đối tượng" in df.columns else None
num_cells = filtered_df[cell_col].nunique() if cell_col else 0
num_sites = filtered_df[site_col].nunique() if site_col else 0

TRAFFIC_COL = "Total Data Traffic Volume (GB)"
if TRAFFIC_COL not in filtered_df.columns:
    filtered_df = filtered_df.assign(**{TRAFFIC_COL: 0.0})

st.title("📡 4G/LTE RAN Dashboard")
st.markdown(
    f"**Records:** `{len(filtered_df):,}` | "
    f"**Sites:** `{num_sites}` | "
    f"**Cells:** `{num_cells}`"
)

st.markdown("---")


def render_card(c):
    s_low = c["status"].lower()
    # Nối chuỗi 1 dòng (không xuống dòng, không thụt lề) để Markdown
    # không biến HTML thành khối code.
    html = (
        f'<div class="kpi-card {s_low}" title="{c["remark"]}">'
        f'<div class="kpi-head">'
        f'<span class="kpi-cat">{c["cat"]}</span>'
        f'<span class="kpi-badge {s_low}">{c["status"].upper()}</span>'
        f"</div>"
        f'<div class="kpi-title">{c["title"]}</div>'
        f'<div class="kpi-val">{c["val"]}</div>'
        f'<div class="kpi-meta">Mục tiêu: {c["tgt"]}</div>'
        f'<div class="kpi-meta">Min {c["min"]} · Max {c["max"]}</div>'
        f'<div class="kpi-remark">{c["remark"]}</div>'
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def get_series(col):
    return filtered_df[col] if col in filtered_df.columns else pd.Series([0.0])


s_traffic = get_series(TRAFFIC_COL)
s_cssr = get_series("Call Setup Success Rate")
s_cdr = get_series("Service Drop (all service)")
s_dl = get_series("DL_Throughput_Mbps")
s_ul = get_series("UL_Throughput_Mbps")
s_cqi = get_series("CQI_4G")
s_prb = get_series("Resource Block Untilizing Rate Downlink (%)")
s_intra = get_series("Intra-frequency HO (%)")
s_irat = get_series("Inter-RAT HOSR (LTE to WCDMA) (%)")
s_srvcc = get_series("SRVCC Success Rate (LTE to WCDMA)")

if "Traffic Volumn DL (GB)" in filtered_df.columns and "Traffic Volume UL (GB)" in filtered_df.columns:
    traffic_remark = (
        f"DL {filtered_df['Traffic Volumn DL (GB)'].sum():,.1f} | "
        f"UL {filtered_df['Traffic Volume UL (GB)'].sum():,.1f} GB"
    )
else:
    traffic_remark = "Tổng lưu lượng DL + UL"

# (nhóm, tên KPI, series, cách gộp, format giá trị, format min/max,
#  mục tiêu, nhận xét, hàm đánh giá)
card_specs = [
    # Row 1
    ("Traffic", "Total Traffic", s_traffic, "sum", "{:,.1f} GB", "{:,.2f}",
     "—", traffic_remark, lambda v: "INFO"),
    ("Accessibility", "Call Setup SR (CSSR)", s_cssr, "mean", "{:.2f}%", "{:.2f}%",
     ">=99.5%", "Rất ổn định",
     lambda v: "GOOD" if v >= 99.5 else "WARNING"),
    ("Retainability", "Service Drop Rate", s_cdr, "mean", "{:.3f}%", "{:.3f}%",
     "<=0.1%", "Kéo bởi 3 bad cell",
     lambda v: "WARNING" if v > 0.1 else "GOOD"),
    ("Integrity", "User DL Throughput", s_dl, "mean", "{:.2f} Mbps", "{:.1f}M",
     ">=15.0M", "+58% chuẩn",
     lambda v: "EXCELLENT" if v >= 15.0 else "GOOD"),
    ("Integrity", "User UL Throughput", s_ul, "mean", "{:.2f} Mbps", "{:.2f}M",
     ">=1.5M", "+92% chuẩn",
     lambda v: "EXCELLENT" if v >= 1.5 else "GOOD"),
    # Row 2
    ("Radio Quality", "CQI (CQI >= 7)", s_cqi, "mean", "{:.2f}%", "{:.1f}%",
     ">=92.0%", "64QAM/256QAM tốt",
     lambda v: "EXCELLENT" if v >= 92.0 else "WARNING"),
    ("Capacity", "PRB Utilization DL", s_prb, "mean", "{:.2f}%", "{:.1f}%",
     "<=35.0%", "Dồi dào tài nguyên",
     lambda v: "EXCELLENT" if v <= 35.0 else "WARNING"),
    ("Mobility", "Intra-freq HO SR", s_intra, "mean", "{:.2f}%", "{:.2f}%",
     ">=99.0%", "Chuyển giao mượt",
     lambda v: "WARNING" if v < 99.0 else "GOOD"),
    ("Mobility", "Inter-RAT HOSR", s_irat, "mean", "{:.2f}%", "{:.1f}%",
     ">=95.0%", "Cần chỉnh Event B2",
     lambda v: "WARNING" if v < 95.0 else "GOOD"),
    ("Voice", "SRVCC Success Rate", s_srvcc, "mean", "{:.2f}%", "{:.1f}%",
     ">=95.0%", "Đảm bảo thoại 3G",
     lambda v: "EXCELLENT" if v >= 95.0 else "WARNING"),
]

cards = []
for cat, title, series, how, fmt_v, fmt_mm, tgt, remark, judge in card_specs:
    v = series.sum() if how == "sum" else series.mean()
    cards.append(
        {
            "cat": cat,
            "title": title,
            "val": fmt_v.format(v),
            "tgt": tgt,
            "min": fmt_mm.format(series.min()),
            "max": fmt_mm.format(series.max()),
            "remark": remark,
            "status": judge(v),
        }
    )

CARDS_PER_ROW = 5
for row_start in range(0, len(cards), CARDS_PER_ROW):
    cols = st.columns(CARDS_PER_ROW, gap="small")
    for col, card in zip(cols, cards[row_start:row_start + CARDS_PER_ROW]):
        with col:
            render_card(card)

st.markdown("---")

# ----------------------------------
# 6. UNIFIED DUAL-AXIS CHART
# ----------------------------------
st.subheader("📈 Biểu Đồ Xu Hướng KPI")

kpi_dict = {
    "DL Throughput (Mbps)": "DL_Throughput_Mbps",
    "UL Throughput (Mbps)": "UL_Throughput_Mbps",
    "CQI 4G Index (%)": "CQI_4G",
    "PRB DL Utilization (%)": "Resource Block Untilizing Rate Downlink (%)",
    "Service Drop Rate (%)": "Service Drop (all service)",
    "Call Setup SR (%)": "Call Setup Success Rate",
    "Intra-Freq HO SR (%)": "Intra-frequency HO (%)",
    "Inter-RAT HOSR (%)": "Inter-RAT HOSR (LTE to WCDMA) (%)",
    "SRVCC Success Rate (%)": "SRVCC Success Rate (LTE to WCDMA)",
    "VoLTE Traffic (Erl)": "VoLTE Traffic (Erl)",
    "VoLTE Drop Rate (%)": "Call Drop Rate (VoLTE)",
}

avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}
if not avail_kpis:
    st.warning("⚠️ File không có cột KPI nào để vẽ biểu đồ.")
    st.stop()


def kpi_agg(label):
    return "sum" if "Traffic" in label or "Erl" in label else "mean"


HOURLY_MODE = "Chỉ theo giờ (24h Avg)"

ctrl_col1, ctrl_col2 = st.columns([1, 1])
with ctrl_col1:
    time_mode = st.radio(
        "⏱ Thời gian:",
        [HOURLY_MODE, "Theo Ngày & Giờ (Timeline)"],
        horizontal=True,
    )

with ctrl_col2:
    sel_kpi_lbl = st.selectbox(
        "🎯 Chọn KPI kết hợp Traffic:",
        options=list(avail_kpis.keys()),
    )

sel_kpi_col = avail_kpis[sel_kpi_lbl]
agg_map = {TRAFFIC_COL: "sum", sel_kpi_col: kpi_agg(sel_kpi_lbl)}

if time_mode == HOURLY_MODE:
    c_data = filtered_df.groupby("Hour").agg(agg_map).reset_index()
    x_axis = c_data["Hour"]
    x_title = "Giờ trong ngày (0h - 23h)"
else:
    c_data = (
        filtered_df.groupby(["Date", "Hour", "DateTime"])
        .agg(agg_map)
        .reset_index()
        .sort_values(by="DateTime")
    )
    c_data["TimeLabel"] = c_data["DateTime"].dt.strftime("%d/%m %H:00")
    x_axis = c_data["TimeLabel"]
    x_title = "Thời Gian (Ngày/Giờ)"

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Bar(
        x=x_axis,
        y=c_data[TRAFFIC_COL],
        name="Traffic (GB)",
        marker_color="rgba(53, 162, 235, 0.5)",
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=x_axis,
        y=c_data[sel_kpi_col],
        name=sel_kpi_lbl,
        mode="lines+markers",
        line=dict(color="#ff4d4f", width=2.5),
    ),
    secondary_y=True,
)

fig.update_layout(
    title_text=f"📊 Biểu đồ Traffic và {sel_kpi_lbl}",
    template="plotly_dark",
    hovermode="x unified",
    height=420,
    margin=dict(l=10, r=10, t=40, b=10),
)

fig.update_xaxes(
    title_text=x_title,
    type="category" if time_mode != HOURLY_MODE else None,
)
fig.update_yaxes(title_text="Traffic (GB)", secondary_y=False, showgrid=False)
fig.update_yaxes(
    title_text=sel_kpi_lbl,
    secondary_y=True,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.1)",
)

st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ----------------------------------
# 7. WORST CELLS MATRIX & PDF REPORT
# ----------------------------------
st.subheader("⚠️ Danh Sách Worst Cells & Báo Cáo")

res_df = pd.DataFrame()
kpi_opt, top_n = "", 0

if cell_col:
    # kpi -> (cột dùng để sắp xếp, sắp xếp giảm dần?)
    worst_rules = {
        "Service Drop Rate (CDR)": ("Service Drop (all service)", True),
        "Low Downlink Throughput": ("DL_Throughput_Mbps", False),
        "Low Uplink Throughput": ("UL_Throughput_Mbps", False),
        "Low CQI (Poor RF Coverage)": ("CQI_4G", False),
        "High PRB Congestion": (
            "Resource Block Untilizing Rate Downlink (%)",
            True,
        ),
        "VoLTE Call Drop Rate": ("Call Drop Rate (VoLTE)", True),
    }

    kpi_opt = st.selectbox("🎯 Lọc Worst Cells theo KPI:", list(worst_rules.keys()))
    top_n = st.slider("Số lượng hiển thị:", 5, 30, 10)

    group_cols = [c for c in (site_col, cell_col) if c]
    agg_cols = [
        "Service Drop (all service)",
        "DL_Throughput_Mbps",
        "UL_Throughput_Mbps",
        "CQI_4G",
        "Resource Block Untilizing Rate Downlink (%)",
        "Call Drop Rate (VoLTE)",
        TRAFFIC_COL,
    ]
    cell_agg = (
        filtered_df.groupby(group_cols)
        .agg({c: "mean" for c in agg_cols if c in filtered_df.columns})
        .reset_index()
    )

    sort_col, descending = worst_rules[kpi_opt]
    if sort_col in cell_agg.columns:
        res_df = cell_agg.sort_values(by=sort_col, ascending=not descending).head(top_n)
    else:
        st.warning(f"⚠️ File không có cột dữ liệu cho tiêu chí: {kpi_opt}")
        res_df = cell_agg.head(top_n)

    st.dataframe(res_df, width="stretch")
else:
    st.info("ℹ️ File không có cột 'Tên đối tượng' nên không lập được danh sách cell.")

st.markdown("### 📄 Báo Cáo Cấp Trên")


def build_pdf_charts():
    """Dữ liệu biểu đồ (trung bình theo giờ) cho từng KPI + Total Traffic."""
    hourly_traffic = filtered_df.groupby("Hour")[TRAFFIC_COL].sum()
    items = [
        {
            "title": "Total Traffic (GB)",
            "x": list(hourly_traffic.index),
            "traffic": list(hourly_traffic.values),
        }
    ]
    for label, col in avail_kpis.items():
        h = (
            filtered_df.groupby("Hour")
            .agg({TRAFFIC_COL: "sum", col: kpi_agg(label)})
            .reset_index()
        )
        items.append(
            {
                "title": f"Traffic vs {label}",
                "x": list(h["Hour"]),
                "traffic": list(h[TRAFFIC_COL]),
                "kpi": list(h[col]),
                "label": label,
            }
        )
    return items


info_line = (
    f"Records: {len(filtered_df):,} | Sites: {num_sites} | Cells: {num_cells} | "
    f"Ngày: {len(sel_dates)}"
)
pdf_sig = repr(
    (
        sorted(map(str, sel_dates)),
        sorted(map(str, sel_sites)),
        kpi_opt,
        top_n,
    )
)

if st.button("🧾 Tạo báo cáo PDF (đủ card + biểu đồ)"):
    with st.spinner("Đang tạo báo cáo PDF..."):
        pdf_buf = generate_pdf_report(cards, build_pdf_charts(), res_df, info_line)
        st.session_state["pdf_bytes"] = pdf_buf.getvalue()
        st.session_state["pdf_sig"] = pdf_sig

if st.session_state.get("pdf_sig") == pdf_sig:
    st.download_button(
        label="📑 Tải Báo Cáo PDF",
        data=st.session_state["pdf_bytes"],
        file_name="Bao_Cao_Toi_Uu_Mang_4G.pdf",
        mime="application/pdf",
    )
elif "pdf_sig" in st.session_state:
    st.caption("Bộ lọc đã thay đổi — bấm 'Tạo báo cáo PDF' để cập nhật.")

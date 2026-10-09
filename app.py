import io
import os
import ssl
import urllib.request
import unicodedata
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

import matplotlib
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

# ---------------------------------------------------------
# DYNAMIC VIETNAMESE UNICODE FONT REGISTRATION
# ---------------------------------------------------------
def setup_vietnamese_fonts():
    """Ưu tiên đọc file DejaVuSans.ttf nằm cùng thư mục dự án."""
    local_reg = "DejaVuSans.ttf"
    local_bold = "DejaVuSans-Bold.ttf"
    
    if os.path.exists(local_reg):
        bold_path = local_bold if os.path.exists(local_bold) else local_reg
        return local_reg, bold_path, "DejaVu Sans"

    search_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]
    
    candidates = [
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVu Sans"),
        ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "Liberation Sans"),
    ]

    for s_dir in search_dirs:
        if os.path.exists(s_dir):
            for root, dirs, files in os.walk(s_dir):
                file_map = {f.lower(): f for f in files}
                for reg_name, bold_name, family in candidates:
                    if reg_name.lower() in file_map:
                        b_path = os.path.join(root, file_map[bold_name.lower()]) if bold_name.lower() in file_map else os.path.join(root, file_map[reg_name.lower()])
                        return (
                            os.path.join(root, file_map[reg_name.lower()]),
                            b_path,
                            family,
                        )

    return None, None, "Helvetica"


font_reg_path, font_bold_path, font_family_name = setup_vietnamese_fonts()

FONT_NAME = "VietFont"
FONT_NAME_BOLD = "VietFont-Bold"

if font_reg_path and font_bold_path:
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, font_reg_path))
        pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, font_bold_path))
        
        addMapping(FONT_NAME, 0, 0, FONT_NAME)
        addMapping(FONT_NAME, 1, 0, FONT_NAME_BOLD)
        addMapping(FONT_NAME, 0, 1, FONT_NAME)
        addMapping(FONT_NAME, 1, 1, FONT_NAME_BOLD)

        addMapping(FONT_NAME_BOLD, 0, 0, FONT_NAME_BOLD)
        addMapping(FONT_NAME_BOLD, 1, 0, FONT_NAME_BOLD)
        addMapping(FONT_NAME_BOLD, 0, 1, FONT_NAME_BOLD)
        addMapping(FONT_NAME_BOLD, 1, 1, FONT_NAME_BOLD)
    except Exception:
        FONT_NAME = "Helvetica"
        FONT_NAME_BOLD = "Helvetica-Bold"
else:
    FONT_NAME = "Helvetica"
    FONT_NAME_BOLD = "Helvetica-Bold"

addMapping("Helvetica", 0, 0, "Helvetica")
addMapping("Helvetica", 1, 0, "Helvetica-Bold")
addMapping("Helvetica", 0, 1, "Helvetica-Oblique")
addMapping("Helvetica", 1, 1, "Helvetica-BoldOblique")

matplotlib.rcParams["font.sans-serif"] = [font_family_name, "DejaVu Sans", "Liberation Sans", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------
# 1. CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="4G RAN Report",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main { background: #0b0e14; }
    div[data-testid="stSidebar"] { background: #11151f; }
    
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

    div[data-testid="stFileUploaderDropzoneInstructions"] > * {
        display: none !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"]::after {
        content: "50MB per file • CSV";
        font-size: 14px;
        color: #8b9bb4;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 2. FILE MẪU & PDF REPORT
# ---------------------------------------------------------
def get_sample_file_bytes():
    for fname in ["4G_Sample - Copy.csv", "4G_Sample.csv", "4G.csv"]:
        if os.path.exists(fname):
            with open(fname, "rb") as f:
                return f.read(), fname
    return None, None


def generate_pdf_report(summary, hourly_trend_df, top10_sites, top10_cells, worst10_cssr, worst10_dcr, worst10_intra_ho, worst10_inter_ho, fb_cell_counts=None, fb_tf_df=None, cell_type_counts=None, fb_type_xtab=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    
    t_style = ParagraphStyle("T", fontName=FONT_NAME, fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    h2_style = ParagraphStyle("H2", fontName=FONT_NAME, fontSize=11, textColor=colors.HexColor("#1e293b"), spaceBefore=8, spaceAfter=4)
    norm_style = ParagraphStyle("N", fontName=FONT_NAME, fontSize=8.5, textColor=colors.HexColor("#334155"))

    now_str = pd.Timestamp.now().strftime("%d/%m/%Y")

    story.append(Paragraph("BÁO CÁO ĐÁNH GIÁ CHẤT LƯỢNG MẠNG 4G", t_style))
    story.append(Paragraph(f"Thời gian xuất báo cáo: {now_str} | RNOC2", norm_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=10))

    # MỤC I. 10 VISUAL KPI CARDS
    story.append(Paragraph("I. TỔNG QUAN KPI", h2_style))
    story.append(Spacer(1, 4))

    card_t_style = ParagraphStyle('CT', fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor('#475569'), leading=9)
    card_v_style = ParagraphStyle('CV', fontName=FONT_NAME, fontSize=13, textColor=colors.HexColor('#0f172a'), leading=15)
    card_s_style = ParagraphStyle('CS', fontName=FONT_NAME, fontSize=6.5, textColor=colors.HexColor('#64748b'), leading=8)

    def create_pdf_card(cat, title, val, target, remark, color_hex="#10b981"):
        p_t = Paragraph(f"<b>{cat.upper()}</b><br/>{title}", card_t_style)
        p_v = Paragraph(f"<font color='{color_hex}'><b>{val}</b></font>", card_v_style)
        p_s = Paragraph(f"<b>Target:</b> {target}<br/><i>{remark}</i>", card_s_style)
        
        c_tbl = Table([[p_t], [p_v], [p_s]], colWidths=[142])
        c_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]))
        return c_tbl

    cards_row1 = [
        create_pdf_card("Data Traffic", "Total Data Traffic", f"{summary.get('tf',0):,.0f} GB", "N/A", "Tải tốt", "#2563eb"),
        create_pdf_card("Accessibility", "Call Setup SR", f"{summary.get('cssr',0):.2f}%", ">=99.00%", "Rất tốt", "#059669" if summary.get('cssr',0)>=99.0 else "#d97706"),
        create_pdf_card("Retainability", "Service Drop Rate", f"{summary.get('drop',0):.3f}%", "<=1.000%", "Ổn định", "#059669" if summary.get('drop',0)<=1.0 else "#dc2626"),
        create_pdf_card("Integrity", "User DL Throughput", f"{summary.get('dl',0):.2f} M", ">20.0M", "Đạt chuẩn", "#059669" if summary.get('dl',0)>20 else "#d97706"),
        create_pdf_card("Integrity", "User UL Throughput", f"{summary.get('ul',0):.2f} M", ">=1.5M", "Đạt chuẩn", "#059669" if summary.get('ul',0)>=1.5 else "#d97706"),
    ]

    cards_row2 = [
        create_pdf_card("Radio Quality", "CQI 4G Index", f"{summary.get('cqi',0):.2f}%", ">=95.00%", "Vùng phủ tốt", "#059669" if summary.get('cqi',0)>=95 else "#d97706"),
        create_pdf_card("Capacity & Load", "PRB DL Utilization", f"{summary.get('prb',0):.2f}%", "<=35.00%", "Dồi dào", "#059669" if summary.get('prb',0)<=35 else "#dc2626"),
        create_pdf_card("Mobility", "Intra-freq HO SR", f"{summary.get('intra',0):.2f}%", ">=98.00%", "Mượt mà", "#059669" if summary.get('intra',0)>=98 else "#d97706"),
        create_pdf_card("Mobility", "Inter-freq HO SR", f"{summary.get('inter',0):.2f}%", ">=98.00%", "Chuyển giao liên tần", "#059669" if summary.get('inter',0)>=98 else "#d97706"),
        create_pdf_card("Voice Continuity", "SRVCC Success Rate", f"{summary.get('srvcc',0):.2f}%", ">=95.00%", "Đảm bảo", "#059669" if summary.get('srvcc',0)>=95 else "#d97706"),
    ]

    grid_cards = Table([cards_row1, cards_row2], colWidths=[150]*5)
    grid_cards.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(grid_cards)
    story.append(Spacer(1, 8))

    # MỤC II. FREQBAND CHARTS
    _has = lambda d: d is not None and not d.empty
    if _has(fb_cell_counts) or _has(fb_tf_df) or _has(cell_type_counts):
        story.append(Paragraph("II. THỐNG KÊ PHÂN BỔ CELL VÀ TRAFFIC THEO FREQBAND", h2_style))
        story.append(Spacer(1, 2))

        fb_img_buf = io.BytesIO()
        fig_fb, (ax1_fb, ax_ct, ax2_fb) = plt.subplots(1, 3, figsize=(11, 2.8), dpi=150)
        fb_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

        def _donut(ax, labels, sizes, cols, title):
            _, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct=lambda p: f"{p:.1f}%", startangle=90,
                colors=cols, wedgeprops=dict(width=0.45, edgecolor='white')
            )
            for t in texts:
                t.set_fontsize(7.5)
            for at in autotexts:
                at.set_fontsize(7)
                at.set_weight('bold')
            ax.set_title(title, fontsize=8.5, fontweight='bold', pad=6)

        # (1) Số lượng cell theo Freqband
        if _has(fb_cell_counts):
            fb_labels = [f"{b} ({n})" for b, n in zip(fb_cell_counts["Freqband"], fb_cell_counts["Số lượng Cell"])]
            fb_sizes = fb_cell_counts["Số lượng Cell"].tolist()
            _donut(ax1_fb, fb_labels, fb_sizes, fb_colors[:len(fb_labels)], "Số lượng Cell theo Freqband")
        else:
            ax1_fb.axis('off')

        # (2) Số lượng cell theo loại cell (VNP / MORAN)
        if _has(cell_type_counts):
            ct_cmap = {"VNP": "#3b82f6", "MORAN": "#f59e0b"}
            ct_labels = [f"{t} ({n})" for t, n in zip(cell_type_counts["Cell Type"], cell_type_counts["Số lượng Cell"])]
            ct_sizes = cell_type_counts["Số lượng Cell"].tolist()
            ct_cols = [ct_cmap.get(t, '#94a3b8') for t in cell_type_counts["Cell Type"]]
            _donut(ax_ct, ct_labels, ct_sizes, ct_cols, "Số lượng Cell theo Loại Cell")
        else:
            ax_ct.axis('off')

        # (3) Traffic theo Freqband
        if _has(fb_tf_df):
            fb_bands = fb_tf_df["Freqband"].tolist()
            fb_traffics = fb_tf_df["Total Data Traffic Volume (GB)"].tolist()
            fb_bars = ax2_fb.bar(fb_bands, fb_traffics, color='#0284c7', width=0.45, alpha=0.85)
            ax2_fb.set_title("Tổng Traffic Volume (GB) theo Freqband", fontsize=8.5, fontweight='bold', pad=6)
            ax2_fb.set_ylabel("Traffic (GB)", fontsize=7.5)
            ax2_fb.tick_params(axis='both', labelsize=7)
            ax2_fb.grid(True, linestyle='--', alpha=0.25, axis='y')

            max_tf = max(fb_traffics) if fb_traffics else 1
            ax2_fb.set_ylim(0, max_tf * 1.18)

            for bar in fb_bars:
                yval = bar.get_height()
                ax2_fb.text(
                    bar.get_x() + bar.get_width()/2.0,
                    yval + (max_tf * 0.02),
                    f"{yval:,.0f}",
                    ha='center',
                    va='bottom',
                    fontsize=6.5,
                    fontweight='bold'
                )
        else:
            ax2_fb.axis('off')

        plt.tight_layout()
        plt.savefig(fb_img_buf, format='png', dpi=150)
        plt.close()
        fb_img_buf.seek(0)
        story.append(Image(fb_img_buf, width=740, height=188))
        story.append(Spacer(1, 6))

        # Bảng thống kê: Freqband x Loại cell (+ Traffic)
        if _has(fb_type_xtab):
            _ps = ParagraphStyle("FBT", fontName=FONT_NAME, fontSize=8, textColor=colors.HexColor("#334155"), alignment=1)
            _pw = ParagraphStyle("FBTW", parent=_ps, textColor=colors.white)

            def _c(txt, bold=False, white=False):
                return Paragraph(f"<b>{txt}</b>" if bold else str(txt), _pw if white else _ps)

            tf_map = {}
            if _has(fb_tf_df):
                tf_map = dict(zip(fb_tf_df["Freqband"], fb_tf_df["Total Data Traffic Volume (GB)"]))
            grand = int(fb_type_xtab["Tổng"].sum()) or 1

            story.append(Paragraph("<b>Thống kê số lượng Cell theo Freqband và Loại Cell (VNP / MORAN):</b>", norm_style))
            story.append(Spacer(1, 2))
            hdr = ["Freqband", "Cell VNP", "Cell MORAN", "Tổng Cell", "Tỷ lệ (%)", "Traffic (GB)"]
            rows = [[_c(h, True, True) for h in hdr]]
            for _, r in fb_type_xtab.iterrows():
                rows.append([
                    _c(r["Freqband"]), _c(int(r["VNP"])), _c(int(r["MORAN"])), _c(int(r["Tổng"])),
                    _c(f"{r['Tổng'] / grand * 100:.1f}"),
                    _c(f"{tf_map[r['Freqband']]:,.1f}" if r["Freqband"] in tf_map and pd.notnull(tf_map[r["Freqband"]]) else "-"),
                ])
            tot_tf = sum(v for v in tf_map.values() if pd.notnull(v)) if tf_map else None
            rows.append([
                _c("Tổng", True), _c(int(fb_type_xtab["VNP"].sum()), True), _c(int(fb_type_xtab["MORAN"].sum()), True),
                _c(grand if grand != 1 or fb_type_xtab["Tổng"].sum() else 0, True), _c("100.0", True),
                _c(f"{tot_tf:,.1f}" if tot_tf is not None else "-", True),
            ])
            t_fb = Table(rows, colWidths=[110, 110, 110, 110, 110, 130], hAlign="LEFT")
            t_fb.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0284c7")),
                ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            story.append(t_fb)
        story.append(Spacer(1, 10))

    # MỤC III. CHARTS XU HƯỚNG
    story.append(Paragraph("III. XU HƯỚNG CÁC CHỈ SỐ KPI THEO KHUNG GIỜ/NGÀY", h2_style))
    story.append(Spacer(1, 4))

    if not hourly_trend_df.empty:
        df_chart = hourly_trend_df.copy()
        x_labels = []
        for _, r in df_chart.iterrows():
            if "TimeLabel" in r and pd.notnull(r["TimeLabel"]) and str(r["TimeLabel"]).strip() != "":
                x_labels.append(str(r["TimeLabel"]))
            elif "DateTime" in r and pd.notnull(r["DateTime"]):
                x_labels.append(pd.to_datetime(r["DateTime"]).strftime("%d/%m %H:00"))
            elif "Date" in r and pd.notnull(r["Date"]):
                d_str = pd.to_datetime(r["Date"]).strftime("%d/%m") if pd.notnull(r["Date"]) else ""
                h_str = f"{int(r.get('Hour', 0)):02d}:00"
                x_labels.append(f"{d_str} {h_str}".strip())
            else:
                x_labels.append(f"{int(r.get('Hour', 0)):02d}:00")
        n_pts = len(x_labels)
        step = max(1, n_pts // 24)

        tf_vals = df_chart.get("Total Data Traffic Volume (GB)", pd.Series([0]*n_pts)).values
        cssr_vals = df_chart.get("Call Setup Success Rate", pd.Series([0]*n_pts)).values
        drop_vals = df_chart.get("Service Drop (all service)", pd.Series([0]*n_pts)).values
        dl_vals = df_chart.get("DL_Throughput_Mbps", pd.Series([0]*n_pts)).values
        intra_vals = df_chart.get("Intra-frequency HO (%)", pd.Series([0]*n_pts)).values
        inter_vals = df_chart.get("Inter-frequency HO (%)", pd.Series([0]*n_pts)).values
        
        volte_cssr_vals = df_chart.get("VoLTE E-RAB Call Setup Success Rate", pd.Series([100]*n_pts)).values
        volte_drop_vals = df_chart.get("Call Drop Rate (VoLTE)", pd.Series([0]*n_pts)).values
        volte_tf_vals = df_chart.get("VoLTE Traffic (Erl)", pd.Series([0]*n_pts)).values

        def make_single_chart(chart_title, bar_vals, line1_vals, line1_lbl, line1_color, 
                              line2_vals=None, line2_lbl=None, line2_color=None, 
                              bar_lbl="Traffic (GB)", is_bar_volte=False):
            img_b = io.BytesIO()
            fig, ax = plt.subplots(figsize=(11, 3.568), dpi=150)

            ax.set_xticks(range(0, n_pts, step))
            ax.set_xticklabels([x_labels[i] for i in range(0, n_pts, step)], rotation=30 if n_pts > 15 else 0, ha='right' if n_pts > 15 else 'center', fontsize=6)
            ax.grid(True, linestyle='--', alpha=0.25)

            if bar_vals is not None:
                b_color = '#a855f7' if is_bar_volte else '#3b82f6'
                ax.bar(range(n_pts), bar_vals, color=b_color, alpha=0.45, label=bar_lbl, width=0.8)
                ax.set_ylabel(bar_lbl, color='#1d4ed8' if not is_bar_volte else '#7e22ce', fontweight='bold', fontsize=7.5)
                ax.tick_params(axis='y', labelcolor='#1d4ed8' if not is_bar_volte else '#7e22ce', labelsize=6.5)

            if line2_vals is None:
                ax_t = ax.twinx() if bar_vals is not None else ax
                ax_t.plot(range(n_pts), line1_vals, color=line1_color, marker='o', markersize=2.5, linewidth=1.4, label=line1_lbl)
                ax_t.set_ylabel(line1_lbl, color=line1_color, fontweight='bold', fontsize=7.5)
                ax_t.tick_params(axis='y', labelcolor=line1_color, labelsize=6.5)
            else:
                ax.plot(range(n_pts), line1_vals, color=line1_color, marker='o', markersize=2.5, linewidth=1.4, label=line1_lbl)
                ax.plot(range(n_pts), line2_vals, color=line2_color, marker='s', markersize=2.5, linewidth=1.4, linestyle='--', label=line2_lbl)
                ax.set_ylabel("Handover SR (%)", color='#0f172a', fontweight='bold', fontsize=7.5)
                ax.set_ylim(80, 100.5)
                ax.legend(fontsize=6.5, loc='lower right')

            ax.set_title(chart_title, fontsize=8.5, fontweight='bold', pad=4)
            plt.tight_layout()
            plt.savefig(img_b, format='png', dpi=150)
            plt.close()
            img_b.seek(0)
            return Image(img_b, width=740, height=240)

        c1_img = make_single_chart("Chart 1: Tỷ lệ CSSR (%) & Data Traffic (GB)", tf_vals, cssr_vals, "CSSR (%)", "#10b981")
        story.append(c1_img)
        story.append(Spacer(1, 8))

        c2_img = make_single_chart("Chart 2: Tỷ lệ DCR (%) & Data Traffic (GB)", tf_vals, drop_vals, "DCR (%)", "#ef4444")
        story.append(c2_img)
        story.append(Spacer(1, 8))

        story.append(PageBreak())

        c3_img = make_single_chart("Chart 3: Download Throughput (Mbps) & Data Traffic (GB)", tf_vals, dl_vals, "DL Thrp (Mbps)", "#8b5cf6")
        story.append(c3_img)
        story.append(Spacer(1, 8))

        c4_img = make_single_chart("Chart 4: So sánh Intra-freq HO (%) & Inter-freq HO (%)", None, intra_vals, "Intra-freq HO (%)", "#059669", line2_vals=inter_vals, line2_lbl="Inter-freq HO (%)", line2_color="#d97706")
        story.append(c4_img)
        story.append(Spacer(1, 8))

        story.append(PageBreak())

        c5_img = make_single_chart("Chart 5: VoLTE CSSR (%) & VoLTE Traffic (Erl)", volte_tf_vals, volte_cssr_vals, "VoLTE CSSR (%)", "#10b981", bar_lbl="VoLTE Traffic (Erl)", is_bar_volte=True)
        story.append(c5_img)
        story.append(Spacer(1, 8))

        c6_img = make_single_chart("Chart 6: VoLTE DCR (%) & VoLTE Traffic (Erl)", volte_tf_vals, volte_drop_vals, "VoLTE DCR (%)", "#dc2626", bar_lbl="VoLTE Traffic (Erl)", is_bar_volte=True)
        story.append(c6_img)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # MỤC IV. TOP 10 SITE & CELL
    story.append(Paragraph("IV. DANH SÁCH TOP 10 HIGH TRAFFIC SITE & CELL", h2_style))
    story.append(Spacer(1, 4))

    def p_cell(text, is_bold=False, align='left', color_hex='#0f172a'):
        p_st = ParagraphStyle('PC', fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor(color_hex), leading=9, alignment=0 if align=='left' else 1)
        txt = f"<b>{text}</b>" if is_bold else str(text)
        return Paragraph(txt, p_st)

    if not top10_cells.empty:
        story.append(Paragraph("<b>1. Top 10 Cell có Lưu lượng Traffic Volume (GB) cao nhất:</b>", norm_style))
        story.append(Spacer(1, 2))
        tr_cols = [c for c in top10_cells.columns if c in ["Site Name", "Tên đối tượng", "Cell Name", "Total Data Traffic Volume (GB)", "DL_Throughput_Mbps", "Resource Block Untilizing Rate Downlink (%)"]][:5]
        tr_sub = top10_cells[tr_cols].head(10)

        tr_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Cell Name", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff'),
            p_cell("DL Thrp (Mbps)", True, color_hex='#ffffff'),
            p_cell("PRB DL (%)", True, color_hex='#ffffff')
        ]]
        for _, row in tr_sub.iterrows():
            tr_data.append([
                p_cell(row.iloc[0] if len(row) > 0 else ""),
                p_cell(row.iloc[1] if len(row) > 1 else ""),
                p_cell(f"{row.iloc[2]:,.2f}" if len(row) > 2 and pd.notnull(row.iloc[2]) else "0.00"),
                p_cell(f"{row.iloc[3]:.2f}" if len(row) > 3 and pd.notnull(row.iloc[3]) else "0.00"),
                p_cell(f"{row.iloc[4]:.2f}" if len(row) > 4 and pd.notnull(row.iloc[4]) else "0.00")
            ])

        t_tr = Table(tr_data, colWidths=[130, 180, 110, 110, 110])
        t_tr.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#047857")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_tr)
        story.append(Spacer(1, 8))

    if not top10_sites.empty:
        story.append(Paragraph("<b>2. Top 10 Site có Lưu lượng Traffic Volume (GB) cao nhất:</b>", norm_style))
        story.append(Spacer(1, 2))
        ts_cols = [c for c in top10_sites.columns if c in ["Site Name", "Total Data Traffic Volume (GB)", "DL_Throughput_Mbps", "Resource Block Untilizing Rate Downlink (%)"]][:4]
        ts_sub = top10_sites[ts_cols].head(10)

        ts_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff'),
            p_cell("DL Thrp Avg (Mbps)", True, color_hex='#ffffff'),
            p_cell("PRB DL Avg (%)", True, color_hex='#ffffff')
        ]]
        for _, row in ts_sub.iterrows():
            ts_data.append([
                p_cell(row.iloc[0] if len(row) > 0 else ""),
                p_cell(f"{row.iloc[1]:,.2f}" if len(row) > 1 and pd.notnull(row.iloc[1]) else "0.00"),
                p_cell(f"{row.iloc[2]:.2f}" if len(row) > 2 and pd.notnull(row.iloc[2]) else "0.00"),
                p_cell(f"{row.iloc[3]:.2f}" if len(row) > 3 and pd.notnull(row.iloc[3]) else "0.00")
            ])

        t_ts = Table(ts_data, colWidths=[180, 150, 150, 160])
        t_ts.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f766e")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_ts)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # MỤC V. WORST 10 CHO CÁC KPI
    story.append(Paragraph("V. DANH SÁCH WORST 10 CELLS CHO CÁC KPI CHÍNH (CSSR, DCR, HANDOVER)", h2_style))
    story.append(Spacer(1, 4))

    if not worst10_cssr.empty:
        story.append(Paragraph("<b>1. Worst 10 Cells theo Tỷ lệ Thiết lập Cuộc gọi Thấp (CSSR):</b>", norm_style))
        story.append(Spacer(1, 2))
        w_sub = worst10_cssr.head(10)
        
        w_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Cell Name", True, color_hex='#ffffff'),
            p_cell("CSSR (%)", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff')
        ]]
        for _, row in w_sub.iterrows():
            w_data.append([
                p_cell(row.get("Site Name", "")),
                p_cell(row.get("Tên đối tượng", row.get("Cell Name", ""))),
                p_cell(f"{row.get('Call Setup Success Rate', 0):.2f}%"),
                p_cell(f"{row.get('Total Data Traffic Volume (GB)', 0):,.2f}")
            ])
        t_cssr = Table(w_data, colWidths=[180, 220, 170, 170])
        t_cssr.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#991b1b")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_cssr)
        story.append(Spacer(1, 8))

    if not worst10_dcr.empty:
        story.append(Paragraph("<b>2. Worst 10 Cells theo Tỷ lệ Rớt Dịch vụ Cao (DCR / Drop Rate):</b>", norm_style))
        story.append(Spacer(1, 2))
        w_sub = worst10_dcr.head(10)
        
        w_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Cell Name", True, color_hex='#ffffff'),
            p_cell("Service Drop Rate (%)", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff')
        ]]
        for _, row in w_sub.iterrows():
            w_data.append([
                p_cell(row.get("Site Name", "")),
                p_cell(row.get("Tên đối tượng", row.get("Cell Name", ""))),
                p_cell(f"{row.get('Service Drop (all service)', 0):.3f}%"),
                p_cell(f"{row.get('Total Data Traffic Volume (GB)', 0):,.2f}")
            ])
        t_dcr = Table(w_data, colWidths=[180, 220, 170, 170])
        t_dcr.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#b91c1c")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_dcr)
        story.append(Spacer(1, 8))

    if not worst10_intra_ho.empty:
        story.append(Paragraph("<b>3. Worst 10 Cells theo Tỷ lệ Chuyển giao Nội băng Thấp (Intra-freq HO):</b>", norm_style))
        story.append(Spacer(1, 2))
        w_sub = worst10_intra_ho.head(10)
        
        w_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Cell Name", True, color_hex='#ffffff'),
            p_cell("Intra-freq HO (%)", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff')
        ]]
        for _, row in w_sub.iterrows():
            w_data.append([
                p_cell(row.get("Site Name", "")),
                p_cell(row.get("Tên đối tượng", row.get("Cell Name", ""))),
                p_cell(f"{row.get('Intra-frequency HO (%)', 0):.2f}%"),
                p_cell(f"{row.get('Total Data Traffic Volume (GB)', 0):,.2f}")
            ])
        t_ho = Table(w_data, colWidths=[180, 220, 170, 170])
        t_ho.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#c2410c")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_ho)
        story.append(Spacer(1, 8))

    if not worst10_inter_ho.empty:
        story.append(Paragraph("<b>4. Worst 10 Cells theo Tỷ lệ Chuyển giao Liên tần Thấp (Inter-freq HO):</b>", norm_style))
        story.append(Spacer(1, 2))
        w_sub = worst10_inter_ho.head(10)
        
        w_data = [[
            p_cell("Site Name", True, color_hex='#ffffff'),
            p_cell("Cell Name", True, color_hex='#ffffff'),
            p_cell("Inter-freq HO (%)", True, color_hex='#ffffff'),
            p_cell("Total Traffic (GB)", True, color_hex='#ffffff')
        ]]
        for _, row in w_sub.iterrows():
            w_data.append([
                p_cell(row.get("Site Name", "")),
                p_cell(row.get("Tên đối tượng", row.get("Cell Name", ""))),
                p_cell(f"{row.get('Inter-frequency HO (%)', 0):.2f}%"),
                p_cell(f"{row.get('Total Data Traffic Volume (GB)', 0):,.2f}")
            ])
        t_inter_ho = Table(w_data, colWidths=[180, 220, 170, 170])
        t_inter_ho.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#ea580c")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t_inter_ho)

    doc.build(story)
    buf.seek(0)
    return buf


# ---------------------------------------------------------
# 3. DATA PROCESSING
# ---------------------------------------------------------
@st.cache_data
def process_data(file_input):
    # thousands=',' : số dạng "5,512.99" (dấu phẩy ngăn cách hàng nghìn) phải được đọc thành số,
    # nếu không pd.to_numeric(errors="coerce") sẽ biến toàn bộ giá trị >= 1000 thành NaN
    df = pd.read_csv(file_input, thousands=",")

    # Chuẩn hóa tên cột
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]

    # Phòng hờ: cột số vẫn là chuỗi có dấu phẩy (vd. file đã đọc kiểu khác) -> bỏ dấu phẩy
    def _clean_num(series):
        if series.dtype == object or str(series.dtype).startswith("str"):
            return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")
        return pd.to_numeric(series, errors="coerce")

    # Mapping Alias cột
    alias_map = {
        "DateTime": ["DateTime", "Thời gian", "Time", "timestamp", "Date", "Ngày"],
        "Hour": ["Giờ", "Hour", "hour"],

        "Site Name": ["Site Name", "Site", "Tên Site", "eNodeB Name", "eNodeB", "NodeB Name"],
        "Tên đối tượng": ["Tên đối tượng", "Cell Name", "Cell", "Tên Cell", "Object Name", "CellId"],

        "Total Data Traffic Volume (GB)": ["Total Data Traffic Volume (GB)", "Total Data Traffic (GB)", "Data Traffic (GB)", "Total Traffic (GB)", "Traffic (GB)", "Traffic_GB"],
        "Traffic Volumn DL (GB)": ["Traffic Volumn DL (GB)", "Traffic Volume DL (GB)", "DL Traffic (GB)", "Data Traffic DL (GB)", "Traffic DL (GB)"],
        "Traffic Volume UL (GB)": ["Traffic Volume UL (GB)", "Traffic Volumn UL (GB)", "UL Traffic (GB)", "Data Traffic UL (GB)", "Traffic UL (GB)"],

        "Resource Block Untilizing Rate Downlink (%)": [
            "Resource Block Untilizing Rate Downlink (%)",
            "Resource Block Utilizing Rate Downlink (%)",
            "PRB Utilization DL (%)",
            "PRB DL Utilization (%)",
            "Resource Block Utilization Rate Downlink (%)",
            "PRB Utilization Downlink (%)",
            "DL PRB Utilization (%)",
            "PRB DL (%)",
            "DL PRB Utilization Rate (%)"
        ],

        "CQI_4G": ["CQI_4G", "CQI 4G Index (%)", "CQI Index", "CQI >= 7 (%)", "CQI 4G", "CQI"],
        "Call Setup Success Rate": ["Call Setup Success Rate", "CSSR (%)", "Call Setup Success Rate (%)", "CSSR"],
        "Service Drop (all service)": ["Service Drop (all service)", "Service Drop Rate (%)", "Service Drop Rate", "DCR (%)", "Call Drop Rate (%)", "Drop Rate (%)"],

        "Intra-frequency HO (%)": ["Intra-frequency HO (%)", "Intra-freq HO SR (%)", "Intra HO (%)", "Intra-frequency HO Success Rate (%)"],
        "Inter-frequency HO (%)": ["Inter-frequency HO (%)", "Inter-freq HO SR (%)", "Inter HO (%)", "Inter-frequency HO Success Rate (%)"],
        "Inter-RAT HOSR (LTE to WCDMA) (%)": ["Inter-RAT HOSR (LTE to WCDMA) (%)", "Inter-RAT HOSR (%)", "IRAT HO (%)"],
        "SRVCC Success Rate (LTE to WCDMA)": ["SRVCC Success Rate (LTE to WCDMA)", "SRVCC Success Rate (%)", "SRVCC SR (%)"],

        "Call Drop Rate (VoLTE)": ["Call Drop Rate (VoLTE)", "VoLTE Drop Rate (%)", "VoLTE DCR (%)"],
        "VoLTE E-RAB Call Setup Success Rate": ["VoLTE E-RAB Call Setup Success Rate", "VoLTE CSSR (%)", "VoLTE Call Setup Success Rate (%)"],
        "VoLTE Traffic (Erl)": ["VoLTE Traffic (Erl)", "VoLTE Traffic"]
    }

    for std_col, aliases in alias_map.items():
        if std_col not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    df.rename(columns={alias: std_col}, inplace=True)
                    break

    # Trích xuất và Quy đổi Throughput Kbps -> Mbps
    dl_kbps_cols = [
        "User Downlink Average Throughput (Kbps)",
        "User Downlink Average Throughput(Kbps)",
        "User Downlink Throughput (Kbps)",
        "User DL Throughput (Kbps)",
        "DL Throughput (Kbps)",
        "DL_Throughput_Kbps"
    ]
    ul_kbps_cols = [
        "User Uplink Average Throughput (Kbps)",
        "User Uplink Average Throughput(Kbps)",
        "User Uplink Throughput (Kbps)",
        "User UL Throughput (Kbps)",
        "UL Throughput (Kbps)",
        "UL_Throughput_Kbps"
    ]

    found_dl_kbps = next((c for c in dl_kbps_cols if c in df.columns), None)
    if found_dl_kbps:
        df["User Downlink Average Throughput (Kbps)"] = _clean_num(df[found_dl_kbps])
        df["DL_Throughput_Mbps"] = df["User Downlink Average Throughput (Kbps)"] / 1000.0
    else:
        dl_mbps_cols = ["DL_Throughput_Mbps", "User Downlink Average Throughput (Mbps)", "DL Throughput (Mbps)", "User DL Throughput (Mbps)"]
        found_dl_mbps = next((c for c in dl_mbps_cols if c in df.columns), None)
        if found_dl_mbps:
            df["DL_Throughput_Mbps"] = _clean_num(df[found_dl_mbps])
            df["User Downlink Average Throughput (Kbps)"] = df["DL_Throughput_Mbps"] * 1000.0

    found_ul_kbps = next((c for c in ul_kbps_cols if c in df.columns), None)
    if found_ul_kbps:
        df["User Uplink Average Throughput (Kbps)"] = _clean_num(df[found_ul_kbps])
        df["UL_Throughput_Mbps"] = df["User Uplink Average Throughput (Kbps)"] / 1000.0
    else:
        ul_mbps_cols = ["UL_Throughput_Mbps", "User Uplink Average Throughput (Mbps)", "UL Throughput (Mbps)", "User UL Throughput (Mbps)"]
        found_ul_mbps = next((c for c in ul_mbps_cols if c in df.columns), None)
        if found_ul_mbps:
            df["UL_Throughput_Mbps"] = _clean_num(df[found_ul_mbps])
            df["User Uplink Average Throughput (Kbps)"] = df["UL_Throughput_Mbps"] * 1000.0

    # Parse DateTime & Hour
    # Xác định "có giờ thật hay không" TRƯỚC khi tạo cột Hour (tránh việc cột Hour tự tạo làm has_hour luôn = True)
    has_hour_col = "Hour" in df.columns
    has_hour = False

    if "DateTime" in df.columns:
        df["DateTime"] = pd.to_datetime(df["DateTime"], dayfirst=True, errors="coerce")
        df["DateTime"] = df["DateTime"].fillna(pd.Timestamp.now())
        dt_has_time = bool(((df["DateTime"].dt.hour != 0) | (df["DateTime"].dt.minute != 0)).any())

        if has_hour_col:
            # File có cột Giờ riêng (vd. "13:00" hoặc 13) -> ghép vào DateTime
            hr = pd.to_numeric(df["Hour"].astype(str).str.extract(r"(\d{1,2})")[0], errors="coerce")
            if hr.notnull().any():
                df["Hour"] = hr.fillna(0).astype(int)
                if not dt_has_time:
                    df["DateTime"] = df["DateTime"].dt.normalize() + pd.to_timedelta(df["Hour"], unit="h")
                has_hour = True
            else:
                df["Hour"] = df["DateTime"].dt.hour
                has_hour = dt_has_time
        else:
            df["Hour"] = df["DateTime"].dt.hour
            has_hour = dt_has_time   # Chỉ có ngày (không có giờ) -> False

        df["Date"] = df["DateTime"].dt.date
    else:
        df["DateTime"] = pd.Timestamp.now()
        df["Date"] = df["DateTime"].dt.date
        df["Hour"] = 0

    df["_has_hour_col"] = has_hour

    # Freqband
    cell_col_name = "Tên đối tượng" if "Tên đối tượng" in df.columns else ("Cell Name" if "Cell Name" in df.columns else None)
    if cell_col_name and cell_col_name in df.columns:
        # 2 loại cell:
        #   - VNP   : "4G-TPH035S11-TGG"      -> freqband = ký tự thứ 11 (index 10)      -> F1
        #   - MORAN : "VNP-4G-TNO801M32-DTP"  -> bỏ tiền tố "VNP-" rồi lấy index 10     -> F3
        cell_s = df[cell_col_name].astype(str).str.strip()
        is_moran = cell_s.str.upper().str.startswith("VNP-")
        core = cell_s.where(~is_moran, cell_s.str[4:])
        fb_char = core.str[10]                                   # NaN nếu tên quá ngắn
        df["Freqband"] = ("F" + fb_char).fillna("N/A")
        df["Cell Type"] = np.where(is_moran, "MORAN", "VNP")

    num_cols = [
        "User Downlink Average Throughput (Kbps)",
        "User Uplink Average Throughput (Kbps)",
        "DL_Throughput_Mbps",
        "UL_Throughput_Mbps",
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
            df[col] = _clean_num(df[col])

    return df


# Hàm gom nhóm tính Trung bình Trọng số chuẩn xác
def aggregate_kpis(df_in, group_cols):
    """Gom nhóm + trung bình có trọng số theo Traffic (bản vectorized, không dùng groupby.apply).

    Thay vì gọi một hàm Python cho từng group (rất chậm khi có hàng nghìn cell),
    ta tính sẵn các cột tích (kpi*trọng số) rồi dùng groupby.agg một lần.
    """
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    group_cols = list(group_cols)

    TOT = 'Total Data Traffic Volume (GB)'
    DLT = 'Traffic Volumn DL (GB)'
    ULT = 'Traffic Volume UL (GB)'
    VOL = 'VoLTE Traffic (Erl)'
    cols = df_in.columns

    nan_s = pd.Series(np.nan, index=df_in.index)
    tot = df_in[TOT] if TOT in cols else nan_s
    tmp = {'_tot': tot}          # cột sẽ SUM
    mean_cols = {}               # cột sẽ MEAN
    spec = {'_tot': 'sum'}

    def add_weighted(key, x, weights):
        """Với mỗi trọng số w_i: tính sum(x*w) và sum(w) trên các dòng hợp lệ; thêm mean(x) làm fallback."""
        for i, w in enumerate(weights):
            valid = x.notna() & w.notna()
            tmp[f'{key}__n{i}'] = (x * w).where(valid)
            tmp[f'{key}__d{i}'] = w.where(valid)
            spec[f'{key}__n{i}'] = 'sum'
            spec[f'{key}__d{i}'] = 'sum'
        mean_cols[f'{key}__m'] = x
        spec[f'{key}__m'] = 'mean'

    if DLT in cols:
        tmp['_dlt'] = df_in[DLT]; spec['_dlt'] = 'sum'
    if ULT in cols:
        tmp['_ult'] = df_in[ULT]; spec['_ult'] = 'sum'

    dl_weights = ([df_in[DLT]] if DLT in cols else []) + [tot]
    ul_weights = ([df_in[ULT]] if ULT in cols else []) + [tot]
    if 'DL_Throughput_Mbps' in cols:
        add_weighted('dl', df_in['DL_Throughput_Mbps'], dl_weights)
    if 'UL_Throughput_Mbps' in cols:
        add_weighted('ul', df_in['UL_Throughput_Mbps'], ul_weights)

    quality_kpis = [k for k in ['Call Setup Success Rate', 'Service Drop (all service)', 'CQI_4G',
                                'Resource Block Untilizing Rate Downlink (%)'] if k in cols]
    for k in quality_kpis:
        add_weighted(f'q::{k}', df_in[k], [tot])

    mean_kpis = [k for k in ['Intra-frequency HO (%)', 'Inter-frequency HO (%)',
                             'Inter-RAT HOSR (LTE to WCDMA) (%)', 'SRVCC Success Rate (LTE to WCDMA)'] if k in cols]
    for k in mean_kpis:
        mean_cols[f'm::{k}'] = df_in[k]; spec[f'm::{k}'] = 'mean'

    volte_kpis = [k for k in ['VoLTE E-RAB Call Setup Success Rate', 'Call Drop Rate (VoLTE)'] if k in cols]
    if VOL in cols:
        tmp['_vol'] = df_in[VOL]; spec['_vol'] = 'sum'
    for k in volte_kpis:
        x = df_in[k]
        if VOL in cols:
            tmp[f'v::{k}__n'] = (x * df_in[VOL]).where(x.notna())
            spec[f'v::{k}__n'] = 'sum'
        mean_cols[f'v::{k}__m'] = x
        spec[f'v::{k}__m'] = 'mean'

    work = pd.concat([df_in[group_cols], pd.DataFrame(tmp), pd.DataFrame(mean_cols)], axis=1)
    agg = work.groupby(group_cols, sort=True).agg(spec)

    def wavg(key, n_weights):
        """Chọn trọng số đầu tiên có tổng > 0; nếu không có thì dùng mean thường."""
        out = agg[f'{key}__m']
        for i in reversed(range(n_weights)):
            d = agg[f'{key}__d{i}']
            out = pd.Series(np.where(d > 0, agg[f'{key}__n{i}'] / d.where(d > 0), out), index=agg.index)
        return out

    res = pd.DataFrame(index=agg.index)
    res[TOT] = agg['_tot']
    if DLT in cols:
        res[DLT] = agg['_dlt']
    if ULT in cols:
        res[ULT] = agg['_ult']
    if 'DL_Throughput_Mbps' in cols:
        res['DL_Throughput_Mbps'] = wavg('dl', len(dl_weights))
    if 'UL_Throughput_Mbps' in cols:
        res['UL_Throughput_Mbps'] = wavg('ul', len(ul_weights))
    for k in quality_kpis:
        res[k] = wavg(f'q::{k}', 1)
    for k in mean_kpis:
        res[k] = agg[f'm::{k}']
    if VOL in cols:
        res[VOL] = agg['_vol']
    for k in volte_kpis:
        if VOL in cols:
            vt = agg['_vol']
            res[k] = pd.Series(np.where(vt > 0, agg[f'v::{k}__n'] / vt.where(vt > 0), agg[f'v::{k}__m']),
                               index=agg.index).fillna(0.0)
        else:
            res[k] = agg[f'v::{k}__m'].fillna(0.0)

    return res.reset_index()


# ---------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("📶 Navigation")

sample_bytes, sample_fname = get_sample_file_bytes()
if sample_bytes:
    st.sidebar.download_button(
        label=f"📥 Tải File Mẫu ({sample_fname})",
        data=sample_bytes,
        file_name=sample_fname,
        mime="text/csv",
    )

st.sidebar.markdown("---")

up_file = st.sidebar.file_uploader("📂 Tải CSV KPI:", type=["csv"])

if up_file is not None:
    st.sidebar.success("✅ Đã tải file!")
    df = process_data(up_file)
elif os.path.exists("4G_Sample - Copy.csv"):
    st.sidebar.info("ℹ️ Đang dùng dữ liệu mẫu 4G_Sample - Copy.csv")
    df = process_data("4G_Sample - Copy.csv")
elif os.path.exists("4G_Sample.csv"):
    st.sidebar.info("ℹ️ Đang dùng dữ liệu mẫu 4G_Sample.csv")
    df = process_data("4G_Sample.csv")
elif os.path.exists("4G.csv"):
    st.sidebar.info("ℹ️ Đang dùng dữ liệu mẫu 4G.csv")
    df = process_data("4G.csv")
else:
    st.info("👋 Vui lòng tải file CSV ở bên trái.")
    st.stop()

# Filters
st.sidebar.subheader("📅 Chọn Ngày")
if "Date" in df.columns:
    all_dates = sorted(df["Date"].dropna().unique().tolist())
    sel_dates = st.sidebar.multiselect(
        "Chọn Ngày",
        options=all_dates,
        default=all_dates,
        label_visibility="collapsed"
    )
else:
    sel_dates = []

st.sidebar.subheader("📡 Chọn Site")
site_col = "Site Name" if "Site Name" in df.columns else None

sel_sites = []
if site_col:
    all_sites = sorted(df[site_col].dropna().unique().tolist())
    sel_sites = st.sidebar.multiselect(
        "Chọn Site",
        options=all_sites,
        default=all_sites,
        label_visibility="collapsed"
    )
    filtered_df = df[(df["Date"].isin(sel_dates)) & (df[site_col].isin(sel_sites))]
else:
    filtered_df = df[df["Date"].isin(sel_dates)] if "Date" in df.columns else df.copy()

if filtered_df.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu!")
    st.stop()

# ---------------------------------------------------------
# 5. HEADER & CARDS
# ---------------------------------------------------------
cell_col = "Tên đối tượng" if "Tên đối tượng" in df.columns else ("Cell Name" if "Cell Name" in df.columns else None)
num_cells = filtered_df[cell_col].nunique() if cell_col and cell_col in filtered_df.columns else 0
num_sites = filtered_df[site_col].nunique() if site_col and site_col in filtered_df.columns else 0

has_hour = filtered_df["_has_hour_col"].iloc[0] if "_has_hour_col" in filtered_df.columns else True

st.title("📡 4G RAN Quality Report")
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


def calc_weighted_avg(df_in, kpi_col, weight_col=None):
    if kpi_col not in df_in.columns:
        return 0.0

    if weight_col is None:
        if kpi_col == "DL_Throughput_Mbps":
            weight_col = "Traffic Volumn DL (GB)" if "Traffic Volumn DL (GB)" in df_in.columns else "Total Data Traffic Volume (GB)"
        elif kpi_col == "UL_Throughput_Mbps":
            weight_col = "Traffic Volume UL (GB)" if "Traffic Volume UL (GB)" in df_in.columns else "Total Data Traffic Volume (GB)"
        else:
            weight_col = "Total Data Traffic Volume (GB)"

    if weight_col in df_in.columns:
        valid_mask = df_in[kpi_col].notnull() & df_in[weight_col].notnull() & (df_in[weight_col] > 0)
        df_valid = df_in[valid_mask]
        total_weight = df_valid[weight_col].sum()
        if total_weight > 0:
            return (df_valid[kpi_col] * df_valid[weight_col]).sum() / total_weight

    df_valid = df_in[df_in[kpi_col].notnull()]
    return df_valid[kpi_col].mean() if not df_valid.empty else 0.0


s_tf = filtered_df.get("Total Data Traffic Volume (GB)", pd.Series([0]))
s_cssr = filtered_df.get("Call Setup Success Rate", pd.Series([0]))
s_cdr = filtered_df.get("Service Drop (all service)", pd.Series([0]))
s_dl = filtered_df.get("DL_Throughput_Mbps", pd.Series([0]))
s_ul = filtered_df.get("UL_Throughput_Mbps", pd.Series([0]))
s_cqi = filtered_df.get("CQI_4G", pd.Series([0]))
s_prb = filtered_df.get("Resource Block Untilizing Rate Downlink (%)", pd.Series([0]))
s_intra = filtered_df.get("Intra-frequency HO (%)", pd.Series([0]))
s_inter = filtered_df.get("Inter-frequency HO (%)", pd.Series([0]))
s_srvcc = filtered_df.get("SRVCC Success Rate (LTE to WCDMA)", pd.Series([0]))

# HÀNG 1 (5 CỘT)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    v = s_tf.sum()
    render_card("Data Traffic", "Total Data Traffic", f"{v:,.0f} GB", "N/A", f"{s_tf.min():.1f}G", f"{s_tf.max():.1f}G", "Tải dữ liệu tổng", "EXCELLENT")
with c2:
    v = calc_weighted_avg(filtered_df, "Call Setup Success Rate")
    render_card("Accessibility", "Call Setup SR", f"{v:.2f}%", ">=99.0%", f"{s_cssr.min():.1f}%", f"{s_cssr.max():.1f}%", "Rất ổn định", "GOOD" if v >= 99.0 else "WARNING")
with c3:
    v = calc_weighted_avg(filtered_df, "Service Drop (all service)")
    render_card("Retainability", "Service Drop Rate", f"{v:.3f}%", "<=1.0%", f"{s_cdr.min():.3f}%", f"{s_cdr.max():.3f}%", "Ổn định chung", "WARNING" if v > 1.0 else "GOOD")
with c4:
    v = calc_weighted_avg(filtered_df, "DL_Throughput_Mbps")
    render_card("Integrity", "User DL Throughput", f"{v:.2f} M", ">20.0M", f"{s_dl.min():.1f}M", f"{s_dl.max():.1f}M", "Tốc độ tải", "EXCELLENT" if v > 20.0 else "GOOD")
with c5:
    v = calc_weighted_avg(filtered_df, "UL_Throughput_Mbps")
    render_card("Integrity", "User UL Throughput", f"{v:.2f} M", ">=1.5M", f"{s_ul.min():.2f}M", f"{s_ul.max():.2f}M", "Tốc độ tải lên", "EXCELLENT" if v >= 1.5 else "GOOD")

# HÀNG 2 (5 CỘT)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    v = calc_weighted_avg(filtered_df, "CQI_4G")
    render_card("Radio Quality", "CQI (CQI >= 7)", f"{v:.2f}%", ">=95.0%", f"{s_cqi.min():.1f}%", f"{s_cqi.max():.1f}%", "Vùng phủ RF", "EXCELLENT" if v >= 95.0 else "WARNING")
with c2:
    v = calc_weighted_avg(filtered_df, "Resource Block Untilizing Rate Downlink (%)")
    render_card("Capacity & Load", "PRB Utilization DL", f"{v:.2f}%", "<=35.0%", f"{s_prb.min():.1f}%", f"{s_prb.max():.1f}%", "Dồi dào dự phòng", "EXCELLENT" if v <= 35.0 else "WARNING")
with c3:
    v = s_intra.mean()
    render_card("Mobility", "Intra-freq HO SR", f"{v:.2f}%", ">=98.0%", f"{s_intra.min():.1f}%", f"{s_intra.max():.1f}%", "Chuyển giao mượt", "WARNING" if v < 98.0 else "GOOD")
with c4:
    v = s_inter.mean()
    render_card("Mobility", "Inter-freq HO SR", f"{v:.2f}%", ">=98.0%", f"{s_inter.min():.1f}%", f"{s_inter.max():.1f}%", "Chuyển giao liên tần", "WARNING" if v < 98.0 else "GOOD")
with c5:
    v = s_srvcc.mean()
    render_card("SRVCC", "SRVCC Success Rate", f"{v:.2f}%", ">=95.0%", f"{s_srvcc.min():.1f}%", f"{s_srvcc.max():.1f}%", "Đảm bảo thoại 3G", "EXCELLENT" if v >= 95.0 else "WARNING")

st.markdown("---")

# ---------------------------------------------------------
# 5.5 THỐNG KÊ FREQBAND
# ---------------------------------------------------------
st.subheader("📊 Thống Kê Phân Bổ Cell & Traffic Theo Freqband")

fb_col1, fb_col2, fb_col3 = st.columns(3)

fb_cell_counts = pd.DataFrame()
fb_tf_df = pd.DataFrame()
cell_type_counts = pd.DataFrame()
fb_type_xtab = pd.DataFrame()

if cell_col and cell_col in filtered_df.columns and "Freqband" in filtered_df.columns:
    _cols = [cell_col, "Freqband"] + (["Cell Type"] if "Cell Type" in filtered_df.columns else [])
    cell_fb_df = filtered_df[_cols].drop_duplicates(subset=[cell_col])

    # --- Số lượng cell theo Freqband
    fb_cell_counts = cell_fb_df["Freqband"].value_counts().reset_index()
    fb_cell_counts.columns = ["Freqband", "Số lượng Cell"]
    fb_cell_counts = fb_cell_counts.sort_values(by="Freqband")

    fig_fb_cell = px.pie(
        fb_cell_counts,
        names="Freqband",
        values="Số lượng Cell",
        title="<b>Số lượng Cell theo Freqband</b>",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_fb_cell.update_traces(textinfo="label+value+percent", textfont_size=12)
    fig_fb_cell.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=40, b=20))

    with fb_col1:
        st.plotly_chart(fig_fb_cell, use_container_width=True)

    # --- Số lượng cell theo loại cell (VNP / MORAN) + bảng chéo Freqband x Loại cell
    if "Cell Type" in cell_fb_df.columns:
        cell_type_counts = cell_fb_df["Cell Type"].value_counts().reset_index()
        cell_type_counts.columns = ["Cell Type", "Số lượng Cell"]
        cell_type_counts = cell_type_counts.sort_values(by="Cell Type", ascending=False)  # VNP trước, MORAN sau

        fb_type_xtab = (
            pd.crosstab(cell_fb_df["Freqband"], cell_fb_df["Cell Type"])
            .reindex(columns=["VNP", "MORAN"], fill_value=0)
        )
        fb_type_xtab["Tổng"] = fb_type_xtab.sum(axis=1)
        fb_type_xtab = fb_type_xtab.sort_index().reset_index()

        fig_ct = px.pie(
            cell_type_counts,
            names="Cell Type",
            values="Số lượng Cell",
            title="<b>Số lượng Cell theo Loại Cell (VNP / MORAN)</b>",
            hole=0.4,
            color="Cell Type",
            color_discrete_map={"VNP": "#3b82f6", "MORAN": "#f59e0b"}
        )
        fig_ct.update_traces(textinfo="label+value+percent", textfont_size=12)
        fig_ct.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=40, b=20))
        with fb_col2:
            st.plotly_chart(fig_ct, use_container_width=True)

    # --- Traffic theo Freqband
    if "Total Data Traffic Volume (GB)" in filtered_df.columns:
        fb_tf_df = filtered_df.groupby("Freqband")["Total Data Traffic Volume (GB)"].sum().reset_index()
        fb_tf_df = fb_tf_df.sort_values(by="Freqband")

        fig_fb_tf = px.bar(
            fb_tf_df,
            x="Freqband",
            y="Total Data Traffic Volume (GB)",
            text="Total Data Traffic Volume (GB)",
            title="<b>Tổng Traffic Volume (GB) theo Freqband</b>",
            color="Freqband",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_fb_tf.update_traces(texttemplate='%{text:,.1f} GB', textposition='outside')
        fig_fb_tf.update_layout(
            template="plotly_dark",
            height=320,
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="Traffic Volume (GB)",
            xaxis_title="Freqband"
        )

        with fb_col3:
            st.plotly_chart(fig_fb_tf, use_container_width=True)

    if not fb_type_xtab.empty:
        st.markdown("**Bảng thống kê số lượng Cell theo Freqband và Loại Cell:**")
        _xt = fb_type_xtab.copy()
        _total = {"Freqband": "Tổng", **{c: int(_xt[c].sum()) for c in ["VNP", "MORAN", "Tổng"]}}
        st.dataframe(pd.concat([_xt, pd.DataFrame([_total])], ignore_index=True), use_container_width=True, hide_index=True)

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
    "Inter-Freq HO SR (%)": "Inter-frequency HO (%)",
    "Inter-RAT HOSR (%)": "Inter-RAT HOSR (LTE to WCDMA) (%)",
    "VoLTE Traffic (Erl)": "VoLTE Traffic (Erl)",
    "VoLTE Drop Rate (%)": "Call Drop Rate (VoLTE)",
}

avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}

if avail_kpis:
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        time_mode = st.radio("⏱ Thời gian:", ["Chỉ theo giờ (24h Avg)", "Theo Ngày & Giờ (Timeline)"], horizontal=True)

    with ctrl_col2:
        sel_kpi_lbl = st.selectbox("🎯 Chọn KPI kết hợp Traffic:", options=list(avail_kpis.keys()))

    sel_kpi_col = avail_kpis[sel_kpi_lbl]

    if time_mode == "Chỉ theo giờ (24h Avg)":
        if has_hour and "Hour" in filtered_df.columns:
            c_data = aggregate_kpis(filtered_df, ["Hour"])
            x_axis = c_data["Hour"]
            x_title = "Giờ trong ngày (0h - 23h)"
        else:
            c_data = aggregate_kpis(filtered_df, ["Date"])
            x_axis = pd.to_datetime(c_data["Date"]).dt.strftime("%d/%m")
            x_title = "Ngày"
    else:
        group_cols = [col for col in ["Date", "Hour", "DateTime"] if col in filtered_df.columns]
        if not has_hour and "Hour" in group_cols:
            group_cols.remove("Hour")
        if group_cols:
            c_data = aggregate_kpis(filtered_df, group_cols)
            if "DateTime" in c_data.columns:
                c_data = c_data.sort_values(by="DateTime")
                fmt_str = "%d/%m %H:00" if has_hour else "%d/%m"
                c_data["TimeLabel"] = pd.to_datetime(c_data["DateTime"]).dt.strftime(fmt_str)
            elif "Date" in c_data.columns:
                c_data["TimeLabel"] = pd.to_datetime(c_data["Date"]).dt.strftime("%d/%m")
            else:
                c_data["TimeLabel"] = c_data["Hour"].astype(str) + ":00"
        else:
            c_data = aggregate_kpis(filtered_df, ["Date"])
            c_data["TimeLabel"] = "Timeline"

        x_axis = c_data["TimeLabel"]
        x_title = "Thời Gian (Ngày/Giờ)" if has_hour else "Thời Gian (Ngày)"

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if "Total Data Traffic Volume (GB)" in c_data.columns:
        fig.add_trace(go.Bar(x=x_axis, y=c_data["Total Data Traffic Volume (GB)"], name="Traffic (GB)", marker_color="rgba(53, 162, 235, 0.5)"), secondary_y=False)
    if sel_kpi_col in c_data.columns:
        fig.add_trace(go.Scatter(x=x_axis, y=c_data[sel_kpi_col], name=sel_kpi_lbl, mode="lines+markers", line=dict(color="#ff4d4f", width=2.5)), secondary_y=True)

    fig.update_layout(title_text=f"📊 Biểu đồ Traffic và {sel_kpi_lbl}", template="plotly_dark", hovermode="x unified", height=420, margin=dict(l=10, r=10, t=40, b=10))
    fig.update_xaxes(title_text=x_title, type="category")
    fig.update_yaxes(title_text="Traffic (GB)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text=sel_kpi_lbl, secondary_y=True, showgrid=True, gridcolor="rgba(255,255,255,0.1)")

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 7. TOP HIGH TRAFFIC SITES AND CELLS
# ---------------------------------------------------------
st.subheader("🔥 Top N Site & Top N Cell Có Lưu Lượng (Traffic) Cao Nhất")

tr_col1, tr_col2 = st.columns([2, 1])
with tr_col1:
    st.markdown("Lọc danh sách Top Site và Top Cell có tổng lưu lượng dữ liệu lớn nhất trong khoảng thời gian đã chọn.")
with tr_col2:
    top_n_traffic = st.number_input("🔢 Nhập số lượng Top N Traffic cần xem:", min_value=1, max_value=200, value=10, step=1)

top_cell_df = pd.DataFrame()
top_site_df = pd.DataFrame()
cell_agg_all = None

if "Total Data Traffic Volume (GB)" in filtered_df.columns:
    tab_cell, tab_site = st.tabs(["📱 Top Cell Traffic", "🏢 Top Site Traffic"])

    grp_cols = [c for c in [site_col, cell_col] if c is not None and c in filtered_df.columns]
    if grp_cols:
        # Tính MỘT lần, dùng lại cho cả Top Cell Traffic lẫn Worst Cells bên dưới
        cell_agg_all = aggregate_kpis(filtered_df, grp_cols)
        top_cell_df = cell_agg_all.nlargest(int(top_n_traffic), "Total Data Traffic Volume (GB)")

        with tab_cell:
            st.markdown(f"**Top {top_n_traffic} Cell có lưu lượng cao nhất:**")
            st.dataframe(top_cell_df, use_container_width=True)

    if site_col and site_col in filtered_df.columns:
        top_site_df = aggregate_kpis(filtered_df, [site_col]).nlargest(int(top_n_traffic), "Total Data Traffic Volume (GB)")
        with tab_site:
            st.markdown(f"**Top {top_n_traffic} Site có lưu lượng cao nhất:**")
            st.dataframe(top_site_df, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 8. WORST CELLS MATRIX FOR ALL KPIS & PDF REPORT EXPORT
# ---------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst N Cells Theo Chỉ Số KPI")

if cell_col and cell_col in filtered_df.columns:
    kpi_options_dict = {
        "CSSR Thấp (Call Setup Success Rate)": ("Call Setup Success Rate", True),
        "DCR / Drop Rate Cao (Service Drop)": ("Service Drop (all service)", False),
        "Intra-Freq HO SR Thấp (Chuyển giao nội băng)": ("Intra-frequency HO (%)", True),
        "Inter-RAT HOSR Thấp (Chuyển giao 4G-3G)": ("Inter-RAT HOSR (LTE to WCDMA) (%)", True),
        "Inter-Freq HO SR Thấp (Chuyển giao liên tần)": ("Inter-frequency HO (%)", True),
        "DL Throughput Thấp (Tốc độ Tải xuống)": ("DL_Throughput_Mbps", True),
        "UL Throughput Thấp (Tốc độ Tải lên)": ("UL_Throughput_Mbps", True),
        "CQI Index Thấp (Chất lượng Vùng phủ RF)": ("CQI_4G", True),
        "PRB Utilization Cao (Nghẽn Tài nguyên DL)": ("Resource Block Untilizing Rate Downlink (%)", False),
        "VoLTE Drop Rate Cao (Tỷ lệ rớt cuộc gọi VoLTE)": ("Call Drop Rate (VoLTE)", False),
    }

    available_kpi_options = {lbl: (col, is_asc) for lbl, (col, is_asc) in kpi_options_dict.items() if col in filtered_df.columns}

    if available_kpi_options:
        kpi_col1, kpi_col2 = st.columns([2, 1])
        with kpi_col1:
            sel_worst_kpi_lbl = st.selectbox(
                "🎯 Chọn KPI cần xem trên giao diện:",
                options=list(available_kpi_options.keys())
            )
        with kpi_col2:
            top_n_worst = st.number_input("🔢 Nhập số lượng Worst Cells (N):", min_value=1, max_value=200, value=10, step=1)

        target_col, sort_ascending = available_kpi_options[sel_worst_kpi_lbl]

        grp_worst_cols = [c for c in [site_col, cell_col] if c is not None and c in filtered_df.columns]
        if grp_worst_cols:
            cell_agg = cell_agg_all if cell_agg_all is not None else aggregate_kpis(filtered_df, grp_worst_cols)

            if target_col in cell_agg.columns:
                _n = int(top_n_worst)
                res_df = cell_agg.nsmallest(_n, target_col) if sort_ascending else cell_agg.nlargest(_n, target_col)
            else:
                res_df = cell_agg.head(int(top_n_worst))

            st.markdown(f"**Danh sách Top {top_n_worst} Worst Cells theo `{sel_worst_kpi_lbl}`:**")
            st.dataframe(res_df, use_container_width=True)

            st.markdown("---")
            st.markdown("### 📄 PDF Report Export")
            st.caption("PDF (kèm biểu đồ) chỉ được dựng khi bấm nút, để không làm chậm mỗi lần đổi bộ lọc / Top N.")

            _pdf_sig = (len(filtered_df), round(float(s_tf.sum()), 3), tuple(map(str, sel_dates)), len(sel_sites))

            if st.button("📑 Tạo Báo Cáo PDF"):
                with st.spinner("Đang tạo PDF..."):
                    _top = lambda col, asc: (cell_agg.nsmallest(10, col) if asc else cell_agg.nlargest(10, col)) if col in cell_agg.columns else pd.DataFrame()
                    worst10_cssr = _top("Call Setup Success Rate", True)
                    worst10_dcr = _top("Service Drop (all service)", False)
                    worst10_intra_ho = _top("Intra-frequency HO (%)", True)
                    worst10_inter_ho = _top("Inter-frequency HO (%)", True)

                    top10_sites_pdf = top_site_df.head(10) if not top_site_df.empty else pd.DataFrame()
                    top10_cells_pdf = top_cell_df.head(10) if not top_cell_df.empty else pd.DataFrame()

                    summary_data = {
                        "tf": s_tf.sum(),
                        "cssr": calc_weighted_avg(filtered_df, "Call Setup Success Rate"),
                        "drop": calc_weighted_avg(filtered_df, "Service Drop (all service)"),
                        "dl": calc_weighted_avg(filtered_df, "DL_Throughput_Mbps"),
                        "ul": calc_weighted_avg(filtered_df, "UL_Throughput_Mbps"),
                        "cqi": calc_weighted_avg(filtered_df, "CQI_4G"),
                        "prb": calc_weighted_avg(filtered_df, "Resource Block Untilizing Rate Downlink (%)"),
                        "intra": s_intra.mean(),
                        "inter": s_inter.mean(),
                        "srvcc": s_srvcc.mean(),
                    }

                    timeline_grp = [c for c in ["Date", "Hour", "DateTime"] if c in filtered_df.columns]
                    if not has_hour and "Hour" in timeline_grp:
                        timeline_grp.remove("Hour")
                    if timeline_grp:
                        c_data_timeline = aggregate_kpis(filtered_df, timeline_grp)

                        if "DateTime" in c_data_timeline.columns:
                            c_data_timeline = c_data_timeline.sort_values(by="DateTime")
                            fmt_str = "%d/%m %H:00" if has_hour else "%d/%m"
                            c_data_timeline["TimeLabel"] = pd.to_datetime(c_data_timeline["DateTime"]).dt.strftime(fmt_str)
                        elif "Date" in c_data_timeline.columns:
                            c_data_timeline["TimeLabel"] = pd.to_datetime(c_data_timeline["Date"]).dt.strftime("%d/%m")
                        elif "Hour" in c_data_timeline.columns:
                            c_data_timeline["TimeLabel"] = c_data_timeline["Hour"].astype(str) + ":00"
                        else:
                            c_data_timeline["TimeLabel"] = "Timeline"
                    else:
                        c_data_timeline = pd.DataFrame()

                    pdf_buf = generate_pdf_report(
                        summary_data,
                        c_data_timeline,
                        top10_sites_pdf,
                        top10_cells_pdf,
                        worst10_cssr,
                        worst10_dcr,
                        worst10_intra_ho,
                        worst10_inter_ho,
                        fb_cell_counts,
                        fb_tf_df,
                        cell_type_counts,
                        fb_type_xtab
                    )
                    st.session_state["pdf_bytes"] = pdf_buf.getvalue()
                    st.session_state["pdf_sig"] = _pdf_sig

            if st.session_state.get("pdf_bytes") is not None:
                if st.session_state.get("pdf_sig") == _pdf_sig:
                    st.download_button(
                        label="⬇️ Tải Báo Cáo PDF",
                        data=st.session_state["pdf_bytes"],
                        file_name="4G_Network_Health.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.info("Bộ lọc đã thay đổi — bấm 'Tạo Báo Cáo PDF' để tạo lại.")

st.caption("🚀 4G RAN Report — Hourly in 3 or 4 days")

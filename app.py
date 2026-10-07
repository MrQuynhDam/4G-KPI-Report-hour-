import io
import os
import ssl
import urllib.request
import unicodedata
import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
    
    # 1. Đọc file local nằm trong dự án (Khuyên dùng)
    if os.path.exists(local_reg):
        bold_path = local_bold if os.path.exists(local_bold) else local_reg
        return local_reg, bold_path, "DejaVu Sans"

    # 2. Tìm kiếm font hệ thống (Linux / Debian / Ubuntu)
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

# Register standard fallbacks
addMapping("Helvetica", 0, 0, "Helvetica")
addMapping("Helvetica", 1, 0, "Helvetica-Bold")
addMapping("Helvetica", 0, 1, "Helvetica-Oblique")
addMapping("Helvetica", 1, 1, "Helvetica-BoldOblique")

# Matplotlib Unicode Setup
matplotlib.rcParams["font.sans-serif"] = [font_family_name, "DejaVu Sans", "Liberation Sans", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------
# 1. CONFIG & STYLING
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
# 2. FILE MẪU & PDF REPORT ĐẦY ĐỦ CARDS, 6 CHARTS, TOP 10 & WORST 10
# ---------------------------------------------------------
def get_sample_file_bytes():
    """Đọc trực tiếp tệp 4G_Sample.csv có sẵn trên GitHub/thư mục dự án"""
    for fname in ["4G_Sample.csv", "4G.csv"]:
        if os.path.exists(fname):
            with open(fname, "rb") as f:
                return f.read(), fname
    return None, None


def generate_pdf_report(summary, hourly_trend_df, top10_sites, top10_cells, worst10_cssr, worst10_dcr, worst10_intra_ho, worst10_inter_ho):
    """Xuất PDF Chuẩn tiếng Việt - Visual Cards, 6 Charts Xu Hướng (Mỗi chart 1 dòng), Top 10 Site/Cell & Worst 10"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    
    # Base Styles with Registered Unicode Font
    t_style = ParagraphStyle("T", fontName=FONT_NAME, fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    h2_style = ParagraphStyle("H2", fontName=FONT_NAME, fontSize=11, textColor=colors.HexColor("#1e293b"), spaceBefore=8, spaceAfter=4)
    norm_style = ParagraphStyle("N", fontName=FONT_NAME, fontSize=8.5, textColor=colors.HexColor("#334155"))

    now_str = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")

    story.append(Paragraph("BÁO CÁO ĐÁNH GIÁ CHẤT LƯỢNG MẠNG 4G/LTE (EXECUTIVE REPORT)", t_style))
    story.append(Paragraph(f"Thời gian xuất báo cáo: {now_str} | Trung tâm Tối ưu hóa Mạng RAN", norm_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=10))

    # ---------------------------------------------------------
    # MỤC I. 10 VISUAL KPI CARDS
    # ---------------------------------------------------------
    story.append(Paragraph("I. BẢNG CARD KPI TỔNG QUAN (VISUAL KPI CARDS)", h2_style))
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
        create_pdf_card("Accessibility", "Call Setup SR", f"{summary.get('cssr',0):.2f}%", ">=99.50%", "Rất tốt", "#059669" if summary.get('cssr',0)>=99.5 else "#d97706"),
        create_pdf_card("Retainability", "Service Drop Rate", f"{summary.get('drop',0):.3f}%", "<=0.100%", "Ổn định", "#059669" if summary.get('drop',0)<=0.1 else "#dc2626"),
        create_pdf_card("Integrity", "User DL Throughput", f"{summary.get('dl',0):.2f} M", ">=15.0M", "Đạt chuẩn", "#059669" if summary.get('dl',0)>=15 else "#d97706"),
        create_pdf_card("Integrity", "User UL Throughput", f"{summary.get('ul',0):.2f} M", ">=1.5M", "Đạt chuẩn", "#059669" if summary.get('ul',0)>=1.5 else "#d97706"),
    ]

    cards_row2 = [
        create_pdf_card("Radio Quality", "CQI 4G Index", f"{summary.get('cqi',0):.2f}%", ">=92.00%", "Vùng phủ tốt", "#059669" if summary.get('cqi',0)>=92 else "#d97706"),
        create_pdf_card("Capacity & Load", "PRB DL Utilization", f"{summary.get('prb',0):.2f}%", "<=35.00%", "Dồi dào", "#059669" if summary.get('prb',0)<=35 else "#dc2626"),
        create_pdf_card("Mobility", "Intra-freq HO SR", f"{summary.get('intra',0):.2f}%", ">=99.00%", "Mượt mà", "#059669" if summary.get('intra',0)>=99 else "#d97706"),
        create_pdf_card("Mobility", "Inter-RAT HOSR", f"{summary.get('irat',0):.2f}%", ">=95.00%", "Cần theo dõi", "#059669" if summary.get('irat',0)>=95 else "#d97706"),
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
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # MỤC II. 6 CHARTS XU HƯỚNG - MỖI CHART 1 DÒNG ĐỘC LẬP
    # ---------------------------------------------------------
    story.append(Paragraph("II. XU HƯỚNG CÁC CHỈ SỐ KPI THEO KHUNG GIỜ/NGÀY (HOURLY KPI CHARTS)", h2_style))
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
            fig, ax = plt.subplots(figsize=(11, 2.2), dpi=150)

            # Draw Bar
            b_color = '#a855f7' if is_bar_volte else '#3b82f6'
            ax.bar(range(n_pts), bar_vals, color=b_color, alpha=0.45, label=bar_lbl, width=0.8)
            ax.set_ylabel(bar_lbl, color='#1d4ed8' if not is_bar_volte else '#7e22ce', fontweight='bold', fontsize=7.5)
            ax.tick_params(axis='y', labelcolor='#1d4ed8' if not is_bar_volte else '#7e22ce', labelsize=6.5)
            
            # X-ticks formatting
            ax.set_xticks(range(0, n_pts, step))
            ax.set_xticklabels([x_labels[i] for i in range(0, n_pts, step)], rotation=30 if n_pts > 15 else 0, ha='right' if n_pts > 15 else 'center', fontsize=6)
            ax.grid(True, linestyle='--', alpha=0.25)

            if line2_vals is None:
                # Dual axis chart
                ax_t = ax.twinx()
                ax_t.plot(range(n_pts), line1_vals, color=line1_color, marker='o', markersize=2.5, linewidth=1.4, label=line1_lbl)
                ax_t.set_ylabel(line1_lbl, color=line1_color, fontweight='bold', fontsize=7.5)
                ax_t.tick_params(axis='y', labelcolor=line1_color, labelsize=6.5)
            else:
                # Two lines chart (e.g. Intra & Inter HO)
                ax.plot(range(n_pts), line1_vals, color=line1_color, marker='o', markersize=2.5, linewidth=1.4, label=line1_lbl)
                ax.plot(range(n_pts), line2_vals, color=line2_color, marker='s', markersize=2.5, linewidth=1.4, linestyle='--', label=line2_lbl)
                ax.set_ylabel("Handover SR (%)", color='#0f172a', fontweight='bold', fontsize=7.5)
                ax.legend(fontsize=6.5, loc='lower right')

            ax.set_title(chart_title, fontsize=8.5, fontweight='bold', pad=4)
            plt.tight_layout()
            plt.savefig(img_b, format='png', dpi=150)
            plt.close()
            img_b.seek(0)
            return Image(img_b, width=740, height=148)

        # Chart 1: CSSR & Data Traffic
        c1_img = make_single_chart("Chart 1: Tỷ lệ CSSR (%) & Data Traffic (GB)", tf_vals, cssr_vals, "CSSR (%)", "#10b981")
        story.append(c1_img)
        story.append(Spacer(1, 8))

        # Chart 2: DCR & Data Traffic
        c2_img = make_single_chart("Chart 2: Tỷ lệ DCR (%) & Data Traffic (GB)", tf_vals, drop_vals, "DCR (%)", "#ef4444")
        story.append(c2_img)
        story.append(Spacer(1, 8))

        story.append(PageBreak())

        # Chart 3: Download Throughput & Data Traffic
        c3_img = make_single_chart("Chart 3: Download Throughput (Mbps) & Data Traffic (GB)", tf_vals, dl_vals, "DL Thrp (Mbps)", "#8b5cf6")
        story.append(c3_img)
        story.append(Spacer(1, 8))

        # Chart 4: Intra HO & Inter HO
        c4_img = make_single_chart("Chart 4: So sánh Intra-freq HO (%) & Inter-freq HO (%)", tf_vals, intra_vals, "Intra-freq HO (%)", "#059669", line2_vals=inter_vals, line2_lbl="Inter-freq HO (%)", line2_color="#d97706")
        story.append(c4_img)
        story.append(Spacer(1, 8))

        story.append(PageBreak())

        # Chart 5: VoLTE CSSR & VoLTE Traffic
        c5_img = make_single_chart("Chart 5: VoLTE CSSR (%) & VoLTE Traffic (Erl)", volte_tf_vals, volte_cssr_vals, "VoLTE CSSR (%)", "#10b981", bar_lbl="VoLTE Traffic (Erl)", is_bar_volte=True)
        story.append(c5_img)
        story.append(Spacer(1, 8))

        # Chart 6: VoLTE DCR & VoLTE Traffic
        c6_img = make_single_chart("Chart 6: VoLTE DCR (%) & VoLTE Traffic (Erl)", volte_tf_vals, volte_drop_vals, "VoLTE DCR (%)", "#dc2626", bar_lbl="VoLTE Traffic (Erl)", is_bar_volte=True)
        story.append(c6_img)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ---------------------------------------------------------
    # MỤC III. DANH SÁCH TOP 10 HIGH TRAFFIC SITE & CELL
    # ---------------------------------------------------------
    story.append(Paragraph("III. DANH SÁCH TOP 10 HIGH TRAFFIC SITE & CELL", h2_style))
    story.append(Spacer(1, 4))

    def p_cell(text, is_bold=False, align='left', color_hex='#0f172a'):
        p_st = ParagraphStyle('PC', fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor(color_hex), leading=9, alignment=0 if align=='left' else 1)
        txt = f"<b>{text}</b>" if is_bold else str(text)
        return Paragraph(txt, p_st)

    if not top10_cells.empty:
        story.append(Paragraph("<b>1. Top 10 Cell có Lưu lượng Traffic Volume (GB) cao nhất:</b>", norm_style))
        story.append(Spacer(1, 2))
        tr_cols = [c for c in top10_cells.columns if c in ["Site Name", "Tên đối tượng", "Total Data Traffic Volume (GB)", "DL_Throughput_Mbps", "Resource Block Untilizing Rate Downlink (%)"]][:5]
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
                p_cell(row.iloc[0]),
                p_cell(row.iloc[1]),
                p_cell(f"{row.iloc[2]:,.2f}"),
                p_cell(f"{row.iloc[3]:.2f}"),
                p_cell(f"{row.iloc[4]:.2f}")
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
                p_cell(row.iloc[0]),
                p_cell(f"{row.iloc[1]:,.2f}"),
                p_cell(f"{row.iloc[2]:.2f}"),
                p_cell(f"{row.iloc[3]:.2f}")
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

    # ---------------------------------------------------------
    # MỤC IV. WORST 10 CHO CÁC KPI: CSSR, DCR VÀ HANDOVER
    # ---------------------------------------------------------
    story.append(Paragraph("IV. DANH SÁCH WORST 10 CELLS CHO CÁC KPI CHÍNH (CSSR, DCR, HANDOVER)", h2_style))
    story.append(Spacer(1, 4))

    # A. Worst 10 CSSR
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
                p_cell(row.get("Tên đối tượng", "")),
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

    # B. Worst 10 DCR / Drop Rate
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
                p_cell(row.get("Tên đối tượng", "")),
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

    # C. Worst 10 Intra-frequency Handover
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
                p_cell(row.get("Tên đối tượng", "")),
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

    # D. Worst 10 Inter-frequency Handover
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
                p_cell(row.get("Tên đối tượng", "")),
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
    c_data = filtered_df.groupby("Hour").agg({
        "Total Data Traffic Volume (GB)": "sum",
        sel_kpi_col: agg_func,
        "DL_Throughput_Mbps": "mean",
        "UL_Throughput_Mbps": "mean",
        "Service Drop (all service)": "mean",
        "Call Setup Success Rate": "mean",
        "Intra-frequency HO (%)": "mean",
        "Inter-frequency HO (%)": "mean",
        "Resource Block Untilizing Rate Downlink (%)": "mean",
        "VoLTE E-RAB Call Setup Success Rate": "mean",
        "Call Drop Rate (VoLTE)": "mean",
        "VoLTE Traffic (Erl)": "sum"
    }).reset_index()
    x_axis = c_data["Hour"]
    x_title = "Giờ trong ngày (0h - 23h)"
else:
    c_data = filtered_df.groupby(["Date", "Hour", "DateTime"]).agg({
        "Total Data Traffic Volume (GB)": "sum",
        sel_kpi_col: agg_func,
        "DL_Throughput_Mbps": "mean",
        "UL_Throughput_Mbps": "mean",
        "Service Drop (all service)": "mean",
        "Call Setup Success Rate": "mean",
        "Intra-frequency HO (%)": "mean",
        "Inter-frequency HO (%)": "mean",
        "Resource Block Untilizing Rate Downlink (%)": "mean",
        "VoLTE E-RAB Call Setup Success Rate": "mean",
        "Call Drop Rate (VoLTE)": "mean",
        "VoLTE Traffic (Erl)": "sum"
    }).reset_index().sort_values(by="DateTime")
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

if "Total Data Traffic Volume (GB)" in filtered_df.columns:
    tab_cell, tab_site = st.tabs(["📱 Top Cell Traffic", "🏢 Top Site Traffic"])

    grp_cols = [site_col, cell_col] if site_col and cell_col else ([cell_col] if cell_col else [site_col])
    top_cell_df = (
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

    with tab_cell:
        st.markdown(f"**Top {top_n_traffic} Cell có lưu lượng cao nhất:**")
        st.dataframe(top_cell_df, use_container_width=True)

    if site_col:
        top_site_df = (
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
        with tab_site:
            st.markdown(f"**Top {top_n_traffic} Site có lưu lượng cao nhất:**")
            st.dataframe(top_site_df, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 8. WORST CELLS MATRIX FOR ALL KPIS & PDF REPORT EXPORT
# ---------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst N Cells Theo Chỉ Số KPI")

if cell_col:
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

    available_kpi_options = {}
    for lbl, (col, is_asc) in kpi_options_dict.items():
        if col in filtered_df.columns:
            available_kpi_options[lbl] = (col, is_asc)

    kpi_col1, kpi_col2 = st.columns([2, 1])
    with kpi_col1:
        sel_worst_kpi_lbl = st.selectbox(
            "🎯 Chọn KPI cần xem trên giao diện:",
            options=list(available_kpi_options.keys())
        )
    with kpi_col2:
        top_n_worst = st.number_input("🔢 Nhập số lượng Worst Cells (N):", min_value=1, max_value=200, value=10, step=1)

    target_col, sort_ascending = available_kpi_options[sel_worst_kpi_lbl]

    agg_dict = {
        col: ("sum" if col == "Total Data Traffic Volume (GB)" else "mean") 
        for col in [
            "Call Setup Success Rate", "Service Drop (all service)",
            "Intra-frequency HO (%)", "Inter-RAT HOSR (LTE to WCDMA) (%)", "Inter-frequency HO (%)",
            "DL_Throughput_Mbps", "UL_Throughput_Mbps", "CQI_4G",
            "Resource Block Untilizing Rate Downlink (%)", "Call Drop Rate (VoLTE)",
            "Total Data Traffic Volume (GB)"
        ] if col in filtered_df.columns
    }
    cell_agg = filtered_df.groupby([site_col, cell_col]).agg(agg_dict).reset_index()

    res_df = cell_agg.sort_values(by=target_col, ascending=sort_ascending).head(int(top_n_worst))

    st.markdown(f"**Danh sách Top {top_n_worst} Worst Cells theo `{sel_worst_kpi_lbl}`:**")
    st.dataframe(res_df, use_container_width=True)

    worst10_cssr = cell_agg.sort_values(by="Call Setup Success Rate", ascending=True).head(10) if "Call Setup Success Rate" in cell_agg.columns else pd.DataFrame()
    worst10_dcr = cell_agg.sort_values(by="Service Drop (all service)", ascending=False).head(10) if "Service Drop (all service)" in cell_agg.columns else pd.DataFrame()
    worst10_intra_ho = cell_agg.sort_values(by="Intra-frequency HO (%)", ascending=True).head(10) if "Intra-frequency HO (%)" in cell_agg.columns else pd.DataFrame()
    worst10_inter_ho = cell_agg.sort_values(by="Inter-frequency HO (%)", ascending=True).head(10) if "Inter-frequency HO (%)" in cell_agg.columns else pd.DataFrame()

    top10_sites_pdf = top_site_df.head(10) if not top_site_df.empty else pd.DataFrame()
    top10_cells_pdf = top_cell_df.head(10) if not top_cell_df.empty else pd.DataFrame()

    st.markdown("---")
    st.markdown("### 📄 Báo Cáo Cấp Trên (Executive PDF Export)")
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

    # Luôn tạo c_data_timeline đầy đủ Ngày & Giờ cho Báo cáo PDF
    c_data_timeline = filtered_df.groupby(["Date", "Hour", "DateTime"]).agg({
        "Total Data Traffic Volume (GB)": "sum",
        "DL_Throughput_Mbps": "mean",
        "UL_Throughput_Mbps": "mean",
        "Service Drop (all service)": "mean",
        "Call Setup Success Rate": "mean",
        "Intra-frequency HO (%)": "mean",
        "Inter-frequency HO (%)": "mean",
        "Resource Block Untilizing Rate Downlink (%)": "mean",
        "VoLTE E-RAB Call Setup Success Rate": "mean",
        "Call Drop Rate (VoLTE)": "mean",
        "VoLTE Traffic (Erl)": "sum"
    }).reset_index().sort_values(by="DateTime")
    c_data_timeline["TimeLabel"] = c_data_timeline["DateTime"].dt.strftime("%d/%m %H:00")

    pdf_buf = generate_pdf_report(
        summary_data,
        c_data_timeline,
        top10_sites_pdf,
        top10_cells_pdf,
        worst10_cssr,
        worst10_dcr,
        worst10_intra_ho,
        worst10_inter_ho
    )

    st.download_button(
        label="📑 Tải Báo Cáo PDF Chuẩn Font Tiếng Việt (Visual Cards, 6 Charts, Top 10 Traffic & Worst 10 CSSR/DCR/HO)",
        data=pdf_buf,
        file_name="Bao_Cao_Toi_Uu_Mang_4G_Executive.pdf",
        mime="application/pdf",
    )

st.caption("🚀 Universal 4G RAN Dashboard — Streamlit & ReportLab")

import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & ANTI-OVERFLOW CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="4G/LTE RAN Dashboard",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """

""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 2. DATA PROCESSING (TỰ ĐỘNG CHUẨN HÓA KPI)
# -----------------------------------------------------------------------------
@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input)

    time_cols = ["Thời gian", "Time", "DateTime", "Date_Time", "timestamp"]
    time_col = next((c for c in time_cols if c in df.columns), None)

    if time_col:
        df["DateTime"] = pd.to_datetime(
            df[time_col], dayfirst=True, errors="coerce"
        )
        df["Date"] = df["DateTime"].dt.date
    else:
        st.error("❌ Không tìm thấy cột Thời gian!")
        st.stop()

    hour_cols = ["Giờ", "Hour", "hour"]
    hour_col = next((c for c in hour_cols if c in df.columns), None)
    if hour_col:
        df["Hour"] = (
            pd.to_numeric(df[hour_col], errors="coerce").fillna(0).astype(int)
        )
    else:
        df["Hour"] = df["DateTime"].dt.hour

    numeric_cols = [
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
        "Call Drop Rate (VoLTE)",
        "VoLTE E-RAB Call Setup Success Rate",
        "VoLTE Traffic (Erl)",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "User Downlink Average Throughput (Kbps)" in df.columns:
        df["DL_Throughput_Mbps"] = (
            df["User Downlink Average Throughput (Kbps)"] / 1000.0
        )
    if "User Uplink Average Throughput (Kbps)" in df.columns:
        df["UL_Throughput_Mbps"] = (
            df["User Uplink Average Throughput (Kbps)"] / 1000.0
        )

    return df


# -----------------------------------------------------------------------------
# 3. SIDEBAR & FILE INPUT
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/antenna.png", width=60)
st.sidebar.title("📶 Management")

uploaded_file = st.sidebar.file_uploader(
    "📂 Tải file CSV KPI (4G/LTE):", type=["csv"]
)

if uploaded_file is not None:
    st.sidebar.success("✅ Đã tải file thành công!")
    df = process_data(uploaded_file)
elif os.path.exists("4G.csv"):
    st.sidebar.info("ℹ️ Đang dùng dữ liệu mẫu (4G.csv)")
    df = process_data("4G.csv")
else:
    st.info("👋 Vui lòng tải file CSV KPI 4G ở thanh bên trái để bắt đầu.")
    st.stop()

# Filters
st.sidebar.subheader("🎯 Bộ lọc Dữ liệu")
all_dates = sorted(df["Date"].dropna().unique())
selected_dates = st.sidebar.multiselect(
    "📅 Chọn Ngày", options=all_dates, default=all_dates
)

site_col = "Site Name" if "Site Name" in df.columns else None
if site_col:
    all_sites = sorted(df[site_col].dropna().unique())
    selected_sites = st.sidebar.multiselect(
        "📡 Chọn Site", options=all_sites, default=all_sites
    )
    filtered_df = df[
        (df["Date"].isin(selected_dates)) & (df[site_col].isin(selected_sites))
    ]
else:
    filtered_df = df[df["Date"].isin(selected_dates)]

if filtered_df.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu khớp!")
    st.stop()

# -----------------------------------------------------------------------------
# 4. HEADER & FULL KPI CARDS (BỔ SUNG ĐẦY ĐỦ CARDS)
# -----------------------------------------------------------------------------
cell_col = "Tên đối tượng" if "Tên đối tượng" in df.columns else None
num_cells = filtered_df[cell_col].nunique() if cell_col else 0
num_sites = filtered_df[site_col].nunique() if site_col else 0

st.title("📡 4G/LTE RAN Optimization Dashboard")
st.markdown(
    f"**Records:** `{len(filtered_df):,}` | "
    f"**Sites:** `{num_sites}` | "
    f"**Cells:** `{num_cells}`"
)

# Hàng 1: Lưu lượng & Tốc độ & Chất lượng kênh
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
tot_tf = filtered_df.get("Total Data Traffic Volume (GB)", pd.Series([0])).sum()
dl_thrp = filtered_df.get("DL_Throughput_Mbps", pd.Series([0])).mean()
ul_thrp = filtered_df.get("UL_Throughput_Mbps", pd.Series([0])).mean()
cqi = filtered_df.get("CQI_4G", pd.Series([0])).mean()
prb = filtered_df.get("Resource Block Untilizing Rate Downlink (%)", pd.Series([0])).mean()

r1_c1.metric("📊 Total Traffic", f"{tot_tf:,.1f} GB")
r1_c2.metric("🚀 DL Throughput", f"{dl_thrp:.2f} Mbps")
r1_c3.metric("📤 UL Throughput", f"{ul_thrp:.2f} Mbps")
r1_c4.metric("📶 CQI 4G Index", f"{cqi:.2f}%")
r1_c5.metric("🔥 PRB DL Util", f"{prb:.2f}%")

# Hàng 2: Thiết lập, Rớt mạng, Handover & VoLTE
r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
cssr = filtered_df.get("Call Setup Success Rate", pd.Series([0])).mean()
drop = filtered_df.get("Service Drop (all service)", pd.Series([0])).mean()
intra_ho = filtered_df.get("Intra-frequency HO (%)", pd.Series([0])).mean()
v_traffic = filtered_df.get("VoLTE Traffic (Erl)", pd.Series([0])).sum()
v_drop = filtered_df.get("Call Drop Rate (VoLTE)", pd.Series([0])).mean()

r2_c1.metric("📞 Call Setup SR", f"{cssr:.2f}%")
r2_c2.metric("🔴 Service Drop", f"{drop:.3f}%")
r2_c3.metric("🔄 Intra-Freq HO", f"{intra_ho:.2f}%")
r2_c4.metric("📱 VoLTE Traffic", f"{v_traffic:,.1f} Erl")
r2_c5.metric("❌ VoLTE Drop", f"{v_drop:.3f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. UNIFIED DUAL-AXIS CHART (ĐẦY ĐỦ KPI)
# -----------------------------------------------------------------------------
st.subheader("📈 Biểu Đồ Tương Quan Xu Hướng (Unified KPI Trend)")

# Danh sách toàn bộ KPI
kpi_dict = {
    "Downlink Throughput (Mbps)": "DL_Throughput_Mbps",
    "Uplink Throughput (Mbps)": "UL_Throughput_Mbps",
    "CQI 4G Index (%)": "CQI_4G",
    "PRB DL Utilization (%)": "Resource Block Untilizing Rate Downlink (%)",
    "Service Drop Rate (%)": "Service Drop (all service)",
    "Call Setup Success Rate (%)": "Call Setup Success Rate",
    "Intra-Frequency HO SR (%)": "Intra-frequency HO (%)",
    "Inter-Frequency HO SR (%)": "Inter-frequency HO (%)",
    "VoLTE Traffic (Erl)": "VoLTE Traffic (Erl)",
    "VoLTE Call Drop Rate (%)": "Call Drop Rate (VoLTE)",
    "VoLTE Setup SR (%)": "VoLTE E-RAB Call Setup Success Rate",
}

avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}

c1, c2 = st.columns([1, 1])
with c1:
    time_mode = st.radio(
        "⏱ Chế độ xem Thời gian:",
        ["Chỉ theo giờ (24h Avg)", "Theo Ngày & Giờ (Timeline)"],
        horizontal=True,
    )

with c2:
    sel_kpi_label = st.selectbox(
        "🎯 Chọn KPI kết hợp Traffic:", options=list(avail_kpis.keys())
    )

sel_kpi_col = avail_kpis[sel_kpi_label]

# Định nghĩa cách gom nhóm cho từng KPI (Traffic/Erlang tính Sum, còn lại tính Mean)
agg_func = "sum" if "Traffic" in sel_kpi_label or "Erl" in sel_kpi_label else "mean"

if time_mode == "Chỉ theo giờ (24h Avg)":
    c_data = (
        filtered_df.groupby("Hour")
        .agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: agg_func})
        .reset_index()
    )
    x_axis = c_data["Hour"]
    x_title = "Giờ trong ngày (0h - 23h)"
else:
    c_data = (
        filtered_df.groupby(["Date", "Hour", "DateTime"])
        .agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: agg_func})
        .reset_index()
        .sort_values(by="DateTime")
    )
    c_data["TimeLabel"] = c_data["DateTime"].dt.strftime("%d/%m %H:00")
    x_axis = c_data["TimeLabel"]
    x_title = "Thời Gian (Ngày/Giờ)"

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Column Traffic Volume (GB)
fig.add_trace(
    go.Bar(
        x=x_axis,
        y=c_data["Total Data Traffic Volume (GB)"],
        name="Traffic (GB)",
        marker_color="rgba(53, 162, 235, 0.5)",
    ),
    secondary_y=False,
)

# Line KPI Selected
fig.add_trace(
    go.Scatter(
        x=x_axis,
        y=c_data[sel_kpi_col],
        name=sel_kpi_label,
        mode="lines+markers",
        line=dict(color="#ff4d4f", width=2.5),
    ),
    secondary_y=True,
)

fig.update_layout(
    title_text=f"📊 Sự tương quan giữa Traffic (GB) và {sel_kpi_label}",
    template="plotly_dark",
    hovermode="x unified",
    height=480,
    margin=dict(l=10, r=10, t=50, b=10),
)

fig.update_xaxes(
    title_text=x_title,
    type="category" if time_mode != "Chỉ theo giờ (24h Avg)" else None,
)
fig.update_yaxes(title_text="Traffic Volume (GB)", secondary_y=False, showgrid=False)
fig.update_yaxes(
    title_text=sel_kpi_label,
    secondary_y=True,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.1)",
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. WORST CELLS MATRIX (BỔ SUNG ĐẦY ĐỦ CÁC OPTION BAD CELL)
# -----------------------------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst Cells Theo KPI")

if cell_col:
    kpi_opt = st.selectbox(
        "🎯 Lọc Worst Cells theo KPI:",
        [
            "Service Drop Rate (CDR)",
            "Low Downlink Throughput",
            "Low Uplink Throughput",
            "Low CQI (Poor RF Coverage)",
            "High PRB Congestion",
            "Low Intra-Frequency HO SR",
            "VoLTE Call Drop Rate",
        ],
    )

    top_n = st.slider("Số lượng hiển thị:", 5, 30, 10)

    cell_agg = (
        filtered_df.groupby([site_col, cell_col])
        .agg(
            {
                col: "mean"
                for col in [
                    "Service Drop (all service)",
                    "DL_Throughput_Mbps",
                    "UL_Throughput_Mbps",
                    "CQI_4G",
                    "Resource Block Untilizing Rate Downlink (%)",
                    "Intra-frequency HO (%)",
                    "Call Drop Rate (VoLTE)",
                    "Total Data Traffic Volume (GB)",
                ]
                if col in filtered_df.columns
            }
        )
        .reset_index()
    )

    if kpi_opt == "Service Drop Rate (CDR)":
        res_df = cell_agg.sort_values(
            by="Service Drop (all service)", ascending=False
        ).head(top_n)
    elif kpi_opt == "Low Downlink Throughput":
        res_df = cell_agg.sort_values(
            by="DL_Throughput_Mbps", ascending=True
        ).head(top_n)
    elif kpi_opt == "Low Uplink Throughput":
        res_df = cell_agg.sort_values(
            by="UL_Throughput_Mbps", ascending=True
        ).head(top_n)
    elif kpi_opt == "Low CQI (Poor RF Coverage)":
        res_df = cell_agg.sort_values(by="CQI_4G", ascending=True).head(top_n)
    elif kpi_opt == "High PRB Congestion":
        res_df = cell_agg.sort_values(
            by="Resource Block Untilizing Rate Downlink (%)", ascending=False
        ).head(top_n)
    elif kpi_opt == "Low Intra-Frequency HO SR":
        res_df = cell_agg.sort_values(
            by="Intra-frequency HO (%)", ascending=True
        ).head(top_n)
    else:
        res_df = cell_agg.sort_values(
            by="Call Drop Rate (VoLTE)", ascending=False
        ).head(top_n)

    st.dataframe(res_df, use_container_width=True)

st.caption("🚀 Universal 4G/LTE RAN Dashboard — Streamlit & Plotly")

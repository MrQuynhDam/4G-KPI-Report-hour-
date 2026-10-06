import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & ANTI-OVERFLOW CUSTOM STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="4G/LTE RAN Dashboard",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS: Ép tự động ngắt dòng (Word-Wrap) để không bị tràn khung chat/màn hình
st.markdown(
    """

""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 2. DATA PREPROCESSING
# -----------------------------------------------------------------------------
@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input)

    # 1. Nhận diện cột Thời Gian
    time_cols = ["Thời gian", "Time", "DateTime", "Date_Time", "timestamp"]
    time_col = next((c for c in time_cols if c in df.columns), None)

    if time_col:
        df["DateTime"] = pd.to_datetime(
            df[time_col], dayfirst=True, errors="coerce"
        )
        df["Date"] = df["DateTime"].dt.date
    else:
        st.error("❌ Không tìm thấy cột Thời gian trong file CSV!")
        st.stop()

    # 2. Nhận diện cột Giờ (Hour)
    hour_cols = ["Giờ", "Hour", "hour"]
    hour_col = next((c for c in hour_cols if c in df.columns), None)

    if hour_col:
        df["Hour"] = (
            pd.to_numeric(df[hour_col], errors="coerce").fillna(0).astype(int)
        )
    else:
        df["Hour"] = df["DateTime"].dt.hour

    # 3. Ép kiểu số cho KPI
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

    # Đổi sang Mbps
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
# 3. SIDEBAR & UPLOAD
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/antenna.png", width=60)
st.sidebar.title("📶 Management")

uploaded_file = st.sidebar.file_uploader(
    "📂 Tải file CSV KPI (4G/LTE):", type=["csv"]
)

if uploaded_file is not None:
    st.sidebar.success("✅ Đã tải file người dùng!")
    df = process_data(uploaded_file)
elif os.path.exists("4G.csv"):
    st.sidebar.info("ℹ️ Dùng dữ liệu mẫu (4G.csv)")
    df = process_data("4G.csv")
else:
    st.info("👋 Vui lòng tải file CSV KPI 4G ở thanh bên trái để bắt đầu.")
    st.stop()

# Dynamic Filters
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
# 4. HEADER & METRICS
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

col1, col2, col3, col4, col5 = st.columns(5)

tot_tf = (
    filtered_df["Total Data Traffic Volume (GB)"].sum()
    if "Total Data Traffic Volume (GB)" in filtered_df
    else 0
)
dl_thrp = (
    filtered_df["DL_Throughput_Mbps"].mean()
    if "DL_Throughput_Mbps" in filtered_df
    else 0
)
cssr = (
    filtered_df["Call Setup Success Rate"].mean()
    if "Call Setup Success Rate" in filtered_df
    else 0
)
drop = (
    filtered_df["Service Drop (all service)"].mean()
    if "Service Drop (all service)" in filtered_df
    else 0
)
v_drop = (
    filtered_df["Call Drop Rate (VoLTE)"].mean()
    if "Call Drop Rate (VoLTE)" in filtered_df
    else 0
)

col1.metric("📊 Total Traffic", f"{tot_tf:,.1f} GB")
col2.metric("🚀 DL Throughput", f"{dl_thrp:.2f} Mbps")
col3.metric("📞 Call Setup SR", f"{cssr:.2f}%")
col4.metric("🔴 Drop Rate", f"{drop:.3f}%")
col5.metric("📱 VoLTE Drop", f"{v_drop:.3f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. UNIFIED DUAL-AXIS CHART
# -----------------------------------------------------------------------------
st.subheader("📈 Phân Tích Xu Hướng Dữ Liệu (KPI Trend)")

kpi_dict = {
    "Downlink Throughput (Mbps)": "DL_Throughput_Mbps",
    "Uplink Throughput (Mbps)": "UL_Throughput_Mbps",
    "Service Drop Rate (%)": "Service Drop (all service)",
    "Call Setup Success Rate (%)": "Call Setup Success Rate",
    "PRB DL Utilization (%)": "Resource Block Untilizing Rate Downlink (%)",
    "CQI 4G Index": "CQI_4G",
    "Intra-Freq HO SR (%)": "Intra-frequency HO (%)",
    "VoLTE Call Drop Rate (%)": "Call Drop Rate (VoLTE)",
}

avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}

c1, c2 = st.columns([1, 1])
with c1:
    time_mode = st.radio(
        "⏱️️ Chế độ xem Thời gian:",
        ["Chỉ theo giờ (24h Avg)", "Theo Ngày & Giờ (Timeline)"],
        horizontal=True,
    )

with c2:
    sel_kpi_label = st.selectbox(
        "🎯 Chọn KPI kết hợp Traffic:", options=list(avail_kpis.keys())
    )

sel_kpi_col = avail_kpis[sel_kpi_label]

if time_mode == "Chỉ theo giờ (24h Avg)":
    c_data = (
        filtered_df.groupby("Hour")
        .agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: "mean"})
        .reset_index()
    )
    x_axis = c_data["Hour"]
    x_title = "Giờ trong ngày (0h - 23h)"
else:
    c_data = (
        filtered_df.groupby(["Date", "Hour", "DateTime"])
        .agg({"Total Data Traffic Volume (GB)": "sum", sel_kpi_col: "mean"})
        .reset_index()
        .sort_values(by="DateTime")
    )
    c_data["TimeLabel"] = c_data["DateTime"].dt.strftime("%d/%m %H:00")
    x_axis = c_data["TimeLabel"]
    x_title = "Thời Gian (Ngày/Giờ)"

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Column Traffic
fig.add_trace(
    go.Bar(
        x=x_axis,
        y=c_data["Total Data Traffic Volume (GB)"],
        name="Traffic (GB)",
        marker_color="rgba(53, 162, 235, 0.5)",
    ),
    secondary_y=False,
)

# Line KPI
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
    title_text=f"📊 Biểu đồ Tương quan Traffic & {sel_kpi_label}",
    template="plotly_dark",
    hovermode="x unified",
    height=480,
    margin=dict(l=10, r=10, t=50, b=10),
)

fig.update_xaxes(
    title_text=x_title,
    type="category" if time_mode != "Chỉ theo giờ (24h Avg)" else None,
)
fig.update_yaxes(title_text="Traffic (GB)", secondary_y=False, showgrid=False)
fig.update_yaxes(
    title_text=sel_kpi_label,
    secondary_y=True,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.1)",
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. WORST CELLS MATRIX
# -----------------------------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst Cells")

if cell_col:
    kpi_opt = st.selectbox(
        "🎯 Lọc Worst Cells theo KPI:",
        [
            "Service Drop Rate (CDR)",
            "Low Downlink Throughput",
            "High PRB Congestion",
            "VoLTE Call Drop Rate",
            "Low CQI (Poor RF)",
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
                    "Resource Block Untilizing Rate Downlink (%)",
                    "Call Drop Rate (VoLTE)",
                    "CQI_4G",
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
    elif kpi_opt == "High PRB Congestion":
        res_df = cell_agg.sort_values(
            by="Resource Block Untilizing Rate Downlink (%)", ascending=False
        ).head(top_n)
    elif kpi_opt == "VoLTE Call Drop Rate":
        res_df = cell_agg.sort_values(
            by="Call Drop Rate (VoLTE)", ascending=False
        ).head(top_n)
    else:
        res_df = cell_agg.sort_values(by="CQI_4G", ascending=True).head(top_n)

    st.dataframe(res_df, use_container_width=True)

st.caption("🚀 Universal 4G/LTE RAN Dashboard — Streamlit & Plotly")

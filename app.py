import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="4G/LTE RAN Health & Optimization Dashboard",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Telecom Dark Theme
st.markdown("""

""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. DATA LOADING & DYNAMIC PREPROCESSING
# -----------------------------------------------------------------------------
@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input)
    
    # 1. Tự động nhận diện cột Thời Gian
    time_col = None
    for candidate in ['Thời gian', 'Time', 'DateTime', 'Date_Time', 'timestamp']:
        if candidate in df.columns:
            time_col = candidate
            break
            
    if time_col:
        df['DateTime'] = pd.to_datetime(df[time_col], dayfirst=True, errors='coerce')
        df['Date'] = df['DateTime'].dt.date
    else:
        st.error("❌ Không tìm thấy cột Thời gian trong file CSV!")
        st.stop()

    # 2. Tự động nhận diện cột Giờ (Hour)
    hour_col = None
    for candidate in ['Giờ', 'Hour', 'hour']:
        if candidate in df.columns:
            hour_col = candidate
            break
    
    if hour_col:
        df['Hour'] = pd.to_numeric(df[hour_col], errors='coerce').fillna(0).astype(int)
    else:
        df['Hour'] = df['DateTime'].dt.hour

    # 3. Tự động ép kiểu số cho các chỉ số KPI
    numeric_cols = [
        'User Downlink Average Throughput (Kbps)',
        'User Uplink Average Throughput (Kbps)',
        'CQI_4G',
        'Call Setup Success Rate',
        'Service Drop (all service)',
        'Resource Block Untilizing Rate Downlink (%)',
        'Total Data Traffic Volume (GB)',
        'Traffic Volumn DL (GB)',
        'Traffic Volume UL (GB)',
        'Intra-frequency HO (%)',
        'Inter-frequency HO (%)',
        'Call Drop Rate (VoLTE)',
        'VoLTE E-RAB Call Setup Success Rate',
        'VoLTE Traffic (Erl)'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Tính toán thêm tốc độ Mbps
    if 'User Downlink Average Throughput (Kbps)' in df.columns:
        df['DL_Throughput_Mbps'] = df['User Downlink Average Throughput (Kbps)'] / 1000.0
    if 'User Uplink Average Throughput (Kbps)' in df.columns:
        df['UL_Throughput_Mbps'] = df['User Uplink Average Throughput (Kbps)'] / 1000.0

    return df

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS & DYNAMIC UPLOAD
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/antenna.png", width=70)
st.sidebar.title("📶 Dynamic Data Input")

uploaded_file = st.sidebar.file_uploader(
    "📂 Tải lên file CSV Kpis (4G/LTE):", 
    type=['csv'],
    help="Tải file CSV chứa KPI theo giờ của trạm/cell"
)

# Xử lý nguồn dữ liệu
df = None
if uploaded_file is not None:
    st.sidebar.success("✅ Đã tải file người dùng!")
    df = process_data(uploaded_file)
elif os.path.exists("4G.csv"):
    st.sidebar.info("ℹ️ Đang dùng dữ liệu mẫu (4G.csv)")
    df = process_data("4G.csv")
else:
    st.info("👋 **Chào mừng bạn!** Vui lòng **tải lên file CSV KPI 4G** ở thanh bên trái để bắt đầu phân tích.")
    st.stop()

# Dynamic Filters based on Uploaded File
st.sidebar.subheader("🎯 Bộ lọc Dữ liệu (Filters)")

# Filter Date
all_dates = sorted(df['Date'].dropna().unique())
selected_dates = st.sidebar.multiselect("📅 Chọn Ngày", options=all_dates, default=all_dates)

# Filter Site (Tự động nhận diện cột Site Name)
site_col = 'Site Name' if 'Site Name' in df.columns else ('Site' if 'Site' in df.columns else None)
if site_col:
    all_sites = sorted(df[site_col].dropna().unique())
    selected_sites = st.sidebar.multiselect("📡 Chọn Site", options=all_sites, default=all_sites)
    filtered_df = df[(df['Date'].isin(selected_dates)) & (df[site_col].isin(selected_sites))]
else:
    filtered_df = df[df['Date'].isin(selected_dates)]

if filtered_df.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu khớp với bộ lọc!")
    st.stop()

# -----------------------------------------------------------------------------
# 4. HEADER & DASHBOARD METRIC CARDS
# -----------------------------------------------------------------------------
cell_col = 'Tên đối tượng' if 'Tên đối tượng' in df.columns else ('Cell' if 'Cell' in df.columns else None)
num_cells = filtered_df[cell_col].nunique() if cell_col else 0
num_sites = filtered_df[site_col].nunique() if site_col else 0

st.title("📡 4G/LTE Network Health & Optimization Dashboard")
st.markdown(f"**Tổng số bản ghi:** `{len(filtered_df):,}` | **Sites:** `{num_sites}` | **Cells:** `{num_cells}`")

st.markdown("---")

# Metrics Display
col1, col2, col3, col4, col5 = st.columns(5)

total_traffic = filtered_df['Total Data Traffic Volume (GB)'].sum() if 'Total Data Traffic Volume (GB)' in filtered_df else 0
avg_dl_thrp = filtered_df['DL_Throughput_Mbps'].mean() if 'DL_Throughput_Mbps' in filtered_df else 0
avg_cssr = filtered_df['Call Setup Success Rate'].mean() if 'Call Setup Success Rate' in filtered_df else 0
avg_drop = filtered_df['Service Drop (all service)'].mean() if 'Service Drop (all service)' in filtered_df else 0
avg_volte_drop = filtered_df['Call Drop Rate (VoLTE)'].mean() if 'Call Drop Rate (VoLTE)' in filtered_df else 0

with col1:
    st.metric("📊 Total Traffic", f"{total_traffic:,.1f} GB")
with col2:
    st.metric("🚀 Avg DL Throughput", f"{avg_dl_thrp:.2f} Mbps")
with col3:
    st.metric("📞 Call Setup SR", f"{avg_cssr:.2f}%")
with col4:
    st.metric("🔴 Service Drop Rate", f"{avg_drop:.3f}%")
with col5:
    st.metric("📱 VoLTE Drop Rate", f"{avg_volte_drop:.3f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. HOURLY TREND CHARTS
# -----------------------------------------------------------------------------
st.subheader("📈 Xu hướng KPI Theo Giờ Qua Các Ngày (Hourly Trend)")

hourly_df = filtered_df.groupby(['Date', 'Hour']).agg({
    col: 'mean' for col in [
        'DL_Throughput_Mbps', 'UL_Throughput_Mbps', 
        'Resource Block Untilizing Rate Downlink (%)', 'Call Setup Success Rate', 
        'Service Drop (all service)', 'CQI_4G', 'Intra-frequency HO (%)', 
        'Call Drop Rate (VoLTE)', 'VoLTE E-RAB Call Setup Success Rate'
    ] if col in filtered_df.columns
}).reset_index()

hourly_df['Date_Str'] = hourly_df['Date'].astype(str)

tab1, tab2, tab3 = st.tabs(["🚀 Throughput & PRB", "☎️ CDR & CSSR", "📶 Quality & VoLTE"])

with tab1:
    c1, c2 = st.columns(2)
    if 'DL_Throughput_Mbps' in hourly_df:
        with c1:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='DL_Throughput_Mbps', color='Date_Str', title='DL Throughput (Mbps)', markers=True).update_layout(template='plotly_dark'), use_container_width=True)
    if 'Resource Block Untilizing Rate Downlink (%)' in hourly_df:
        with c2:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='Resource Block Untilizing Rate Downlink (%)', color='Date_Str', title='PRB DL Utilization (%)', markers=True).update_layout(template='plotly_dark'), use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    if 'Service Drop (all service)' in hourly_df:
        with c1:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='Service Drop (all service)', color='Date_Str', title='Service Drop Rate (%)', markers=True).update_layout(template='plotly_dark'), use_container_width=True)
    if 'Call Setup Success Rate' in hourly_df:
        with c2:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='Call Setup Success Rate', color='Date_Str', title='CSSR (%)', markers=True).update_layout(template='plotly_dark'), use_container_width=True)

with tab3:
    c1, c2 = st.columns(2)
    if 'CQI_4G' in hourly_df:
        with c1:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='CQI_4G', color='Date_Str', title='CQI 4G Index', markers=True).update_layout(template='plotly_dark'), use_container_width=True)
    if 'Call Drop Rate (VoLTE)' in hourly_df:
        with c2:
            st.plotly_chart(px.line(hourly_df, x='Hour', y='Call Drop Rate (VoLTE)', color='Date_Str', title='VoLTE Drop Rate (%)', markers=True).update_layout(template='plotly_dark'), use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. WORST CELLS LIST FOR SELECTED KPI
# -----------------------------------------------------------------------------
st.subheader("⚠️ Danh Sách Worst Cells Theo Từng Chỉ Số KPI")

if cell_col:
    kpi_option = st.selectbox(
        "🎯 Chọn KPI muốn truy xuất danh sách Worst Cells:",
        [
            "Service Drop Rate (CDR)", 
            "Low Downlink Throughput", 
            "High PRB Congestion", 
            "VoLTE Call Drop Rate", 
            "Low CQI (Poor RF)"
        ]
    )

    top_n = st.slider("Số lượng Cells hiển thị:", min_value=5, max_value=30, value=10)

    # Aggregate by Cell
    cell_agg = filtered_df.groupby([site_col, cell_col]).agg({
        col: 'mean' for col in [
            'Service Drop (all service)', 'DL_Throughput_Mbps', 
            'Resource Block Untilizing Rate Downlink (%)', 'Call Drop Rate (VoLTE)', 
            'CQI_4G', 'Total Data Traffic Volume (GB)'
        ] if col in filtered_df.columns
    }).reset_index()

    if kpi_option == "Service Drop Rate (CDR)" and 'Service Drop (all service)' in cell_agg:
        res_df = cell_agg.sort_values(by='Service Drop (all service)', ascending=False).head(top_n)
    elif kpi_option == "Low Downlink Throughput" and 'DL_Throughput_Mbps' in cell_agg:
        res_df = cell_agg.sort_values(by='DL_Throughput_Mbps', ascending=True).head(top_n)
    elif kpi_option == "High PRB Congestion" and 'Resource Block Untilizing Rate Downlink (%)' in cell_agg:
        res_df = cell_agg.sort_values(by='Resource Block Untilizing Rate Downlink (%)', ascending=False).head(top_n)
    elif kpi_option == "VoLTE Call Drop Rate" and 'Call Drop Rate (VoLTE)' in cell_agg:
        res_df = cell_agg.sort_values(by='Call Drop Rate (VoLTE)', ascending=False).head(top_n)
    elif kpi_option == "Low CQI (Poor RF)" and 'CQI_4G' in cell_agg:
        res_df = cell_agg.sort_values(by='CQI_4G', ascending=True).head(top_n)
    else:
        res_df = cell_agg.head(top_n)

    st.dataframe(res_df, use_container_width=True)
else:
    st.info("Cột tên Cell không tồn tại trong dữ liệu đã upload.")

st.caption("🚀 Universal 4G/LTE RAN Dashboard — Build with Streamlit & Python")

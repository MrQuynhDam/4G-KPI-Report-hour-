import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CẤU HÌNH TRANG STREAMLIT
st.set_page_config(
    page_title="Báo Cáo Tình Trạng & Tối Ưu Mạng 4G LTE",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CHUẨN HÓA DỮ LIỆU
@st.cache_data
def load_data(file_path_or_buffer):
    df = pd.read_csv(file_path_or_buffer)
    df['Thời gian'] = pd.to_datetime(df['Thời gian'], errors='coerce')
    df['Ngày'] = df['Thời gian'].dt.date
    
    if 'Giờ' in df.columns:
        df['Giờ'] = pd.to_numeric(df['Giờ'], errors='coerce').fillna(df['Thời gian'].dt.hour).fillna(0).astype(int)
    else:
        df['Giờ'] = df['Thời gian'].dt.hour.fillna(0).astype(int)
    
    numeric_cols = [
        'User Uplink Average Throughput (Kbps)',
        'User Downlink Average Throughput (Kbps)',
        'CQI_4G', 'Call Setup Success Rate',
        'Inter-RAT HOSR (LTE to WCDMA) (%)',
        'Inter-frequency HO (%)', 'Intra-frequency HO (%)',
        'Resource Block Untilizing Rate Downlink (%)',
        'Service Drop (all service)', 'Total Data Traffic Volume (GB)',
        'Traffic Volumn DL (GB)', 'Traffic Volume UL (GB)',
        'Call Drop Rate (VoLTE)', 'Inter-frequency HO Success Rates (VoLTE)',
        'Intra-frequency HO Success Rates (VoLTE)',
        'VoLTE E-RAB Call Setup Success Rate', 'VoLTE Traffic (Erl)'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0

    df['_Weighted_DL_THP'] = df['User Downlink Average Throughput (Kbps)'] * df['Traffic Volumn DL (GB)']
    df['_Weighted_UL_THP'] = df['User Uplink Average Throughput (Kbps)'] * df['Traffic Volume UL (GB)']
    df['_Weighted_PRB_DL'] = df['Resource Block Untilizing Rate Downlink (%)'] * df['Traffic Volumn DL (GB)']
    df['_Weighted_CQI'] = df['CQI_4G'] * df['Total Data Traffic Volume (GB)']

    return df
# 3. SIDEBAR & BỘ LỌC
st.sidebar.title("📡 Cấu Hình & Bộ Lọc")
uploaded_file = st.sidebar.file_uploader("Tải lên file KPI (CSV)", type=["csv"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    try:
        df = load_data("4GKPI.csv")
    except Exception:
        st.error("Vui lòng tải file `4GKPI.csv` lên ứng dụng để tiếp tục.")
        st.stop()

all_dates = sorted([d for d in df['Ngày'].dropna().unique()])
selected_dates = st.sidebar.multiselect("Chọn Ngày", options=all_dates, default=all_dates)

all_hours = sorted([int(h) for h in df['Giờ'].dropna().unique()])
selected_hours = st.sidebar.multiselect("Chọn Giờ (0 - 23)", options=all_hours, default=all_hours)

all_provinces = sorted(df['Tỉnh/Tp'].dropna().unique()) if 'Tỉnh/Tp' in df.columns else []
selected_provinces = st.sidebar.multiselect("Tỉnh / TP", options=all_provinces, default=all_provinces)

df_prov = df[df['Tỉnh/Tp'].isin(selected_provinces)] if 'Tỉnh/Tp' in df.columns else df
all_wards = sorted(df_prov['Phường/xã'].dropna().unique()) if 'Phường/xã' in df.columns else []
selected_wards = st.sidebar.multiselect("Phường / Xã", options=all_wards, default=all_wards)

df_ward = df_prov[df_prov['Phường/xã'].isin(selected_wards)] if 'Phường/xã' in df.columns else df_prov
all_sites = sorted(df_ward['Site Name'].dropna().unique()) if 'Site Name' in df.columns else []
selected_sites = st.sidebar.multiselect("Site Name", options=all_sites, default=[])

filtered_df = df[(df['Ngày'].isin(selected_dates)) & (df['Giờ'].isin(selected_hours))]

if 'Tỉnh/Tp' in df.columns and selected_provinces:
    filtered_df = filtered_df[filtered_df['Tỉnh/Tp'].isin(selected_provinces)]
if 'Phường/xã' in df.columns and selected_wards:
    filtered_df = filtered_df[filtered_df['Phường/xã'].isin(selected_wards)]
if 'Site Name' in df.columns and selected_sites:
    filtered_df = filtered_df[filtered_df['Site Name'].isin(selected_sites)]

if filtered_df.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
    st.stop()

# 4. TÍNH KPI CHUẨN
def calculate_kpis(data):
    total_traffic = data['Total Data Traffic Volume (GB)'].sum()
    dl_traffic = data['Traffic Volumn DL (GB)'].sum()
    ul_traffic = data['Traffic Volume UL (GB)'].sum()
    
    avg_dl_thp = data['_Weighted_DL_THP'].sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_ul_thp = data['_Weighted_UL_THP'].sum() / (ul_traffic if ul_traffic > 0 else 1)
    avg_prb_dl = data['_Weighted_PRB_DL'].sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_cqi = data['_Weighted_CQI'].sum() / (total_traffic if total_traffic > 0 else 1)
    avg_cssr = data['Call Setup Success Rate'].mean()
    
    return {
        'total_traffic': total_traffic, 'dl_traffic': dl_traffic, 'ul_traffic': ul_traffic,
        'avg_dl_thp': avg_dl_thp, 'avg_ul_thp': avg_ul_thp,
        'avg_prb_dl': avg_prb_dl, 'avg_cqi': avg_cqi, 'avg_cssr': avg_cssr
    }

kpis = calculate_kpis(filtered_df)

# 5. GIAO DIỆN CHÍNH
st.title("📡 BÁO CÁO TÌNH TRẠNG & TỐI ƯU MẠNG 4G LTE")

col1, col2, col3, col4 = st.columns(4)
col1.metric("TỔNG TRAFFIC (GB)", f"{kpis['total_traffic']:,.2f} GB", f"DL: {kpis['dl_traffic']:,.1f} | UL: {kpis['ul_traffic']:,.1f}")
col2.metric("DL / UL THROUGHPUT", f"{kpis['avg_dl_thp']:,.0f} / {kpis['avg_ul_thp']:,.0f} Kbps")
col3.metric("CALL SETUP SUCCESS (CSSR)", f"{kpis['avg_cssr']:.2f}%", delta="Mục tiêu ≥ 98%")
col4.metric("PRB UTIL DL & CQI", f"{kpis['avg_prb_dl']:.1f}% / {kpis['avg_cqi']:.1f}%")
# 6. TAB NAVIGATION
tab1, tab2, tab3 = st.tabs([
    "📈 Phân Tích Biến Động (Daily & Hourly)",
    "⚠️ Phân Tích Cell / KPI Kém",
    "🛠 Khuyến Nghị Troubleshoot"
])

# TAB 1: BIỂU ĐỒ BIẾN ĐỘNG
with tab1:
    st.subheader("1. Biến Động Mức Ngày (Daily Trend)")
    daily_grouped = filtered_df.groupby('Ngày').agg({
        'Total Data Traffic Volume (GB)': 'sum',
        'Traffic Volumn DL (GB)': 'sum',
        '_Weighted_DL_THP': 'sum'
    }).reset_index()

    daily_grouped['DL Throughput (Kbps)'] = daily_grouped['_Weighted_DL_THP'] / daily_grouped['Traffic Volumn DL (GB)'].replace(0, 1)

    fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
    fig_daily.add_trace(go.Bar(x=daily_grouped['Ngày'], y=daily_grouped['Total Data Traffic Volume (GB)'], name="Total Traffic (GB)"), secondary_y=False)
    fig_daily.add_trace(go.Scatter(x=daily_grouped['Ngày'], y=daily_grouped['DL Throughput (Kbps)'], name="DL Throughput (Kbps)", mode='lines+markers'), secondary_y=True)
    fig_daily.update_layout(hovermode="x unified")
    st.plotly_chart(fig_daily, use_container_width=True)
    
    st.subheader("2. Biến Động Mức Giờ (Hourly Profile)")
    hourly_grouped = filtered_df.groupby('Giờ').agg({
        'Total Data Traffic Volume (GB)': 'sum',
        'Traffic Volumn DL (GB)': 'sum',
        '_Weighted_PRB_DL': 'sum',
        'Intra-frequency HO (%)': 'mean',
        'Inter-frequency HO (%)': 'mean'
    }).reset_index()

    hourly_grouped['PRB Util DL (%)'] = hourly_grouped['_Weighted_PRB_DL'] / hourly_grouped['Traffic Volumn DL (GB)'].replace(0, 1)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        fig_h = make_subplots(specs=[[{"secondary_y": True}]])
        fig_h.add_trace(go.Bar(x=hourly_grouped['Giờ'], y=hourly_grouped['Total Data Traffic Volume (GB)'], name="Traffic (GB)"), secondary_y=False)
        fig_h.add_trace(go.Scatter(x=hourly_grouped['Giờ'], y=hourly_grouped['PRB Util DL (%)'], name="PRB Util DL (%)"), secondary_y=True)
        st.plotly_chart(fig_h, use_container_width=True)
    with col_h2:
        fig_ho = go.Figure()
        fig_ho.add_trace(go.Scatter(x=hourly_grouped['Giờ'], y=hourly_grouped['Intra-frequency HO (%)'], name="Intra-freq HO (%)"))
        fig_ho.add_trace(go.Scatter(x=hourly_grouped['Giờ'], y=hourly_grouped['Inter-frequency HO (%)'], name="Inter-freq HO (%)"))
        st.plotly_chart(fig_ho, use_container_width=True)

# TAB 2: LỌC CELL KÉM
with tab2:
    st.subheader("Danh Sách Cell Kém Theo Ngưỡng Quy Chuẩn")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    thp_threshold = col_t1.number_input("DL Throughput < (Kbps)", value=10000, step=1000)
    prb_threshold = col_t2.number_input("PRB Util DL > (%)", value=70.0, step=5.0)
    cqi_threshold = col_t3.number_input("CQI_4G < (%)", value=90.0, step=5.0)
    drop_threshold = col_t4.number_input("Service Drops > (Lượt)", value=10, step=5)
        
    group_cols = [c for c in ['Mã đối tượng', 'Tên đối tượng', 'Site Name', 'Phường/xã'] if c in filtered_df.columns]
    
    if group_cols:
        cell_agg = filtered_df.groupby(group_cols).agg({
            'Total Data Traffic Volume (GB)': 'sum',
            'Traffic Volumn DL (GB)': 'sum',
            'Traffic Volume UL (GB)': 'sum',
            '_Weighted_DL_THP': 'sum',
            '_Weighted_UL_THP': 'sum',
            '_Weighted_PRB_DL': 'sum',
            '_Weighted_CQI': 'sum',
            'Call Setup Success Rate': 'mean',
            'Service Drop (all service)': 'sum'
        }).reset_index()

        cell_agg['Avg DL Throughput (Kbps)'] = cell_agg['_Weighted_DL_THP'] / cell_agg['Traffic Volumn DL (GB)'].replace(0, 1)
        cell_agg['Avg PRB Util DL (%)'] = cell_agg['_Weighted_PRB_DL'] / cell_agg['Traffic Volumn DL (GB)'].replace(0, 1)
        cell_agg['Avg CQI (%)'] = cell_agg['_Weighted_CQI'] / cell_agg['Total Data Traffic Volume (GB)'].replace(0, 1)

        bad_cells = cell_agg[
            (cell_agg['Avg DL Throughput (Kbps)'] < thp_threshold) |
            (cell_agg['Avg PRB Util DL (%)'] > prb_threshold) |
            (cell_agg['Avg CQI (%)'] < cqi_threshold) |
            (cell_agg['Service Drop (all service)'] > drop_threshold)
        ].sort_values(by='Avg DL Throughput (Kbps)', ascending=True)
        
        st.write(f"**Tổng số Cell bị cảnh báo kém:** {len(bad_cells)} / {len(cell_agg)} Cells")
        st.dataframe(bad_cells, use_container_width=True)

# TAB 3: TROUBLESHOOTING
with tab3:
    st.subheader("Chẩn Đoán Tự Động & Đề Xuất Tối Ưu")
    if 'bad_cells' not in locals() or bad_cells.empty:
        st.success("Không có Cell nào bị vi phạm ngưỡng KPI kém.")
    else:
        for _, row in bad_cells.iterrows():
            issues, actions = [], []
            if row['Avg PRB Util DL (%)'] > prb_threshold and row['Avg DL Throughput (Kbps)'] < thp_threshold:
                issues.append("Nghẽn vô tuyến")
                actions.append("• Mở rộng băng thông / MLB / Điều chỉnh Anten chia tải.")
            if row['Avg CQI (%)'] < cqi_threshold:
                issues.append("CQI kém / Nhiễu cao")
                actions.append("• Kiểm tra Tilt/Azimuth anten, quét nhiễu PIM / PCI collision.")
            if row['Service Drop (all service)'] > drop_threshold:
                issues.append("Rớt dịch vụ cao")
                actions.append("• Kiểm tra hardware log eNodeB, truyền dẫn S1 và Missing Neighbor.")
                
            cell_name = row.get('Tên đối tượng', 'N/A')
            site_name = row.get('Site Name', 'N/A')
            with st.expander(f"🔴 Cell: {cell_name} (Site: {site_name}) — {' | '.join(issues)}"):
                st.write(f"**DL Throughput:** {row['Avg DL Throughput (Kbps)']:,.0f} Kbps | **PRB Util:** {row['Avg PRB Util DL (%)']:.1f}% | **CQI:** {row['Avg CQI (%)']:.1f}%")
                st.info("\n".join(actions))

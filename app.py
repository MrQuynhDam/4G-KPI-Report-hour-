import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Báo Cáo Tình Trạng & Tối Ưu Mạng 4G LTE",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện chuyên nghiệp
st.markdown("""
<style>
    .main-title {
        font-size: 26px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 12px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 13px;
        color: #64748B;
        font-weight: 600;
    }
    .metric-value {
        font-size: 20px;
        font-weight: bold;
        color: #0F172A;
    }
    .stTable {
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. LOAD & CHUẨN HÓA DỮ LIỆU
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path_or_buffer):
    df = pd.read_csv(file_path_or_buffer)
    
    # Ép kiểu Datetime cho Thời gian
    df['Thời gian'] = pd.to_datetime(df['Thời gian'], errors='coerce')
    df['Ngày'] = df['Thời gian'].dt.date
    df['Giờ'] = df['Giờ'].fillna(df['Thời gian'].dt.hour).astype(int)
    
    # Chuẩn hóa các cột chỉ số số
    numeric_cols = [
        'User Uplink Average Throughput (Kbps)',
        'User Downlink Average Throughput (Kbps)',
        'CQI_4G',
        'Call Setup Success Rate',
        'Inter-RAT HOSR (LTE to WCDMA) (%)',
        'Inter-frequency HO (%)',
        'Intra-frequency HO (%)',
        'Resource Block Untilizing Rate Downlink (%)',
        'Service Drop (all service)',
        'Total Data Traffic Volume (GB)',
        'Traffic Volumn DL (GB)',
        'Traffic Volume UL (GB)',
        'Call Drop Rate (VoLTE)',
        'Inter-frequency HO Success Rates (VoLTE)',
        'Intra-frequency HO Success Rates (VoLTE)',
        'VoLTE E-RAB Call Setup Success Rate',
        'VoLTE Traffic (Erl)'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df


# -----------------------------------------------------------------------------
# 3. SIDEBAR: UPLOAD FILE & BỘ LỌC ĐỘNG
# -----------------------------------------------------------------------------
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

# Bộ lọc động
st.sidebar.subheader("Bộ Lọc Dữ Liệu")

# Lọc Ngày
all_dates = sorted(df['Ngày'].dropna().unique())
selected_dates = st.sidebar.multiselect("Chọn Ngày", options=all_dates, default=all_dates)

# Lọc Giờ
all_hours = sorted(df['Giờ'].dropna().unique())
selected_hours = st.sidebar.multiselect("Chọn Giờ (0 - 23)", options=all_hours, default=all_hours)

# Lọc Tỉnh/Thành phố
all_provinces = sorted(df['Tỉnh/Tp'].dropna().unique())
selected_provinces = st.sidebar.multiselect("Tỉnh / TP", options=all_provinces, default=all_provinces)

# Lọc Phường/Xã
filtered_df_temp = df[df['Tỉnh/Tp'].isin(selected_provinces)]
all_wards = sorted(filtered_df_temp['Phường/xã'].dropna().unique())
selected_wards = st.sidebar.multiselect("Phường / Xã", options=all_wards, default=all_wards)

# Lọc Site
filtered_df_temp = filtered_df_temp[filtered_df_temp['Phường/xã'].isin(selected_wards)]
all_sites = sorted(filtered_df_temp['Site Name'].dropna().unique())
selected_sites = st.sidebar.multiselect("Site Name", options=all_sites, default=[])

# Áp dụng bộ lọc
filtered_df = df[
    (df['Ngày'].isin(selected_dates)) &
    (df['Giờ'].isin(selected_hours)) &
    (df['Tỉnh/Tp'].isin(selected_provinces)) &
    (df['Phường/xã'].isin(selected_wards))
]

if selected_sites:
    filtered_df = filtered_df[filtered_df['Site Name'].isin(selected_sites)]

if filtered_df.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
    st.stop()


# -----------------------------------------------------------------------------
# 4. HÀM TÍNH TOÁN KPI CHUẨN (SUM TRAFFIC & WEIGHTED AVERAGE KPI)
# -----------------------------------------------------------------------------
def calculate_kpis(data):
    # 1. SUM Traffic (Tuyệt đối không lấy AVG)
    total_traffic = data['Total Data Traffic Volume (GB)'].sum()
    dl_traffic = data['Traffic Volumn DL (GB)'].sum()
    ul_traffic = data['Traffic Volume UL (GB)'].sum()
    volte_traffic = data['VoLTE Traffic (Erl)'].sum()
    
    # 2. Weighted Avg Throughput
    avg_dl_thp = (data['User Downlink Average Throughput (Kbps)'] * data['Traffic Volumn DL (GB)']).sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_ul_thp = (data['User Uplink Average Throughput (Kbps)'] * data['Traffic Volume UL (GB)']).sum() / (ul_traffic if ul_traffic > 0 else 1)
    
    # 3. Weighted Avg PRB Util & CQI (Theo Traffic)
    avg_prb_dl = (data['Resource Block Untilizing Rate Downlink (%)'] * data['Traffic Volumn DL (GB)']).sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_cqi = (data['CQI_4G'] * data['Total Data Traffic Volume (GB)']).sum() / (total_traffic if total_traffic > 0 else 1)
    
    # 4. Unweighted Avg cho các KPI Tỷ lệ
    avg_cssr = data['Call Setup Success Rate'].mean()
    total_drops = data['Service Drop (all service)'].sum()
    avg_volte_cssr = data['VoLTE E-RAB Call Setup Success Rate'].mean()
    avg_volte_drop = data['Call Drop Rate (VoLTE)'].mean()
    
    return {
        'total_traffic': total_traffic,
        'dl_traffic': dl_traffic,
        'ul_traffic': ul_traffic,
        'volte_traffic': volte_traffic,
        'avg_dl_thp': avg_dl_thp,
        'avg_ul_thp': avg_ul_thp,
        'avg_prb_dl': avg_prb_dl,
        'avg_cqi': avg_cqi,
        'avg_cssr': avg_cssr,
        'total_drops': total_drops,
        'avg_volte_cssr': avg_volte_cssr,
        'avg_volte_drop': avg_volte_drop
    }

kpis = calculate_kpis(filtered_df)


# -----------------------------------------------------------------------------
# 5. GIAO DIỆN CHÍNH: EXECUTIVE SUMMARY
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">📡 BÁO CÁO TÌNH TRẠNG & TỐI ƯU MẠNG 4G LTE</div>', unsafe_allow_html=True)

# Row 1: Traffic Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">TỔNG TRAFFIC (GB)</div>
        <div class="metric-value">{kpis['total_traffic']:,.2f} GB</div>
        <small>DL: {kpis['dl_traffic']:,.1f} | UL: {kpis['ul_traffic']:,.1f}</small>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">DL / UL THROUGHPUT</div>
        <div class="metric-value">{kpis['avg_dl_thp']:,.0f} / {kpis['avg_ul_thp']:,.0f} Kbps</div>
        <small>Tải xuống / Tải lên trung bình</small>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">CALL SETUP SUCCESS (CSSR)</div>
        <div class="metric-value" style="color: {'green' if kpis['avg_cssr'] >= 98 else 'red'}">{kpis['avg_cssr']:.2f}%</div>
        <small>Mục tiêu ≥ 98%</small>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">PRB UTIL DL & CQI</div>
        <div class="metric-value">{kpis['avg_prb_dl']:.1f}% / {kpis['avg_cqi']:.1f}%</div>
        <small>Tải PRB DL / Chất lượng CQI</small>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. TAB NAVIGATION DÀNH CHO CÁC PHẦN BÁO CÁO
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 Phân Tích Biến Động (Daily & Hourly)",
    "⚠️ Phân Tích Cell / KPI Kém",
    "🛠️️ Khuyến Nghị Troubleshoot"
])

# -----------------------------------------------------------------------------
# TAB 1: PHẦN BIỂU ĐỒ BIẾN ĐỘNG (DAILY & HOURLY TRENDS)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("1. Biến Động Mức Ngày (Daily Trend)")
    
    # Gom nhóm theo ngày
    daily_df = filtered_df.groupby('Ngày').apply(lambda x: pd.Series({
        'Total Traffic (GB)': x['Total Data Traffic Volume (GB)'].sum(),
        'DL Traffic (GB)': x['Traffic Volumn DL (GB)'].sum(),
        'UL Traffic (GB)': x['Traffic Volume UL (GB)'].sum(),
        'DL Throughput (Kbps)': (x['User Downlink Average Throughput (Kbps)'] * x['Traffic Volumn DL (GB)']).sum() / (x['Traffic Volumn DL (GB)'].sum() if x['Traffic Volumn DL (GB)'].sum() > 0 else 1),
        'UL Throughput (Kbps)': (x['User Uplink Average Throughput (Kbps)'] * x['Traffic Volume UL (GB)']).sum() / (x['Traffic Volume UL (GB)'].sum() if x['Traffic Volume UL (GB)'].sum() > 0 else 1),
        'CSSR (%)': x['Call Setup Success Rate'].mean(),
        'Service Drop Count': x['Service Drop (all service)'].sum()
    })).reset_index()
    
    # Biểu đồ Ngày: Traffic (Bar) + Throughput (Line)
    fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_daily.add_trace(
        go.Bar(x=daily_df['Ngày'], y=daily_df['Total Traffic (GB)'], name="Total Traffic (GB)", marker_color='#3B82F6'),
        secondary_y=False
    )
    
    fig_daily.add_trace(
        go.Scatter(x=daily_df['Ngày'], y=daily_df['DL Throughput (Kbps)'], name="DL Throughput (Kbps)", mode='lines+markers', line=dict(color='#EF4444', width=3)),
        secondary_y=True
    )
    
    fig_daily.update_layout(title_text="Tổng Traffic & DL Throughput Trung Bình Theo Ngày", hovermode="x unified")
    fig_daily.update_xaxes(title_text="Ngày")
    fig_daily.update_yaxes(title_text="Traffic (GB)", secondary_y=False)
    fig_daily.update_yaxes(title_text="DL Throughput (Kbps)", secondary_y=True)
    st.plotly_chart(fig_daily, use_container_width=True)
    
    st.markdown("---")
    st.subheader("2. Biến Động Mức Giờ (Hourly Profile - 24h)")
    
    # Gom nhóm theo giờ
    hourly_df = filtered_df.groupby('Giờ').apply(lambda x: pd.Series({
        'Total Traffic (GB)': x['Total Data Traffic Volume (GB)'].sum(),
        'DL Throughput (Kbps)': (x['User Downlink Average Throughput (Kbps)'] * x['Traffic Volumn DL (GB)']).sum() / (x['Traffic Volumn DL (GB)'].sum() if x['Traffic Volumn DL (GB)'].sum() > 0 else 1),
        'PRB Util DL (%)': (x['Resource Block Untilizing Rate Downlink (%)'] * x['Traffic Volumn DL (GB)']).sum() / (x['Traffic Volumn DL (GB)'].sum() if x['Traffic Volumn DL (GB)'].sum() > 0 else 1),
        'Intra HO (%)': x['Intra-frequency HO (%)'].mean(),
        'Inter HO (%)': x['Inter-frequency HO (%)'].mean(),
        'Inter-RAT HOSR (%)': x['Inter-RAT HOSR (LTE to WCDMA) (%)'].mean()
    })).reset_index()
    
    col_h1, col_h2 = st.columns(2)
    
    with col_h1:
        # Traffic & PRB Util
        fig_hourly_prb = make_subplots(specs=[[{"secondary_y": True}]])
        fig_hourly_prb.add_trace(
            go.Bar(x=hourly_df['Giờ'], y=hourly_df['Total Traffic (GB)'], name="Traffic (GB)", marker_color='#10B981'),
            secondary_y=False
        )
        fig_hourly_prb.add_trace(
            go.Scatter(x=hourly_df['Giờ'], y=hourly_df['PRB Util DL (%)'], name="PRB Util DL (%)", mode='lines+markers', line=dict(color='#F59E0B', width=2)),
            secondary_y=True
        )
        fig_hourly_prb.update_layout(title_text="Phụ Tải Traffic & Mức Độ Sử Dụng PRB DL Theo Giờ (Xác Định Giờ Bận)")
        fig_hourly_prb.update_xaxes(title_text="Giờ trong ngày (0 - 23)")
        st.plotly_chart(fig_hourly_prb, use_container_width=True)
        
    with col_h2:
        # Handover Performance
        fig_ho = go.Figure()
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Intra HO (%)'], name="Intra-freq HO (%)", mode='lines'))
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Inter HO (%)'], name="Inter-freq HO (%)", mode='lines'))
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Inter-RAT HOSR (%)'], name="Inter-RAT HOSR (%)", mode='lines'))
        fig_ho.update_layout(title_text="Tỷ Lệ Chuyển Giao Thành Công Theo Giờ", hovermode="x unified")
        fig_ho.update_xaxes(title_text="Giờ trong ngày (0 - 23)")
        st.plotly_chart(fig_ho, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 2: LỌC & DANH SÁCH CELL / KPI KÉM
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Danh Sách Cell Kém Theo Ngưỡng Quy Chuẩn")
    
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        thp_threshold = st.number_input("DL Throughput < (Kbps)", value=10000, step=1000)
    with col_t2:
        prb_threshold = st.number_input("PRB Util DL > (%)", value=70.0, step=5.0)
    with col_t3:
        cqi_threshold = st.number_input("CQI_4G < (%)", value=90.0, step=5.0)
    with col_t4:
        drop_threshold = st.number_input("Service Drops > (Lượt)", value=10, step=5)
        
    # Gom nhóm theo Cell (Tên đối tượng / Mã đối tượng)
    cell_summary = filtered_df.groupby(['Mã đối tượng', 'Tên đối tượng', 'Site Name', 'Phường/xã']).apply(lambda x: pd.Series({
        'Total Traffic (GB)': x['Total Data Traffic Volume (GB)'].sum(),
        'DL Traffic (GB)': x['Traffic Volumn DL (GB)'].sum(),
        'Avg DL Throughput (Kbps)': (x['User Downlink Average Throughput (Kbps)'] * x['Traffic Volumn DL (GB)']).sum() / (x['Traffic Volumn DL (GB)'].sum() if x['Traffic Volumn DL (GB)'].sum() > 0 else 1),
        'Avg UL Throughput (Kbps)': (x['User Uplink Average Throughput (Kbps)'] * x['Traffic Volume UL (GB)']).sum() / (x['Traffic Volume UL (GB)'].sum() if x['Traffic Volume UL (GB)'].sum() > 0 else 1),
        'Avg PRB Util DL (%)': (x['Resource Block Untilizing Rate Downlink (%)'] * x['Traffic Volumn DL (GB)']).sum() / (x['Traffic Volumn DL (GB)'].sum() if x['Traffic Volumn DL (GB)'].sum() > 0 else 1),
        'Avg CQI (%)': (x['CQI_4G'] * x['Total Data Traffic Volume (GB)']).sum() / (x['Total Data Traffic Volume (GB)'].sum() if x['Total Data Traffic Volume (GB)'].sum() > 0 else 1),
        'CSSR (%)': x['Call Setup Success Rate'].mean(),
        'Total Service Drops': x['Service Drop (all service)'].sum(),
        'Intra HO (%)': x['Intra-frequency HO (%)'].mean(),
        'Inter HO (%)': x['Inter-frequency HO (%)'].mean()
    })).reset_index()
    
    # Lọc các Cell kém
    bad_cells = cell_summary[
        (cell_summary['Avg DL Throughput (Kbps)'] < thp_threshold) |
        (cell_summary['Avg PRB Util DL (%)'] > prb_threshold) |
        (cell_summary['Avg CQI (%)'] < cqi_threshold) |
        (cell_summary['Total Service Drops'] > drop_threshold)
    ].sort_values(by='Avg DL Throughput (Kbps)', ascending=True)
    
    st.write(f"**Tổng số Cell bị cảnh báo kém:** {len(bad_cells)} / {len(cell_summary)} Cells")
    
    st.dataframe(
        bad_cells.style.format({
            'Total Traffic (GB)': '{:,.2f}',
            'Avg DL Throughput (Kbps)': '{:,.0f}',
            'Avg UL Throughput (Kbps)': '{:,.0f}',
            'Avg PRB Util DL (%)': '{:.1f}%',
            'Avg CQI (%)': '{:.1f}%',
            'CSSR (%)': '{:.2f}%',
            'Total Service Drops': '{:,.0f}'
        }),
        use_container_width=True
    )


# -----------------------------------------------------------------------------
# TAB 3: ĐỀ XUẤT TROUBLESHOOT & HƯỚNG XỬ LÝ SỰ CỐ
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Chẩn Đoán Tự Động & Đề Xuất Tối Ưu Cho Cell Kém")
    
    if bad_cells.empty:
        st.success("Không có Cell nào bị vi phạm ngưỡng KPI kém trong bộ lọc hiện tại.")
    else:
        troubleshoot_list = []
        
        for _, row in bad_cells.iterrows():
            issues = []
            actions = []
            
            # 1. Congestion Check
            if row['Avg PRB Util DL (%)'] > prb_threshold and row['Avg DL Throughput (Kbps)'] < thp_threshold:
                issues.append("Nghẽn vô tuyến (High PRB Util & Low DL Throughput)")
                actions.append("• Mở rộng băng thông (Kích hoạt thêm Carrier/MIMO)\n• Tối ưu Mobility Load Balancing (MLB)\n• Điều chỉnh góc ngẩng/nghiêng Anten để chia tải.")
                
            # 2. Coverage & Interference Check
            if row['Avg CQI (%)'] < cqi_threshold:
                issues.append("Chất lượng vô tuyến kém / Nhiễu cao (Low CQI)")
                actions.append("• Kiểm tra Tilt/Azimuth anten thực tế tại trạm\n• Quét nhiễu PIM/External interference\n• Rà soát PCI collision/confusion với trạm láng giềng.")
                
            # 3. Drop Issue Check
            if row['Total Service Drops'] > drop_threshold:
                issues.append("Rớt dịch vụ cao (High Service Drops)")
                actions.append("• Kiểm tra hardware log eNodeB (VSWR, quạt, TRX card)\n• Bổ sung Missing Neighbor Relation\n• Kiểm tra chất lượng đường truyền dẫn (S1/Abis link).")
                
            # 4. Low CSSR
            if row['CSSR (%)'] < 95.0:
                issues.append("Khởi tạo cuộc gọi kém (Low CSSR)")
                actions.append("• Kiểm tra quá tải kênh Paging/RACH\n• Kiểm tra cấu hình thông số CCE/PRACH\n• Kiểm tra Core Network / MME response.")
                
            troubleshoot_list.append({
                'Mã đối tượng': row['Mã đối tượng'],
                'Tên Cell': row['Tên đối tượng'],
                'Site Name': row['Site Name'],
                'DL Throughput (Kbps)': f"{row['Avg DL Throughput (Kbps)']:,.0f}",
                'PRB Util (%)': f"{row['Avg PRB Util DL (%)']:.1f}%",
                'CQI (%)': f"{row['Avg CQI (%)']:.1f}%",
                'Vấn Đề Chẩn Đoán': " | ".join(issues) if issues else "Lỗi KPI khác",
                'Đề Xuất Hướng Xử Lý': "\n".join(actions) if actions else "Theo dõi thêm log trạm"
            })
            
        ts_df = pd.DataFrame(troubleshoot_list)
        
        for idx, item in ts_df.iterrows():
            with st.expander(f"🔴 Cell: {item['Tên Cell']} (Site: {item['Site Name']}) — {item['Vấn Đề Chẩn Đoán']}"):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.write(f"**DL Throughput:** {item['DL Throughput (Kbps)']} Kbps")
                    st.write(f"**PRB Utilization:** {item['PRB Util (%)']}")
                    st.write(f"**CQI 4G:** {item['CQI (%)']}")
                with col_b:
                    st.write("**Giải Pháp Troubleshoot Đề Xuất:**")
                    st.info(item['Đề Xuất Hướng Xử Lý'])

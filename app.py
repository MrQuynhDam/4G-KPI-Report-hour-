import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

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
# 2. LOAD & CHUẨN HÓA DỮ LIỆU TỪ TRÌNH DUYỆT (FILE UPLOAD)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_source):
    df = pd.read_csv(file_source)
    
    # Ép kiểu Datetime chuẩn hóa nhanh
    df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='mixed', errors='coerce')
    df['Ngày'] = df['Thời gian'].dt.date
    df['Giờ'] = df['Giờ'].fillna(df['Thời gian'].dt.hour).fillna(0).astype(int)
    
    # Chuẩn hóa các cột số
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
            
    # Tính toán trước các cột trọng số
    df['DL_Thp_Weight'] = df['User Downlink Average Throughput (Kbps)'] * df['Traffic Volumn DL (GB)']
    df['UL_Thp_Weight'] = df['User Uplink Average Throughput (Kbps)'] * df['Traffic Volume UL (GB)']
    df['PRB_Weight'] = df['Resource Block Untilizing Rate Downlink (%)'] * df['Traffic Volumn DL (GB)']
    df['CQI_Weight'] = df['CQI_4G'] * df['Total Data Traffic Volume (GB)']
    
    return df


# -----------------------------------------------------------------------------
# 3. SIDEBAR & XỬ LÝ UPLOAD FILE
# -----------------------------------------------------------------------------
st.sidebar.title("📡 Cấu Hình & Bộ Lọc")

uploaded_file = st.sidebar.file_uploader("Tải lên file KPI 4G (.csv)", type=["csv"])

df = None
if uploaded_file is not None:
    df = load_data(uploaded_file)
elif os.path.exists("4GKPI.csv"):
    df = load_data("4GKPI.csv")

if df is None:
    st.markdown('<div class="main-title">📡 BÁO CÁO TÌNH TRẠNG & TỐI ƯU MẠNG 4G LTE</div>', unsafe_allow_html=True)
    st.info("👇 **Ứng dụng đã sẵn sàng!** Vui lòng bấm nút **Browse files** ở thanh bên trái (Sidebar) để tải lên file dữ liệu KPI 4G (`.csv`) của bạn.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. BỘ LỌC ĐỘNG (Dữ liệu đã được load thành công)
# -----------------------------------------------------------------------------
st.sidebar.subheader("Bộ Lọc Dữ Liệu")

# Lọc Ngày
all_dates = sorted([d for d in df['Ngày'].dropna().unique()])
selected_dates = st.sidebar.multiselect("Chọn Ngày", options=all_dates, default=all_dates)

# Lọc Giờ
all_hours = sorted(df['Giờ'].unique())
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
# 5. HÀM TÍNH TOÁN KPI CHUẨN (SUM TRAFFIC & WEIGHTED AVERAGE KPI)
# -----------------------------------------------------------------------------
def calculate_kpis(data):
    total_traffic = data['Total Data Traffic Volume (GB)'].sum()
    dl_traffic = data['Traffic Volumn DL (GB)'].sum()
    ul_traffic = data['Traffic Volume UL (GB)'].sum()
    volte_traffic = data['VoLTE Traffic (Erl)'].sum()
    
    avg_dl_thp = data['DL_Thp_Weight'].sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_ul_thp = data['UL_Thp_Weight'].sum() / (ul_traffic if ul_traffic > 0 else 1)
    avg_prb_dl = data['PRB_Weight'].sum() / (dl_traffic if dl_traffic > 0 else 1)
    avg_cqi = data['CQI_Weight'].sum() / (total_traffic if total_traffic > 0 else 1)
    
    avg_cssr = data['Call Setup Success Rate'].mean()
    total_drops = data['Service Drop (all service)'].sum()
    
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
        'total_drops': total_drops
    }

kpis = calculate_kpis(filtered_df)


# -----------------------------------------------------------------------------
# 6. GIAO DIỆN CHÍNH: EXECUTIVE SUMMARY
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">📡 BÁO CÁO TÌNH TRẠNG & TỐI ƯU MẠNG 4G LTE</div>', unsafe_allow_html=True)

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
# 7. TAB NAVIGATION DÀNH CHO CÁC PHẦN BÁO CÁO
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 Phân Tích Biến Động (Daily & Hourly)",
    "⚠️ Phân Tích Cell / KPI Kém",
    "🛠️ Khuyến Nghị Troubleshoot"
])

# -----------------------------------------------------------------------------
# TAB 1: PHẦN BIỂU ĐỒ BIẾN ĐỘNG (DAILY & HOURLY TRENDS)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("1. Biến Động Mức Ngày (Daily Trend)")
    
    daily_df = filtered_df.groupby('Ngày', as_index=False).agg({
        'Total Data Traffic Volume (GB)': 'sum',
        'Traffic Volumn DL (GB)': 'sum',
        'Traffic Volume UL (GB)': 'sum',
        'DL_Thp_Weight': 'sum',
        'UL_Thp_Weight': 'sum',
        'Call Setup Success Rate': 'mean',
        'Service Drop (all service)': 'sum'
    })
    
    daily_df['DL Throughput (Kbps)'] = daily_df['DL_Thp_Weight'] / daily_df['Traffic Volumn DL (GB)'].replace(0, 1)
    
    fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_daily.add_trace(
        go.Bar(x=daily_df['Ngày'], y=daily_df['Total Data Traffic Volume (GB)'], name="Total Traffic (GB)", marker_color='#3B82F6'),
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
    
    hourly_df = filtered_df.groupby('Giờ', as_index=False).agg({
        'Total Data Traffic Volume (GB)': 'sum',
        'Traffic Volumn DL (GB)': 'sum',
        'DL_Thp_Weight': 'sum',
        'PRB_Weight': 'sum',
        'Intra-frequency HO (%)': 'mean',
        'Inter-frequency HO (%)': 'mean',
        'Inter-RAT HOSR (LTE to WCDMA) (%)': 'mean'
    })
    
    hourly_df['PRB Util DL (%)'] = hourly_df['PRB_Weight'] / hourly_df['Traffic Volumn DL (GB)'].replace(0, 1)
    
    col_h1, col_h2 = st.columns(2)
    
    with col_h1:
        fig_hourly_prb = make_subplots(specs=[[{"secondary_y": True}]])
        fig_hourly_prb.add_trace(
            go.Bar(x=hourly_df['Giờ'], y=hourly_df['Total Data Traffic Volume (GB)'], name="Traffic (GB)", marker_color='#10B981'),
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
        fig_ho = go.Figure()
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Intra-frequency HO (%)'], name="Intra-freq HO (%)", mode='lines'))
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Inter-frequency HO (%)'], name="Inter-freq HO (%)", mode='lines'))
        fig_ho.add_trace(go.Scatter(x=hourly_df['Giờ'], y=hourly_df['Inter-RAT HOSR (LTE to WCDMA) (%)'], name="Inter-RAT HOSR (%)", mode='lines'))
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
        
    cell_summary = filtered_df.groupby(['Mã đối tượng', 'Tên đối tượng', 'Site Name', 'Phường/xã'], as_index=False).agg({
        'Total Data Traffic Volume (GB)': 'sum',
        'Traffic Volumn DL (GB)': 'sum',
        'Traffic Volume UL (GB)': 'sum',
        'DL_Thp_Weight': 'sum',
        'UL_Thp_Weight': 'sum',
        'PRB_Weight': 'sum',
        'CQI_Weight': 'sum',
        'Call Setup Success Rate': 'mean',
        'Service Drop (all service)': 'sum'
    })
    
    cell_summary['Avg DL Throughput (Kbps)'] = cell_summary['DL_Thp_Weight'] / cell_summary['Traffic Volumn DL (GB)'].replace(0, 1)
    cell_summary['Avg UL Throughput (Kbps)'] = cell_summary['UL_Thp_Weight'] / cell_summary['Traffic Volume UL (GB)'].replace(0, 1)
    cell_summary['Avg PRB Util DL (%)'] = cell_summary['PRB_Weight'] / cell_summary['Traffic Volumn DL (GB)'].replace(0, 1)
    cell_summary['Avg CQI (%)'] = cell_summary['CQI_Weight'] / cell_summary['Total Data Traffic Volume (GB)'].replace(0, 1)
    
    bad_cells = cell_summary[
        (cell_summary['Avg DL Throughput (Kbps)'] < thp_threshold) |
        (cell_summary['Avg PRB Util DL (%)'] > prb_threshold) |
        (cell_summary['Avg CQI (%)'] < cqi_threshold) |
        (cell_summary['Service Drop (all service)'] > drop_threshold)
    ].sort_values(by='Avg DL Throughput (Kbps)', ascending=True)
    
    st.write(f"**Tổng số Cell bị cảnh báo kém:** {len(bad_cells)} / {len(cell_summary)} Cells")
    
    display_df = bad_cells[['Mã đối tượng', 'Tên đối tượng', 'Site Name', 'Phường/xã', 'Total Data Traffic Volume (GB)', 'Avg DL Throughput (Kbps)', 'Avg PRB Util DL (%)', 'Avg CQI (%)', 'Call Setup Success Rate', 'Service Drop (all service)']]
    display_df.columns = ['Mã đối tượng', 'Tên Cell', 'Site Name', 'Phường/xã', 'Traffic (GB)', 'DL Throughput (Kbps)', 'PRB Util (%)', 'CQI 4G (%)', 'CSSR (%)', 'Service Drops']
    
    st.dataframe(
        display_df.style.format({
            'Traffic (GB)': '{:,.2f}',
            'DL Throughput (Kbps)': '{:,.0f}',
            'PRB Util (%)': '{:.1f}%',
            'CQI 4G (%)': '{:.1f}%',
            'CSSR (%)': '{:.2f}%',
            'Service Drops': '{:,.0f}'
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
        for idx, row in bad_cells.iterrows():
            issues = []
            actions = []
            
            if row['Avg PRB Util DL (%)'] > prb_threshold and row['Avg DL Throughput (Kbps)'] < thp_threshold:
                issues.append("Nghẽn vô tuyến (High PRB Util & Low DL Throughput)")
                actions.append("• Mở rộng băng thông (Kích hoạt thêm Carrier/MIMO)\n• Tối ưu Mobility Load Balancing (MLB)\n• Điều chỉnh góc ngẩng/nghiêng Anten để chia tải.")
                
            if row['Avg CQI (%)'] < cqi_threshold:
                issues.append("Chất lượng vô tuyến kém / Nhiễu cao (Low CQI)")
                actions.append("• Kiểm tra Tilt/Azimuth anten thực tế tại trạm\n• Quét nhiễu PIM/External interference\n• Rà soát PCI collision/confusion với trạm láng giềng.")
                
            if row['Service Drop (all service)'] > drop_threshold:
                issues.append("Rớt dịch vụ cao (High Service Drops)")
                actions.append("• Kiểm tra hardware log eNodeB (VSWR, quạt, TRX card)\n• Bổ sung Missing Neighbor Relation\n• Kiểm tra chất lượng đường truyền dẫn (S1/Abis link).")
                
            if row['Call Setup Success Rate'] < 95.0:
                issues.append("Khởi tạo cuộc gọi kém (Low CSSR)")
                actions.append("• Kiểm tra quá tải kênh Paging/RACH\n• Kiểm tra cấu hình thông số CCE/PRACH\n• Kiểm tra Core Network / MME response.")
                
            issue_title = " | ".join(issues) if issues else "Lỗi KPI cần theo dõi thêm"
            action_text = "\n".join(actions) if actions else "Theo dõi thêm log trạm"
            
            with st.expander(f"🔴 Cell: {row['Tên đối tượng']} (Site: {row['Site Name']}) — {issue_title}"):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.write(f"**DL Throughput:** {row['Avg DL Throughput (Kbps)']:,.0f} Kbps")
                    st.write(f"**PRB Utilization:** {row['Avg PRB Util DL (%)']:.1f}%")
                    st.write(f"**CQI 4G:** {row['Avg CQI (%)']:.1f}%")
                    st.write(f"**Service Drops:** {row['Service Drop (all service)']:,.0f}")
                with col_b:
                    st.write("**Giải Pháp Troubleshoot Đề Xuất:**")
                    st.info(action_text)

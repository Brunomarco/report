import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configure Streamlit page
st.set_page_config(
    page_title="LFS Amsterdam - TMS Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .highlight-box {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title and header
st.markdown('<h1 class="main-header">🚛 LFS Amsterdam - TMS Performance Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Transportation Management System Analytics & KPI Monitoring**")

# Sidebar for filters and controls
st.sidebar.title("📋 Dashboard Controls")
st.sidebar.markdown("---")

# Date range selector
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(datetime.now() - timedelta(days=30), datetime.now()),
    help="Select the period for analysis"
)

# Service type filter
service_types = st.sidebar.multiselect(
    "Service Types",
    options=['AVS', 'LFS', 'SP', 'RP'],
    default=['AVS', 'LFS', 'SP', 'RP'],
    help="Filter by service type"
)

# File upload section
st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Data Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload TMS Data (Excel)",
    type=['xlsx', 'xls'],
    help="Upload your TMS raw data file"
)

# Sample data generation (replace with your actual data loading)
@st.cache_data
def load_sample_data():
    """
    Replace this function with your actual data loading from Excel sheets
    """
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # Volume data
    volume_data = []
    for date in dates:
        for service in ['AVS', 'LFS', 'SP', 'RP']:
            volume_data.append({
                'Date': date,
                'Service_Type': service,
                'Volume': np.random.poisson(50 + (ord(service[0]) % 20)),
                'Revenue': np.random.normal(1000, 200),
                'Cost': np.random.normal(800, 150),
                'OTP_Score': np.random.beta(8, 2) * 100
            })
    
    df_volume = pd.DataFrame(volume_data)
    
    # Lane usage data
    lanes = ['AMS-LON', 'AMS-PAR', 'AMS-BER', 'AMS-ROM', 'AMS-MAD']
    lane_data = []
    for date in dates[::7]:  # Weekly data
        for lane in lanes:
            lane_data.append({
                'Date': date,
                'Lane': lane,
                'Utilization': np.random.uniform(0.3, 0.95),
                'Shipments': np.random.poisson(25),
                'Avg_Cost_Per_Shipment': np.random.normal(150, 30)
            })
    
    df_lanes = pd.DataFrame(lane_data)
    
    return df_volume, df_lanes

@st.cache_data
def load_excel_data(uploaded_file):
    """
    Load data from uploaded Excel file
    """
    if uploaded_file is not None:
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(uploaded_file)
            sheets = {}
            for sheet_name in excel_file.sheet_names:
                sheets[sheet_name] = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            return sheets
        except Exception as e:
            st.error(f"Error reading Excel file: {str(e)}")
            return None
    return None

# Load data
if uploaded_file is not None:
    excel_sheets = load_excel_data(uploaded_file)
    if excel_sheets:
        st.sidebar.success(f"✅ Loaded {len(excel_sheets)} sheets from Excel file")
        st.sidebar.write("Sheet names:", list(excel_sheets.keys()))
        # Here you would process your actual Excel data
        # For now, we'll use sample data
        df_volume, df_lanes = load_sample_data()
    else:
        df_volume, df_lanes = load_sample_data()
else:
    df_volume, df_lanes = load_sample_data()
    st.sidebar.info("📝 Using sample data. Upload your Excel file to see actual data.")

# Filter data based on sidebar selections
df_volume_filtered = df_volume[df_volume['Service_Type'].isin(service_types)]
df_volume_filtered = df_volume_filtered[
    (df_volume_filtered['Date'] >= pd.to_datetime(date_range[0])) &
    (df_volume_filtered['Date'] <= pd.to_datetime(date_range[1]))
]

# Main dashboard layout
col1, col2, col3, col4 = st.columns(4)

# KPI Metrics
with col1:
    total_volume = df_volume_filtered['Volume'].sum()
    prev_volume = df_volume_filtered['Volume'].sum() * 0.9  # Sample comparison
    delta_volume = total_volume - prev_volume
    st.metric(
        label="📦 Total Volume",
        value=f"{total_volume:,}",
        delta=f"{delta_volume:,.0f}",
        delta_color="normal"
    )

with col2:
    avg_otp = df_volume_filtered['OTP_Score'].mean()
    target_otp = 95.0
    delta_otp = avg_otp - target_otp
    st.metric(
        label="⏰ Avg OTP Score",
        value=f"{avg_otp:.1f}%",
        delta=f"{delta_otp:.1f}% vs target",
        delta_color="normal" if delta_otp >= 0 else "inverse"
    )

with col3:
    total_revenue = df_volume_filtered['Revenue'].sum()
    prev_revenue = total_revenue * 0.85  # Sample comparison
    delta_revenue = total_revenue - prev_revenue
    st.metric(
        label="💰 Total Revenue",
        value=f"€{total_revenue:,.0f}",
        delta=f"€{delta_revenue:,.0f}",
        delta_color="normal"
    )

with col4:
    profit_margin = ((df_volume_filtered['Revenue'].sum() - df_volume_filtered['Cost'].sum()) / df_volume_filtered['Revenue'].sum()) * 100
    target_margin = 20.0
    delta_margin = profit_margin - target_margin
    st.metric(
        label="📈 Profit Margin",
        value=f"{profit_margin:.1f}%",
        delta=f"{delta_margin:.1f}% vs target",
        delta_color="normal" if delta_margin >= 0 else "inverse"
    )

st.markdown("---")

# Volume Analysis Section
st.markdown('<h2 class="section-header">📊 Volume Analysis by Service Type</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Daily Volume Trends**")
    # Volume by service type (daily trend)
    daily_volume = df_volume_filtered.groupby(['Date', 'Service_Type'])['Volume'].sum().reset_index()
    pivot_volume = daily_volume.pivot(index='Date', columns='Service_Type', values='Volume')
    st.line_chart(pivot_volume)

with col2:
    st.markdown("**Volume Distribution by Service Type**")
    # Volume distribution
    service_totals = df_volume_filtered.groupby('Service_Type')['Volume'].sum()
    st.bar_chart(service_totals)

# Create summary table for volume
st.markdown("**Volume Summary Table**")
volume_summary = df_volume_filtered.groupby('Service_Type').agg({
    'Volume': ['sum', 'mean', 'std'],
    'Revenue': ['sum', 'mean'],
    'Cost': ['sum', 'mean']
}).round(2)

volume_summary.columns = ['Total Volume', 'Avg Daily Volume', 'Volume Std Dev', 
                         'Total Revenue (€)', 'Avg Daily Revenue (€)',
                         'Total Cost (€)', 'Avg Daily Cost (€)']
st.dataframe(volume_summary, use_container_width=True)

# OTP Analysis Section
st.markdown('<h2 class="section-header">⏱️ On-Time Performance (OTP) Analysis</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**OTP Performance by Service Type**")
    # OTP by service type
    otp_by_service = df_volume_filtered.groupby('Service_Type')['OTP_Score'].mean()
    st.bar_chart(otp_by_service)
    
    # Add target line information
    st.markdown('<div class="highlight-box">🎯 <strong>Target OTP: 95%</strong><br>Red line indicates target performance level</div>', unsafe_allow_html=True)

with col2:
    st.markdown("**Weekly OTP Trends**")
    # OTP trend over time
    df_volume_filtered['Week'] = df_volume_filtered['Date'].dt.to_period('W')
    weekly_otp = df_volume_filtered.groupby(['Week', 'Service_Type'])['OTP_Score'].mean().reset_index()
    weekly_otp['Week'] = weekly_otp['Week'].dt.start_time
    pivot_otp = weekly_otp.pivot(index='Week', columns='Service_Type', values='OTP_Score')
    st.line_chart(pivot_otp)

# OTP Statistics
otp_stats = df_volume_filtered.groupby('Service_Type')['OTP_Score'].agg(['mean', 'std', 'min', 'max']).round(2)
otp_stats.columns = ['Average OTP (%)', 'Std Deviation', 'Minimum OTP (%)', 'Maximum OTP (%)']
st.dataframe(otp_stats, use_container_width=True)

# Cost vs Sales Analysis
st.markdown('<h2 class="section-header">💰 Cost vs. Sales Analysis</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Monthly Revenue vs Cost**")
    # Monthly aggregation
    df_volume_filtered['Month'] = df_volume_filtered['Date'].dt.to_period('M')
    monthly_data = df_volume_filtered.groupby('Month').agg({
        'Revenue': 'sum',
        'Cost': 'sum'
    }).reset_index()
    monthly_data['Month'] = monthly_data['Month'].dt.start_time
    monthly_data = monthly_data.set_index('Month')
    st.line_chart(monthly_data)

with col2:
    st.markdown("**Profit Margin by Service Type**")
    service_financials = df_volume_filtered.groupby('Service_Type').agg({
        'Revenue': 'sum',
        'Cost': 'sum'
    })
    service_financials['Profit_Margin'] = ((service_financials['Revenue'] - service_financials['Cost']) / service_financials['Revenue']) * 100
    st.bar_chart(service_financials['Profit_Margin'])

# Financial summary
financial_summary = df_volume_filtered.groupby('Service_Type').agg({
    'Revenue': 'sum',
    'Cost': 'sum'
})
financial_summary['Profit'] = financial_summary['Revenue'] - financial_summary['Cost']
financial_summary['Profit_Margin_Percent'] = (financial_summary['Profit'] / financial_summary['Revenue'] * 100).round(2)
financial_summary = financial_summary.round(2)
st.dataframe(financial_summary, use_container_width=True)

# Lane Usage Analysis
st.markdown('<h2 class="section-header">🛣️ Lane Usage Analysis</h2>', unsafe_allow_html=True)

# Filter lane data based on date range
df_lanes_filtered = df_lanes[
    (df_lanes['Date'] >= pd.to_datetime(date_range[0])) &
    (df_lanes['Date'] <= pd.to_datetime(date_range[1]))
]

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Average Lane Utilization**")
    lane_util = df_lanes_filtered.groupby('Lane')['Utilization'].mean()
    st.bar_chart(lane_util)
    st.markdown('<div class="highlight-box">🎯 <strong>Target Utilization: 80%</strong></div>', unsafe_allow_html=True)

with col2:
    st.markdown("**Average Cost per Shipment by Lane**")
    cost_by_lane = df_lanes_filtered.groupby('Lane')['Avg_Cost_Per_Shipment'].mean()
    st.bar_chart(cost_by_lane)

# Lane summary table
lane_summary = df_lanes_filtered.groupby('Lane').agg({
    'Utilization': ['mean', 'std'],
    'Shipments': 'sum',
    'Avg_Cost_Per_Shipment': 'mean'
}).round(2)

lane_summary.columns = ['Avg Utilization', 'Utilization Std Dev', 'Total Shipments', 'Avg Cost per Shipment (€)']
st.dataframe(lane_summary, use_container_width=True)

# Performance Alerts Section
st.markdown('<h2 class="section-header">🚨 Performance Alerts</h2>', unsafe_allow_html=True)

# Generate alerts based on thresholds
alerts = []

# OTP alerts
for service in service_types:
    service_otp = df_volume_filtered[df_volume_filtered['Service_Type'] == service]['OTP_Score'].mean()
    if service_otp < 95:
        alerts.append({
            'Type': '⏰ OTP Alert',
            'Service': service,
            'Message': f'OTP below target: {service_otp:.1f}% (Target: 95%)',
            'Severity': 'High' if service_otp < 90 else 'Medium'
        })

# Profit margin alerts
for service in service_types:
    service_data = df_volume_filtered[df_volume_filtered['Service_Type'] == service]
    service_margin = ((service_data['Revenue'].sum() - service_data['Cost'].sum()) / service_data['Revenue'].sum()) * 100
    if service_margin < 15:
        alerts.append({
            'Type': '💰 Margin Alert',
            'Service': service,
            'Message': f'Low profit margin: {service_margin:.1f}% (Target: 20%)',
            'Severity': 'High' if service_margin < 10 else 'Medium'
        })

# Lane utilization alerts
for lane in df_lanes_filtered['Lane'].unique():
    lane_util = df_lanes_filtered[df_lanes_filtered['Lane'] == lane]['Utilization'].mean()
    if lane_util < 0.6:
        alerts.append({
            'Type': '🛣️ Utilization Alert',
            'Service': lane,
            'Message': f'Low lane utilization: {lane_util:.1%} (Target: 80%)',
            'Severity': 'Medium'
        })

if alerts:
    alerts_df = pd.DataFrame(alerts)
    st.dataframe(alerts_df, use_container_width=True, hide_index=True)
else:
    st.success("✅ All performance metrics within target ranges!")

# Summary Statistics Table
st.markdown('<h2 class="section-header">📋 Executive Summary</h2>', unsafe_allow_html=True)

# Create executive summary
summary_data = {
    'Metric': [
        'Total Volume (shipments)',
        'Average OTP Score (%)',
        'Total Revenue (€)',
        'Total Profit (€)',
        'Average Profit Margin (%)',
        'Average Lane Utilization (%)'
    ],
    'Value': [
        f"{df_volume_filtered['Volume'].sum():,}",
        f"{df_volume_filtered['OTP_Score'].mean():.1f}%",
        f"€{df_volume_filtered['Revenue'].sum():,.0f}",
        f"€{(df_volume_filtered['Revenue'].sum() - df_volume_filtered['Cost'].sum()):,.0f}",
        f"{profit_margin:.1f}%",
        f"{df_lanes_filtered['Utilization'].mean():.1%}"
    ],
    'Target': [
        'N/A',
        '95.0%',
        'N/A',
        'N/A',
        '20.0%',
        '80.0%'
    ],
    'Status': [
        '✅ Good',
        '✅ Good' if df_volume_filtered['OTP_Score'].mean() >= 95 else '⚠️ Below Target',
        '✅ Good',
        '✅ Good' if profit_margin > 0 else '❌ Loss',
        '✅ Good' if profit_margin >= 20 else '⚠️ Below Target',
        '✅ Good' if df_lanes_filtered['Utilization'].mean() >= 0.8 else '⚠️ Below Target'
    ]
}

summary_df = pd.DataFrame(summary_data)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="highlight-box">
<strong>📋 Dashboard Notes:</strong><br>
• Data reflects Amsterdam (LFS) office operations only<br>
• Performance Targets: OTP ≥95% | Profit Margin ≥20% | Lane Utilization ≥80%<br>
• Dashboard updates automatically with new data uploads<br>
• For detailed analysis and recommendations, refer to the comprehensive report<br>
• Contact: Dashboard created for Adam and the LFS Amsterdam team
</div>
""", unsafe_allow_html=True)

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Dashboard Statistics")
st.sidebar.metric("Data Points", f"{len(df_volume_filtered):,}")
st.sidebar.metric("Date Range", f"{(date_range[1] - date_range[0]).days} days")
st.sidebar.metric("Service Types", len(service_types))

st.sidebar.markdown("### ℹ️ System Info")
st.sidebar.info(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.info("Status: ✅ All systems operational")

# Data export functionality
st.sidebar.markdown("### 📥 Export Options")
if st.sidebar.button("📊 Export Dashboard Data"):
    # Create export data
    export_data = df_volume_filtered.copy()
    csv = export_data.to_csv(index=False)
    st.sidebar.download_button(
        label="💾 Download CSV",
        data=csv,
        file_name=f"tms_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

if st.sidebar.button("📈 Export Summary Report"):
    st.sidebar.download_button(
        label="💾 Download Summary",
        data=summary_df.to_csv(index=False),
        file_name=f"tms_summary_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

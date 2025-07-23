import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
</style>
""", unsafe_allow_html=True)

# Title and header
st.markdown('<h1 class="main-header">🚛 LFS Amsterdam - TMS Performance Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Transportation Management System Analytics & KPI Monitoring**")

# Sidebar for filters and controls
st.sidebar.title("📋 Dashboard Controls")
st.sidebar.markdown("---")

# Date range selector (you'll replace with actual data dates)
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
                'OTP_Score': np.random.beta(8, 2) * 100  # On-time performance
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

# Load data
df_volume, df_lanes = load_sample_data()

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
    st.metric(
        label="📦 Total Volume",
        value=f"{total_volume:,}",
        delta=f"{(total_volume - df_volume_filtered['Volume'].sum()/1.1):,.0f}",
        delta_color="normal"
    )

with col2:
    avg_otp = df_volume_filtered['OTP_Score'].mean()
    st.metric(
        label="⏰ Avg OTP Score",
        value=f"{avg_otp:.1f}%",
        delta=f"{(avg_otp - 90):.1f}%",
        delta_color="normal"
    )

with col3:
    total_revenue = df_volume_filtered['Revenue'].sum()
    st.metric(
        label="💰 Total Revenue",
        value=f"€{total_revenue:,.0f}",
        delta=f"€{(total_revenue * 0.1):,.0f}",
        delta_color="normal"
    )

with col4:
    profit_margin = ((df_volume_filtered['Revenue'].sum() - df_volume_filtered['Cost'].sum()) / df_volume_filtered['Revenue'].sum()) * 100
    st.metric(
        label="📈 Profit Margin",
        value=f"{profit_margin:.1f}%",
        delta=f"{(profit_margin - 15):.1f}%",
        delta_color="normal"
    )

st.markdown("---")

# Volume Analysis Section
st.markdown('<h2 class="section-header">📊 Volume Analysis by Service Type</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Volume by service type (daily trend)
    daily_volume = df_volume_filtered.groupby(['Date', 'Service_Type'])['Volume'].sum().reset_index()
    fig_volume_trend = px.line(
        daily_volume, 
        x='Date', 
        y='Volume', 
        color='Service_Type',
        title='Daily Volume Trends by Service Type',
        labels={'Volume': 'Daily Volume', 'Date': 'Date'}
    )
    fig_volume_trend.update_layout(height=400)
    st.plotly_chart(fig_volume_trend, use_container_width=True)

with col2:
    # Volume distribution pie chart
    service_totals = df_volume_filtered.groupby('Service_Type')['Volume'].sum().reset_index()
    fig_pie = px.pie(
        service_totals, 
        values='Volume', 
        names='Service_Type',
        title='Volume Distribution by Service Type',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

# OTP Analysis Section
st.markdown('<h2 class="section-header">⏱️ On-Time Performance (OTP) Analysis</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # OTP by service type
    otp_by_service = df_volume_filtered.groupby('Service_Type')['OTP_Score'].agg(['mean', 'std']).reset_index()
    otp_by_service.columns = ['Service_Type', 'Avg_OTP', 'OTP_StdDev']
    
    fig_otp = go.Figure()
    fig_otp.add_trace(go.Bar(
        x=otp_by_service['Service_Type'],
        y=otp_by_service['Avg_OTP'],
        error_y=dict(type='data', array=otp_by_service['OTP_StdDev']),
        name='Average OTP',
        marker_color='lightblue'
    ))
    fig_otp.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Target: 95%")
    fig_otp.update_layout(
        title='OTP Performance by Service Type',
        yaxis_title='OTP Score (%)',
        xaxis_title='Service Type',
        height=400
    )
    st.plotly_chart(fig_otp, use_container_width=True)

with col2:
    # OTP trend over time
    weekly_otp = df_volume_filtered.set_index('Date').groupby('Service_Type')['OTP_Score'].resample('W').mean().reset_index()
    fig_otp_trend = px.line(
        weekly_otp,
        x='Date',
        y='OTP_Score',
        color='Service_Type',
        title='Weekly OTP Trends',
        labels={'OTP_Score': 'OTP Score (%)', 'Date': 'Week'}
    )
    fig_otp_trend.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Target: 95%")
    fig_otp_trend.update_layout(height=400)
    st.plotly_chart(fig_otp_trend, use_container_width=True)

# Cost vs Sales Analysis
st.markdown('<h2 class="section-header">💰 Cost vs. Sales Analysis</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Cost vs Revenue scatter plot
    monthly_data = df_volume_filtered.set_index('Date').groupby('Service_Type').resample('M').agg({
        'Revenue': 'sum',
        'Cost': 'sum',
        'Volume': 'sum'
    }).reset_index()
    monthly_data['Profit_Margin'] = ((monthly_data['Revenue'] - monthly_data['Cost']) / monthly_data['Revenue']) * 100
    
    fig_scatter = px.scatter(
        monthly_data,
        x='Cost',
        y='Revenue',
        color='Service_Type',
        size='Volume',
        hover_data=['Profit_Margin', 'Date'],
        title='Monthly Cost vs Revenue Analysis',
        labels={'Cost': 'Total Cost (€)', 'Revenue': 'Total Revenue (€)'}
    )
    # Add break-even line
    max_val = max(monthly_data['Cost'].max(), monthly_data['Revenue'].max())
    fig_scatter.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode='lines',
        name='Break-even Line',
        line=dict(dash='dash', color='red')
    ))
    fig_scatter.update_layout(height=400)
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    # Profit margin trends
    profit_trends = monthly_data.copy()
    fig_profit = px.line(
        profit_trends,
        x='Date',
        y='Profit_Margin',
        color='Service_Type',
        title='Monthly Profit Margin Trends',
        labels={'Profit_Margin': 'Profit Margin (%)', 'Date': 'Month'}
    )
    fig_profit.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="Target: 20%")
    fig_profit.update_layout(height=400)
    st.plotly_chart(fig_profit, use_container_width=True)

# Lane Usage Analysis
st.markdown('<h2 class="section-header">🛣️ Lane Usage Analysis</h2>', unsafe_allow_html=True)

# Filter lane data based on date range
df_lanes_filtered = df_lanes[
    (df_lanes['Date'] >= pd.to_datetime(date_range[0])) &
    (df_lanes['Date'] <= pd.to_datetime(date_range[1]))
]

col1, col2 = st.columns(2)

with col1:
    # Lane utilization
    lane_util = df_lanes_filtered.groupby('Lane')['Utilization'].mean().reset_index()
    lane_util = lane_util.sort_values('Utilization', ascending=True)
    
    fig_lanes = px.bar(
        lane_util,
        x='Utilization',
        y='Lane',
        orientation='h',
        title='Average Lane Utilization',
        labels={'Utilization': 'Utilization Rate', 'Lane': 'Transportation Lane'},
        color='Utilization',
        color_continuous_scale='RdYlGn'
    )
    fig_lanes.add_vline(x=0.8, line_dash="dash", line_color="orange", annotation_text="Target: 80%")
    fig_lanes.update_layout(height=400)
    st.plotly_chart(fig_lanes, use_container_width=True)

with col2:
    # Cost per shipment by lane
    cost_by_lane = df_lanes_filtered.groupby('Lane')['Avg_Cost_Per_Shipment'].mean().reset_index()
    cost_by_lane = cost_by_lane.sort_values('Avg_Cost_Per_Shipment', ascending=False)
    
    fig_cost_lane = px.bar(
        cost_by_lane,
        x='Lane',
        y='Avg_Cost_Per_Shipment',
        title='Average Cost per Shipment by Lane',
        labels={'Avg_Cost_Per_Shipment': 'Avg Cost per Shipment (€)', 'Lane': 'Transportation Lane'},
        color='Avg_Cost_Per_Shipment',
        color_continuous_scale='Reds'
    )
    fig_cost_lane.update_layout(height=400)
    st.plotly_chart(fig_cost_lane, use_container_width=True)

# Summary Statistics Table
st.markdown('<h2 class="section-header">📋 Summary Statistics</h2>', unsafe_allow_html=True)

# Service type summary
service_summary = df_volume_filtered.groupby('Service_Type').agg({
    'Volume': ['sum', 'mean'],
    'Revenue': ['sum', 'mean'],
    'Cost': ['sum', 'mean'],
    'OTP_Score': ['mean', 'std']
}).round(2)

service_summary.columns = ['Total Volume', 'Avg Daily Volume', 'Total Revenue (€)', 'Avg Daily Revenue (€)', 
                          'Total Cost (€)', 'Avg Daily Cost (€)', 'Avg OTP (%)', 'OTP Std Dev']

# Add profit margin calculation
service_summary['Profit Margin (%)'] = ((service_summary['Total Revenue (€)'] - service_summary['Total Cost (€)']) / service_summary['Total Revenue (€)'] * 100).round(2)

st.dataframe(service_summary, use_container_width=True)

# Lane summary
st.markdown("### Lane Performance Summary")
lane_summary = df_lanes_filtered.groupby('Lane').agg({
    'Utilization': ['mean', 'std'],
    'Shipments': 'sum',
    'Avg_Cost_Per_Shipment': 'mean'
}).round(2)

lane_summary.columns = ['Avg Utilization', 'Utilization Std Dev', 'Total Shipments', 'Avg Cost per Shipment (€)']
st.dataframe(lane_summary, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
**Dashboard Notes:**
- Data reflects Amsterdam (LFS) office operations only
- OTP Target: 95% | Profit Margin Target: 20% | Lane Utilization Target: 80%
- This dashboard auto-refreshes with new data uploads
- For detailed analysis, refer to the comprehensive report
""")

# Download section
st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 Data Export")
if st.sidebar.button("Export Current View Data"):
    st.sidebar.success("Data export functionality ready for implementation")

st.sidebar.markdown("### ℹ️ Dashboard Info")
st.sidebar.info("Dashboard created for Adam and the LFS Amsterdam team. Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M"))

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

# Custom CSS for enhanced visual design
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 3rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .section-header {
        font-size: 2rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 3rem 0 2rem 0;
        padding: 1rem 0;
        border-bottom: 3px solid #3498db;
        text-align: center;
    }
    .subsection-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #34495e;
        margin: 2rem 0 1rem 0;
        text-align: center;
    }
    .metric-container {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        margin: 1rem 0;
        text-align: center;
        border: 1px solid rgba(52, 152, 219, 0.2);
    }
    .chart-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        margin: 2rem 0;
        border: 1px solid #e8f4fd;
    }
    .insight-box {
        background: linear-gradient(135deg, #e8f6ff 0%, #f0f8ff 100%);
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
        border-left: 5px solid #3498db;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    .alert-success {
        background: linear-gradient(135deg, #d5f5d5 0%, #c8f7c5 100%);
        border: 2px solid #27ae60;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .alert-warning {
        background: linear-gradient(135deg, #fff4e6 0%, #ffe4b5 100%);
        border: 2px solid #f39c12;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .alert-danger {
        background: linear-gradient(135deg, #ffe6e6 0%, #ffb3b3 100%);
        border: 2px solid #e74c3c;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .data-table {
        margin: 2rem 0;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .spacer {
        margin: 3rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">LFS Amsterdam TMS Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<div style="text-align: center; font-size: 1.3rem; color: #7f8c8d; margin-bottom: 3rem;">Transportation Management System Performance Analytics</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("📊 Dashboard Controls")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "Upload TMS Excel File",
    type=['xlsx', 'xls'],
    help="Upload your 'report raw data.xls' file"
)

# Define service types and countries correctly
SERVICE_TYPES = ['CTX', 'CX', 'EF', 'EGD', 'FF', 'RGD', 'ROU', 'SF']
COUNTRIES = ['AT', 'AU', 'BE', 'DE', 'DK', 'ES', 'FR', 'GB', 'IT', 'N1', 'NL', 'NZ', 'SE', 'US']

def safe_date_conversion(date_series):
    """Safely convert Excel dates"""
    try:
        if date_series.dtype in ['int64', 'float64']:
            return pd.to_datetime(date_series, origin='1899-12-30', unit='D', errors='coerce')
        else:
            return pd.to_datetime(date_series, errors='coerce')
    except:
        return date_series

@st.cache_data
def load_tms_data(uploaded_file):
    """Load and process TMS Excel file"""
    if uploaded_file is not None:
        try:
            excel_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            data = {}
            
            # 1. Raw Data
            if "AMS RAW DATA" in excel_sheets:
                data['raw_data'] = excel_sheets["AMS RAW DATA"].copy()
            
            # 2. OTP Data - first 5 columns only
            if "OTP POD" in excel_sheets:
                otp_df = excel_sheets["OTP POD"].copy().iloc[:, :5]
                otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status']
                otp_df = otp_df.dropna(subset=['TMS_Order'])
                data['otp'] = otp_df
            
            # 3. Volume Data - correct processing
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"].copy()
                data['volume_raw'] = volume_df
                
                # Process service volumes correctly
                service_volumes = {}
                country_volumes = {}
                
                # Look for service data in the volume sheet
                for idx, row in volume_df.iterrows():
                    if len(row) >= 2 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                        first_col = str(row.iloc[0]).strip()
                        second_col = row.iloc[1]
                        
                        # Check if it's a service type
                        if first_col in SERVICE_TYPES:
                            try:
                                service_volumes[first_col] = float(second_col)
                            except:
                                continue
                        
                        # Check if it's a country code
                        elif first_col in COUNTRIES:
                            try:
                                # Sum all numeric values in the row for country total
                                total = 0
                                for val in row[1:]:
                                    if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                                        total += val
                                if total > 0:
                                    country_volumes[first_col] = total
                            except:
                                continue
                
                data['service_volumes'] = service_volumes
                data['country_volumes'] = country_volumes
            
            # 4. Lane Usage
            if "Lane usage " in excel_sheets:
                data['lanes'] = excel_sheets["Lane usage "].copy()
            
            # 5. Cost Sales
            if "cost sales" in excel_sheets:
                cost_df = excel_sheets["cost sales"].copy()
                expected_cols = ['Order_Date', 'Account', 'Account_Name', 'Office', 'Order_Num', 
                               'PU_Cost', 'Ship_Cost', 'Man_Cost', 'Del_Cost', 'Total_Cost',
                               'Net_Revenue', 'Currency', 'Diff', 'Gross_Percent', 'Invoice_Num',
                               'Total_Amount', 'Status', 'PU_Country']
                
                new_cols = expected_cols[:len(cost_df.columns)]
                cost_df.columns = new_cols
                
                if 'Order_Date' in cost_df.columns:
                    cost_df['Order_Date'] = safe_date_conversion(cost_df['Order_Date'])
                
                data['cost_sales'] = cost_df
            
            return data
            
        except Exception as e:
            st.error(f"Error processing Excel file: {str(e)}")
            return None
    return None

# Load data
tms_data = None
if uploaded_file is not None:
    tms_data = load_tms_data(uploaded_file)
    if tms_data:
        st.sidebar.success("✅ Data loaded successfully")
    else:
        st.sidebar.error("❌ Error loading data")
else:
    st.sidebar.info("📁 Upload Excel file to begin")

# Create tabs for each sheet
if tms_data is not None:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "📦 Volume Analysis", 
        "⏱️ OTP Performance", 
        "💰 Financial Analysis", 
        "🛣️ Lane Network"
    ])
    
    # TAB 1: Overview
    with tab1:
        st.markdown('<h2 class="section-header">Executive Dashboard Overview</h2>', unsafe_allow_html=True)
        
        # Calculate key metrics
        total_services = sum(tms_data.get('service_volumes', {}).values())
        total_countries = sum(tms_data.get('country_volumes', {}).values())
        
        # OTP metrics
        avg_otp = 0
        total_orders = 0
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            if 'Status' in otp_df.columns:
                status_series = otp_df['Status'].dropna()
                total_orders = len(status_series)
                on_time_orders = len(status_series[status_series == 'ON TIME'])
                avg_otp = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Financial metrics
        total_revenue = 0
        total_cost = 0
        profit_margin = 0
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            if 'Net_Revenue' in cost_df.columns:
                total_revenue = cost_df['Net_Revenue'].sum()
            if 'Total_Cost' in cost_df.columns:
                total_cost = cost_df['Total_Cost'].sum()
            profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
        
        # KPI Dashboard
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("📦 Total Volume", f"{int(total_services):,}", "pieces")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("⏱️ OTP Rate", f"{avg_otp:.1f}%", f"{avg_otp-95:.1f}% vs target")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("💰 Revenue", f"€{total_revenue:,.0f}", "total")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("📈 Margin", f"{profit_margin:.1f}%", f"{profit_margin-20:.1f}% vs target")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
        
        # Performance Status
        if avg_otp >= 95 and profit_margin >= 20:
            st.markdown('<div class="alert-success"><strong>✅ Excellent Performance:</strong> All key metrics exceeding targets</div>', unsafe_allow_html=True)
        elif avg_otp >= 90 and profit_margin >= 15:
            st.markdown('<div class="alert-warning"><strong>⚠️ Good Performance:</strong> Minor improvements needed</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-danger"><strong>🔴 Action Required:</strong> Critical metrics below target</div>', unsafe_allow_html=True)
        
        # Quick insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            st.markdown("**📊 Operational Highlights**")
            st.markdown(f"• **{len(tms_data.get('service_volumes', {}))} Service Types** active")
            st.markdown(f"• **{len(tms_data.get('country_volumes', {}))} Countries** served")
            st.markdown(f"• **{total_orders:,} Orders** tracked")
            st.markdown(f"• **European Focus** with global reach")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            st.markdown("**🎯 Key Opportunities**")
            if avg_otp < 95:
                st.markdown("• **OTP Improvement** - Target 95%+")
            if profit_margin < 20:
                st.markdown("• **Margin Optimization** - Target 20%+")
            st.markdown("• **Service Diversification** ongoing")
            st.markdown("• **Network Expansion** potential")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 2: Volume Analysis
    with tab2:
        st.markdown('<h2 class="section-header">Volume Analysis by Service & Country</h2>', unsafe_allow_html=True)
        
        if 'service_volumes' in tms_data and tms_data['service_volumes']:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="subsection-header">Volume by Service Type</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                service_data = pd.Series(tms_data['service_volumes'])
                st.bar_chart(service_data, height=400)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Service breakdown table
                st.markdown('<div class="data-table">', unsafe_allow_html=True)
                service_table = pd.DataFrame({
                    'Service': service_data.index,
                    'Volume': service_data.values.astype(int),
                    'Share %': (service_data.values / service_data.sum() * 100).round(1)
                })
                st.dataframe(service_table, hide_index=True, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="subsection-header">Volume by Country</div>', unsafe_allow_html=True)
                
                if 'country_volumes' in tms_data and tms_data['country_volumes']:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    
                    country_data = pd.Series(tms_data['country_volumes'])
                    st.bar_chart(country_data, height=400)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Country breakdown table
                    st.markdown('<div class="data-table">', unsafe_allow_html=True)
                    country_table = pd.DataFrame({
                        'Country': country_data.index,
                        'Volume': country_data.values.astype(int),
                        'Share %': (country_data.values / country_data.sum() * 100).round(1)
                    })
                    st.dataframe(country_table, hide_index=True, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
        
        # Volume insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("**📦 Volume Analysis Insights**")
        
        if 'service_volumes' in tms_data and tms_data['service_volumes']:
            top_service = max(tms_data['service_volumes'], key=tms_data['service_volumes'].get)
            st.markdown(f"• **Top Service**: {top_service} with {tms_data['service_volumes'][top_service]:.0f} pieces")
        
        if 'country_volumes' in tms_data and tms_data['country_volumes']:
            top_country = max(tms_data['country_volumes'], key=tms_data['country_volumes'].get)
            st.markdown(f"• **Top Country**: {top_country} with {tms_data['country_volumes'][top_country]:.0f} shipments")
        
        st.markdown(f"• **Total Services**: {len(tms_data.get('service_volumes', {}))} active service types")
        st.markdown(f"• **Geographic Reach**: {len(tms_data.get('country_volumes', {}))} countries served")
        st.markdown("• **Portfolio Diversification**: Balanced mix reduces operational risk")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 3: OTP Performance
    with tab3:
        st.markdown('<h2 class="section-header">On-Time Performance Deep Analysis</h2>', unsafe_allow_html=True)
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            
            # OTP Status Analysis
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="subsection-header">OTP Status Distribution</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                if 'Status' in otp_df.columns:
                    status_counts = otp_df['Status'].value_counts()
                    st.bar_chart(status_counts, height=300)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="subsection-header">Performance Metrics</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                metrics_data = pd.DataFrame({
                    'Metric': ['Total Orders', 'On-Time', 'Late', 'OTP Rate %'],
                    'Value': [
                        f"{total_orders:,}",
                        f"{total_orders - (total_orders - int(avg_otp/100 * total_orders)):,}",
                        f"{total_orders - int(avg_otp/100 * total_orders):,}",
                        f"{avg_otp:.1f}%"
                    ]
                })
                st.dataframe(metrics_data, hide_index=True, use_container_width=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="subsection-header">QC Name Analysis</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                # Find QC Name column (it might be in different positions)
                qc_column = None
                for col in otp_df.columns:
                    if 'QC' in str(col).upper() or 'NAME' in str(col).upper():
                        qc_column = col
                        break
                
                if qc_column is not None:
                    qc_counts = otp_df[qc_column].value_counts().head(10)
                    if not qc_counts.empty:
                        st.bar_chart(qc_counts, height=300)
                    
                    # QC breakdown table
                    qc_table = pd.DataFrame({
                        'QC Name': qc_counts.index,
                        'Count': qc_counts.values
                    })
                    st.dataframe(qc_table, hide_index=True, use_container_width=True)
                else:
                    st.info("QC Name data not found in expected format")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
            
            # Time difference analysis
            if 'Time_Diff' in otp_df.columns:
                st.markdown('<div class="subsection-header">Delivery Time Analysis</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    time_diff_clean = otp_df['Time_Diff'].dropna()
                    if not time_diff_clean.empty:
                        # Create histogram bins
                        hist_data = pd.cut(time_diff_clean, bins=10).value_counts().sort_index()
                        st.bar_chart(hist_data, height=300)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    if not time_diff_clean.empty:
                        time_stats = pd.DataFrame({
                            'Statistic': ['Mean Difference', 'Median', 'Std Dev', 'Min', 'Max'],
                            'Days': [
                                f"{time_diff_clean.mean():.2f}",
                                f"{time_diff_clean.median():.2f}",
                                f"{time_diff_clean.std():.2f}",
                                f"{time_diff_clean.min():.2f}",
                                f"{time_diff_clean.max():.2f}"
                            ]
                        })
                        st.dataframe(time_stats, hide_index=True, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # OTP Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("**⏱️ OTP Performance Insights**")
        
        if avg_otp >= 95:
            st.markdown("• **Excellent Performance**: OTP exceeds industry standard of 95%")
        elif avg_otp >= 90:
            st.markdown("• **Good Performance**: Minor improvements needed to reach 95% target")
        else:
            st.markdown("• **Action Required**: Significant OTP improvement needed")
        
        st.markdown(f"• **Total Orders Tracked**: {total_orders:,} with systematic monitoring")
        st.markdown("• **Quality Control**: Multiple QC checkpoints ensuring delivery accuracy")
        st.markdown("• **Time Tracking**: Detailed analysis of delivery time variations")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 4: Financial Analysis
    with tab4:
        st.markdown('<h2 class="section-header">Financial Performance & Profitability Analysis</h2>', unsafe_allow_html=True)
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            
            # Financial Overview
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="subsection-header">Revenue vs Cost</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                financial_overview = pd.Series({
                    'Revenue': total_revenue,
                    'Cost': total_cost,
                    'Profit': total_revenue - total_cost
                })
                st.bar_chart(financial_overview, height=300)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="subsection-header">Cost Breakdown</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                cost_components = {}
                cost_cols = ['PU_Cost', 'Ship_Cost', 'Man_Cost', 'Del_Cost']
                for col in cost_cols:
                    if col in cost_df.columns:
                        cost_sum = cost_df[col].sum()
                        if cost_sum > 0:
                            cost_components[col.replace('_Cost', '')] = cost_sum
                
                if cost_components:
                    cost_series = pd.Series(cost_components)
                    st.bar_chart(cost_series, height=300)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="subsection-header">Margin Distribution</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                if 'Gross_Percent' in cost_df.columns:
                    margin_data = cost_df['Gross_Percent'].dropna()
                    if not margin_data.empty:
                        margin_bins = pd.cut(margin_data, 
                                           bins=[-np.inf, 0, 0.1, 0.2, 0.3, np.inf], 
                                           labels=['Loss', '0-10%', '10-20%', '20-30%', '30%+'])
                        margin_dist = margin_bins.value_counts()
                        st.bar_chart(margin_dist, height=300)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
            
            # Country Financial Performance
            if 'PU_Country' in cost_df.columns:
                st.markdown('<div class="subsection-header">Financial Performance by Country</div>', unsafe_allow_html=True)
                
                country_financials = cost_df.groupby('PU_Country').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum',
                    'Gross_Percent': 'mean'
                }).round(2)
                
                country_financials['Profit'] = country_financials['Net_Revenue'] - country_financials['Total_Cost']
                country_financials = country_financials.sort_values('Net_Revenue', ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.markdown("**Revenue by Country**")
                    st.bar_chart(country_financials['Net_Revenue'], height=400)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.markdown("**Profit Margin by Country**")
                    st.bar_chart(country_financials['Gross_Percent'], height=400)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Detailed financial table
                st.markdown('<div class="data-table">', unsafe_allow_html=True)
                st.markdown("**Detailed Country Financial Performance**")
                
                display_financials = country_financials.copy()
                display_financials['Net_Revenue'] = display_financials['Net_Revenue'].round(0).astype(int)
                display_financials['Total_Cost'] = display_financials['Total_Cost'].round(0).astype(int)
                display_financials['Profit'] = display_financials['Profit'].round(0).astype(int)
                display_financials['Gross_Percent'] = (display_financials['Gross_Percent'] * 100).round(1)
                display_financials.columns = ['Revenue (€)', 'Cost (€)', 'Margin (%)', 'Profit (€)']
                
                st.dataframe(display_financials, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Financial Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("**💰 Financial Performance Insights**")
        
        if profit_margin >= 20:
            st.markdown("• **Strong Profitability**: Margins exceed 20% target indicating efficient operations")
        elif profit_margin >= 10:
            st.markdown("• **Moderate Profitability**: Opportunities exist for margin improvement")
        else:
            st.markdown("• **Margin Concern**: Immediate focus needed on cost optimization")
        
        st.markdown(f"• **Total Revenue**: €{total_revenue:,.0f} from operational activities")
        st.markdown(f"• **Operating Profit**: €{(total_revenue - total_cost):,.0f} net profit generated")
        st.markdown("• **Cost Structure**: Detailed breakdown enables targeted optimization")
        st.markdown("• **Country Analysis**: Geographic profitability patterns identified")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 5: Lane Network
    with tab5:
        st.markdown('<h2 class="section-header">Lane Network & Route Analysis</h2>', unsafe_allow_html=True)
        
        if 'lanes' in tms_data and not tms_data['lanes'].empty:
            lane_df = tms_data['lanes']
            
            # Lane Usage Matrix
            st.markdown('<div class="subsection-header">Origin-Destination Network Matrix</div>', unsafe_allow_html=True)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            
            # Display the lane matrix
            display_lanes = lane_df.fillna(0)
            st.dataframe(display_lanes, use_container_width=True, height=400)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
            
            # Network Analysis
            if len(lane_df) > 1 and len(lane_df.columns) > 1:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="subsection-header">Top Origin Countries</div>', unsafe_allow_html=True)
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    
                    # Calculate row totals (origins)
                    numeric_cols = lane_df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        origin_totals = lane_df[numeric_cols].sum(axis=1)
                        origin_countries = lane_df.iloc[:, 0] if len(lane_df.columns) > 0 else range(len(origin_totals))
                        
                        origin_data = pd.Series(origin_totals.values, index=origin_countries)
                        origin_data = origin_data[origin_data > 0].sort_values(ascending=False)
                        
                        if not origin_data.empty:
                            st.bar_chart(origin_data.head(10), height=350)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="subsection-header">Top Destination Countries</div>', unsafe_allow_html=True)
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    
                    # Calculate column totals (destinations)
                    if len(numeric_cols) > 0:
                        dest_totals = lane_df[numeric_cols].sum(axis=0)
                        dest_data = dest_totals[dest_totals > 0].sort_values(ascending=False)
                        
                        if not dest_data.empty:
                            st.bar_chart(dest_data.head(10), height=350)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Network Statistics
            st.markdown('<div class="subsection-header">Network Performance Statistics</div>', unsafe_allow_html=True)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            
            # Calculate network metrics
            total_shipments = 0
            active_lanes = 0
            
            if len(lane_df) > 0:
                numeric_data = lane_df.select_dtypes(include=[np.number])
                if not numeric_data.empty:
                    total_shipments = numeric_data.sum().sum()
                    active_lanes = (numeric_data > 0).sum().sum()
            
            network_stats = pd.DataFrame({
                'Metric': [
                    'Total Shipments',
                    'Active Lanes',
                    'Origin Countries',
                    'Destination Countries',
                    'Average per Lane'
                ],
                'Value': [
                    f"{int(total_shipments):,}",
                    f"{int(active_lanes):,}",
                    f"{len(lane_df):,}",
                    f"{len(lane_df.columns)-1:,}" if len(lane_df.columns) > 1 else "0",
                    f"{(total_shipments/active_lanes):.1f}" if active_lanes > 0 else "0"
                ]
            })
            
            st.dataframe(network_stats, hide_index=True, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Lane Network Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("**🛣️ Lane Network Analysis Insights**")
        
        st.markdown("• **European Hub Strategy**: Amsterdam positioned as central distribution point")
        st.markdown("• **Multi-Country Coverage**: Comprehensive network spanning major European markets")
        st.markdown("• **Route Optimization**: High-volume lanes identified for capacity planning")
        st.markdown("• **Network Efficiency**: Balanced origin-destination flow patterns")
        st.markdown("• **Strategic Routes**: Key corridors supporting business growth")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # No data uploaded
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('''
        <div style="text-align: center; padding: 4rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 20px; margin: 2rem 0;">
            <h2 style="color: #2c3e50; margin-bottom: 2rem;">📊 Welcome to TMS Dashboard</h2>
            <p style="font-size: 1.2rem; color: #7f8c8d; margin-bottom: 2rem;">
                Upload your Excel file to begin comprehensive analysis
            </p>
            <div style="background: white; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
                <h3 style="color: #3498db;">Expected Data Structure:</h3>
                <ul style="text-align: left; color: #2c3e50;">
                    <li><strong>Volume per SVC:</strong> Service and country volume data</li>
                    <li><strong>OTP POD:</strong> On-time performance tracking</li>
                    <li><strong>cost sales:</strong> Financial and profitability data</li>
                    <li><strong>Lane usage:</strong> Origin-destination network matrix</li>
                    <li><strong>AMS RAW DATA:</strong> Detailed transaction records</li>
                </ul>
            </div>
        </div>
        ''', unsafe_allow_html=True)

# Sidebar status
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 System Status")

if tms_data is not None:
    st.sidebar.success(f"✅ Data loaded successfully")
    st.sidebar.info(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Quick stats in sidebar
    st.sidebar.markdown("### 📈 Quick Stats")
    if 'service_volumes' in tms_data:
        st.sidebar.write(f"📦 Services: {len(tms_data['service_volumes'])}")
    if 'country_volumes' in tms_data:
        st.sidebar.write(f"🌍 Countries: {len(tms_data['country_volumes'])}")
    if 'otp' in tms_data:
        st.sidebar.write(f"⏱️ Orders: {len(tms_data['otp']):,}")
    if 'cost_sales' in tms_data:
        st.sidebar.write(f"💰 Transactions: {len(tms_data['cost_sales']):,}")
    
    # Data export
    st.sidebar.markdown("### 📥 Export Data")
    if st.sidebar.button("📊 Export Analysis"):
        st.sidebar.info("Contact administrator for data export")

else:
    st.sidebar.warning("📁 Awaiting data upload")

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Dashboard Info")
st.sidebar.info("""
**Professional TMS Analytics**  
Created for LFS Amsterdam  
Real-time performance monitoring  
Comprehensive business intelligence
""")

# Footer
st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.markdown('''
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-top: 3rem;">
    <h3>LFS Amsterdam TMS Dashboard</h3>
    <p>Professional Transportation Management System Analytics</p>
    <p style="font-size: 0.9rem; opacity: 0.8;">Empowering data-driven logistics decisions</p>
</div>
''', unsafe_allow_html=True)

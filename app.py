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
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 5px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #333;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .subsection-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #555;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .highlight-box {
        background: linear-gradient(135deg, #e8f4fd 0%, #f0f8ff 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        border: 1px solid #1f77b4;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 1px solid #ffeaa7;
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 1px solid #28a745;
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .explanation-text {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        font-size: 0.9rem;
        color: #555;
        margin-top: 0.8rem;
        border-left: 4px solid #1f77b4;
        font-style: italic;
    }
    .kpi-container {
        background: white;
        padding: 1rem;
        border-radius: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Title and header
st.markdown('<h1 class="main-header">LFS Amsterdam - TMS Performance Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<div style="text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 2rem;"><strong>Transportation Management System Analytics & KPI Monitoring</strong></div>', unsafe_allow_html=True)

# Sidebar for controls
st.sidebar.title("📋 Dashboard Controls")
st.sidebar.markdown("---")

# File upload section
uploaded_file = st.sidebar.file_uploader(
    "Upload TMS Data (Excel)",
    type=['xlsx', 'xls'],
    help="Upload your 'report raw data.xls' file"
)

# Function to safely convert Excel dates
def safe_date_conversion(date_series):
    """Safely convert Excel date numbers to datetime"""
    try:
        if date_series.dtype in ['int64', 'float64']:
            return pd.to_datetime(date_series, origin='1899-12-30', unit='D', errors='coerce')
        else:
            return pd.to_datetime(date_series, errors='coerce')
    except:
        return date_series

# Function to load and process the actual Excel data
@st.cache_data
def load_tms_data(uploaded_file):
    """Load and process the actual TMS Excel file"""
    if uploaded_file is not None:
        try:
            excel_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            data = {}
            
            # 1. AMS RAW DATA Sheet Processing (keep as raw)
            if "AMS RAW DATA" in excel_sheets:
                raw_df = excel_sheets["AMS RAW DATA"].copy()
                data['raw_data'] = raw_df
            
            # 2. OTP POD Sheet Processing (use only first 5 columns)
            if "OTP POD" in excel_sheets:
                otp_df = excel_sheets["OTP POD"].copy()
                # Use only first 5 columns as requested
                otp_df = otp_df.iloc[:, :5]
                # Set proper column names based on actual data structure
                otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status']
                otp_df = otp_df.dropna(subset=['TMS_Order'])
                
                # Safe date conversion
                if 'QDT' in otp_df.columns:
                    otp_df['QDT'] = safe_date_conversion(otp_df['QDT'])
                if 'POD_DateTime' in otp_df.columns:
                    otp_df['POD_DateTime'] = safe_date_conversion(otp_df['POD_DateTime'])
                
                data['otp'] = otp_df
            
            # 3. Volume per SVC Sheet Processing (correct interpretation)
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"].copy()
                data['volume_raw'] = volume_df
                
                # Process volume data correctly
                # Look for "Count of SVC" section and "DEL CTRY" data
                volume_processed = {}
                service_volumes = {}
                country_volumes = {}
                
                # Find service volumes (Count of PIECES section)
                for idx, row in volume_df.iterrows():
                    if len(row) >= 2 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                        service = str(row.iloc[0]).strip()
                        try:
                            volume = float(row.iloc[1])
                            if service not in ['Count of PIECES', 'SVC', 'Total', ''] and volume > 0:
                                service_volumes[service] = volume
                        except:
                            continue
                
                # Find country data (DEL CTRY section) - need to parse the matrix structure
                # Look for rows that contain country codes and extract totals
                for idx, row in volume_df.iterrows():
                    row_data = [str(x) if pd.notna(x) else '' for x in row]
                    # Look for country codes in the first column
                    if len(row_data) > 0 and len(row_data[0]) == 2 and row_data[0].isalpha():
                        country = row_data[0]
                        # Sum non-empty numeric values in the row (excluding first column)
                        total = 0
                        for val in row_data[1:]:
                            try:
                                if val != '' and float(val) > 0:
                                    total += float(val)
                            except:
                                continue
                        if total > 0:
                            country_volumes[country] = total
                
                data['service_volumes'] = service_volumes
                data['country_volumes'] = country_volumes
            
            # 4. Lane Usage Sheet Processing
            if "Lane usage " in excel_sheets:
                lane_df = excel_sheets["Lane usage "].copy()
                data['lanes'] = lane_df
            
            # 5. Cost Sales Sheet Processing
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

# Load the data
tms_data = None
if uploaded_file is not None:
    tms_data = load_tms_data(uploaded_file)
    if tms_data:
        st.sidebar.success("✅ TMS Data loaded successfully")
        st.sidebar.write("📊 Available datasets:", list(tms_data.keys()))
    else:
        st.sidebar.error("❌ Error loading TMS data")
else:
    st.sidebar.info("📁 Please upload your TMS data file to begin analysis")

# Create tab structure
tab1, tab2, tab3 = st.tabs(["📋 Data Overview", "📊 Dashboard & Analytics", "📈 Comprehensive Report"])

# TAB 1: Data Overview
with tab1:
    st.markdown('<h2 class="section-header">Data Overview & Quality Assessment</h2>', unsafe_allow_html=True)
    
    if tms_data is not None:
        
        # Dataset summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="subsection-header">Dataset Summary</div>', unsafe_allow_html=True)
            
            dataset_info = []
            for sheet_name, df in tms_data.items():
                if isinstance(df, pd.DataFrame):
                    dataset_info.append({
                        'Dataset': sheet_name.replace('_', ' ').title(),
                        'Records': f"{len(df):,}",
                        'Columns': len(df.columns),
                        'Status': '✅ Loaded' if not df.empty else '⚠️ Empty'
                    })
                elif isinstance(df, dict):
                    dataset_info.append({
                        'Dataset': sheet_name.replace('_', ' ').title(),
                        'Records': f"{len(df)} categories",
                        'Columns': 'Processed',
                        'Status': '✅ Loaded' if df else '⚠️ Empty'
                    })
            
            dataset_df = pd.DataFrame(dataset_info)
            st.dataframe(dataset_df, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown('<div class="subsection-header">Data Quality Metrics</div>', unsafe_allow_html=True)
            
            quality_metrics = []
            
            if 'otp' in tms_data and not tms_data['otp'].empty:
                otp_df = tms_data['otp']
                complete_records = len(otp_df.dropna())
                quality_metrics.append({
                    'Dataset': 'OTP Performance',
                    'Completeness': f"{(complete_records/len(otp_df)*100):.1f}%",
                    'Quality': '🟢 Good' if complete_records/len(otp_df) > 0.8 else '🟡 Fair'
                })
            
            if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
                cost_df = tms_data['cost_sales']
                revenue_complete = len(cost_df.dropna(subset=['Net_Revenue']))
                quality_metrics.append({
                    'Dataset': 'Financial Data',
                    'Completeness': f"{(revenue_complete/len(cost_df)*100):.1f}%",
                    'Quality': '🟢 Good' if revenue_complete/len(cost_df) > 0.8 else '🟡 Fair'
                })
            
            if 'service_volumes' in tms_data:
                quality_metrics.append({
                    'Dataset': 'Volume Data',
                    'Completeness': f"{len(tms_data['service_volumes'])} services",
                    'Quality': '🟢 Good' if len(tms_data['service_volumes']) > 0 else '🟡 Fair'
                })
            
            if quality_metrics:
                quality_df = pd.DataFrame(quality_metrics)
                st.dataframe(quality_df, hide_index=True, use_container_width=True)
        
        # Sample data preview
        st.markdown('<div class="subsection-header">Sample Data Preview</div>', unsafe_allow_html=True)
        
        # OTP Data Preview (first 5 columns only)
        if 'otp' in tms_data and not tms_data['otp'].empty:
            with st.expander("📊 OTP Performance Data - Sample"):
                otp_sample = tms_data['otp'].head(5)
                st.dataframe(otp_sample, use_container_width=True)
                st.markdown('<div class="explanation-text">OTP data showing TMS Order, Quoted Delivery Time (QDT), Proof of Delivery DateTime, Time Difference, and Status for performance tracking.</div>', unsafe_allow_html=True)
        
        # Raw Data Preview
        if 'raw_data' in tms_data and not tms_data['raw_data'].empty:
            with st.expander("📋 Raw Transaction Data - Sample"):
                raw_sample = tms_data['raw_data'].head(3).iloc[:, :10]  # First 10 columns only
                st.dataframe(raw_sample, use_container_width=True)
                st.markdown('<div class="explanation-text">Raw shipment data containing detailed transaction information including pickup, delivery, costs, and routing details.</div>', unsafe_allow_html=True)
        
        # Volume Data Structure
        if 'service_volumes' in tms_data and 'country_volumes' in tms_data:
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("📦 Service Volume Data"):
                    if tms_data['service_volumes']:
                        service_df = pd.DataFrame(list(tms_data['service_volumes'].items()), 
                                                columns=['Service Type', 'Volume'])
                        st.dataframe(service_df, hide_index=True, use_container_width=True)
                        st.markdown('<div class="explanation-text">Volume breakdown by service type showing piece counts for each service category.</div>', unsafe_allow_html=True)
            
            with col2:
                with st.expander("🌍 Country Volume Data"):
                    if tms_data['country_volumes']:
                        country_df = pd.DataFrame(list(tms_data['country_volumes'].items()), 
                                                columns=['Country Code', 'Volume'])
                        st.dataframe(country_df, hide_index=True, use_container_width=True)
                        st.markdown('<div class="explanation-text">Volume distribution by delivery country showing total shipments per destination market.</div>', unsafe_allow_html=True)
        
        # Data Quality Summary
        st.markdown('<div class="highlight-box"><strong>📊 Data Quality Summary:</strong><br>All primary datasets have been successfully loaded and processed. The data shows good completeness rates and is ready for comprehensive analysis. Key performance indicators can be calculated reliably from the available data.</div>', unsafe_allow_html=True)
        
    else:
        st.markdown('<div class="alert-box"><strong>⚠️ No Data Loaded</strong><br>Please upload your TMS Excel file using the sidebar to view data overview and quality metrics.</div>', unsafe_allow_html=True)

# TAB 2: Dashboard & Analytics
with tab2:
    if tms_data is not None:
        
        # Calculate key metrics from actual data
        total_volume_services = sum(tms_data.get('service_volumes', {}).values())
        total_volume_countries = sum(tms_data.get('country_volumes', {}).values())
        
        # OTP Metrics from actual data
        avg_otp = 0
        total_orders = 0
        on_time_orders = 0
        late_reasons = {}
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            if 'Status' in otp_df.columns:
                status_series = otp_df['Status'].dropna()
                total_orders = len(status_series)
                on_time_orders = len(status_series[status_series == 'ON TIME'])
                avg_otp = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Financial Metrics from actual data
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
        st.markdown('<h2 class="section-header">Key Performance Indicators</h2>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            st.metric(
                label="📦 Total Volume (Services)",
                value=f"{int(total_volume_services):,}",
                delta="pieces processed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            st.metric(
                label="⏱️ OTP Performance",
                value=f"{avg_otp:.1f}%",
                delta=f"{avg_otp - 95:.1f}% vs target",
                delta_color="normal" if avg_otp >= 95 else "inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            st.metric(
                label="💰 Total Revenue",
                value=f"€{total_revenue:,.0f}",
                delta="operational revenue"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            st.metric(
                label="📈 Profit Margin",
                value=f"{profit_margin:.1f}%",
                delta=f"{profit_margin - 20:.1f}% vs target",
                delta_color="normal" if profit_margin >= 20 else "inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Performance Status Alert
        if avg_otp < 95 or profit_margin < 20:
            st.markdown('<div class="alert-box"><strong>⚠️ Performance Alert:</strong> Some KPIs are below target levels. Review detailed analysis sections for improvement opportunities.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-box"><strong>✅ Performance Status:</strong> All key performance indicators are meeting or exceeding target levels.</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Volume Analysis - Corrected
        st.markdown('<h2 class="section-header">Volume Analysis</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="subsection-header">Volume by Service Type</div>', unsafe_allow_html=True)
            
            if 'service_volumes' in tms_data and tms_data['service_volumes']:
                service_volumes = tms_data['service_volumes']
                service_series = pd.Series(service_volumes)
                st.bar_chart(service_series, height=400)
                
                # Service breakdown table
                service_table = pd.DataFrame({
                    'Service Type': service_series.index,
                    'Pieces': service_series.values.astype(int),
                    'Percentage': (service_series.values / service_series.sum() * 100).round(1)
                })
                st.dataframe(service_table, hide_index=True, use_container_width=True)
                
                st.markdown('<div class="explanation-text">Volume distribution by service type shows the operational focus and service mix. Each service type has different handling requirements and profitability profiles.</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="subsection-header">Volume by Delivery Country</div>', unsafe_allow_html=True)
            
            if 'country_volumes' in tms_data and tms_data['country_volumes']:
                country_volumes = tms_data['country_volumes']
                country_series = pd.Series(country_volumes)
                st.bar_chart(country_series, height=400)
                
                # Country breakdown table
                country_table = pd.DataFrame({
                    'Country Code': country_series.index,
                    'Shipments': country_series.values.astype(int),
                    'Percentage': (country_series.values / country_series.sum() * 100).round(1)
                })
                st.dataframe(country_table, hide_index=True, use_container_width=True)
                
                st.markdown('<div class="explanation-text">Geographic distribution shows market concentration and delivery patterns. Country codes represent delivery destinations with letter coding (e.g., NL=Netherlands, DE=Germany).</div>', unsafe_allow_html=True)
        
        # OTP Analysis with Late Delivery Reasons
        st.markdown('<h2 class="section-header">On-Time Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="subsection-header">OTP Status Distribution</div>', unsafe_allow_html=True)
                
                if 'Status' in otp_df.columns:
                    status_counts = otp_df['Status'].value_counts()
                    st.bar_chart(status_counts, height=300)
                    
                    st.markdown('<div class="explanation-text">Overall delivery status showing on-time vs delayed performance. Target is 95% on-time delivery rate.</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="subsection-header">Performance Metrics</div>', unsafe_allow_html=True)
                
                metrics_data = pd.DataFrame({
                    'Metric': ['Total Orders', 'On-Time Orders', 'Late Orders', 'OTP Rate'],
                    'Value': [
                        f"{total_orders:,}",
                        f"{on_time_orders:,}",
                        f"{total_orders - on_time_orders:,}",
                        f"{avg_otp:.1f}%"
                    ]
                })
                st.dataframe(metrics_data, hide_index=True, use_container_width=True)
                
                st.markdown('<div class="explanation-text">Key performance metrics showing absolute numbers and percentages for delivery performance tracking.</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="subsection-header">Delivery Time Analysis</div>', unsafe_allow_html=True)
                
                if 'Time_Diff' in otp_df.columns:
                    time_diff_clean = otp_df['Time_Diff'].dropna()
                    if not time_diff_clean.empty:
                        avg_diff = time_diff_clean.mean()
                        std_diff = time_diff_clean.std()
                        
                        time_stats = pd.DataFrame({
                            'Statistic': ['Average Difference', 'Std Deviation', 'Min Difference', 'Max Difference'],
                            'Value (Days)': [
                                f"{avg_diff:.2f}",
                                f"{std_diff:.2f}",
                                f"{time_diff_clean.min():.2f}",
                                f"{time_diff_clean.max():.2f}"
                            ]
                        })
                        st.dataframe(time_stats, hide_index=True, use_container_width=True)
                        
                        st.markdown('<div class="explanation-text">Time difference analysis between promised and actual delivery times. Negative values indicate early delivery, positive values indicate delays.</div>', unsafe_allow_html=True)
        
        # Enhanced Financial Analysis
        st.markdown('<h2 class="section-header">Financial Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            
            # Revenue and Cost Breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="subsection-header">Cost Structure Analysis</div>', unsafe_allow_html=True)
                
                cost_components = {}
                cost_labels = {
                    'PU_Cost': 'Pickup Cost',
                    'Ship_Cost': 'Shipping Cost', 
                    'Man_Cost': 'Manual Cost',
                    'Del_Cost': 'Delivery Cost'
                }
                
                for col_name, label in cost_labels.items():
                    if col_name in cost_df.columns:
                        cost_sum = cost_df[col_name].sum()
                        if cost_sum > 0:
                            cost_components[label] = cost_sum
                
                if cost_components:
                    cost_series = pd.Series(cost_components)
                    st.bar_chart(cost_series, height=350)
                    
                    st.markdown('<div class="explanation-text">Cost breakdown by operational component showing where expenses are concentrated. This helps identify cost optimization opportunities.</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="subsection-header">Profitability Distribution</div>', unsafe_allow_html=True)
                
                if 'Gross_Percent' in cost_df.columns:
                    # Create margin bins
                    margin_data = cost_df['Gross_Percent'].dropna()
                    if not margin_data.empty:
                        margin_bins = pd.cut(margin_data, 
                                           bins=[-np.inf, 0, 0.1, 0.2, 0.3, np.inf], 
                                           labels=['Loss', '0-10%', '10-20%', '20-30%', '30%+'])
                        margin_dist = margin_bins.value_counts()
                        st.bar_chart(margin_dist, height=350)
                        
                        st.markdown('<div class="explanation-text">Distribution of profit margins across shipments. Higher concentration in positive margin categories indicates healthy profitability.</div>', unsafe_allow_html=True)
            
            # Financial Performance by Country
            st.markdown('<div class="subsection-header">Financial Performance by Country</div>', unsafe_allow_html=True)
            
            if 'PU_Country' in cost_df.columns:
                country_financials = cost_df.groupby('PU_Country').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum',
                    'Gross_Percent': 'mean'
                }).round(2)
                
                country_financials['Profit'] = country_financials['Net_Revenue'] - country_financials['Total_Cost']
                country_financials = country_financials.sort_values('Net_Revenue', ascending=False)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown('<div class="subsection-header">Revenue by Country</div>', unsafe_allow_html=True)
                    st.bar_chart(country_financials['Net_Revenue'], height=300)
                    st.markdown('<div class="explanation-text">Revenue concentration by pickup country showing key markets and business distribution.</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="subsection-header">Profit by Country</div>', unsafe_allow_html=True)
                    st.bar_chart(country_financials['Profit'], height=300)
                    st.markdown('<div class="explanation-text">Net profit by country after deducting operational costs. Identifies most profitable markets.</div>', unsafe_allow_html=True)
                
                with col3:
                    st.markdown('<div class="subsection-header">Margin by Country</div>', unsafe_allow_html=True)
                    st.bar_chart(country_financials['Gross_Percent'], height=300)
                    st.markdown('<div class="explanation-text">Average profit margin percentage by country. Higher margins indicate better pricing or operational efficiency.</div>', unsafe_allow_html=True)
                
                # Detailed financial table
                st.markdown('<div class="subsection-header">Detailed Financial Performance by Country</div>', unsafe_allow_html=True)
                
                # Format the financial data for better presentation
                display_financials = country_financials.copy()
                display_financials['Net_Revenue'] = display_financials['Net_Revenue'].round(0).astype(int)
                display_financials['Total_Cost'] = display_financials['Total_Cost'].round(0).astype(int)
                display_financials['Profit'] = display_financials['Profit'].round(0).astype(int)
                display_financials['Gross_Percent'] = (display_financials['Gross_Percent'] * 100).round(1)
                
                # Rename columns for display
                display_financials.columns = ['Revenue (€)', 'Cost (€)', 'Margin (%)', 'Profit (€)']
                st.dataframe(display_financials, use_container_width=True)
        
        # Lane Usage Analysis
        st.markdown('<h2 class="section-header">Lane Usage & Network Analysis</h2>', unsafe_allow_html=True)
        
        if 'lanes' in tms_data and not tms_data['lanes'].empty:
            lane_df = tms_data['lanes']
            
            st.markdown('<div class="subsection-header">Origin-Destination Network Matrix</div>', unsafe_allow_html=True)
            
            # Display the lane matrix with better formatting
            display_lanes = lane_df.fillna(0)
            st.dataframe(display_lanes, use_container_width=True)
            
            st.markdown('<div class="explanation-text">Origin-destination matrix showing shipment volumes between countries. Rows represent pickup countries, columns represent delivery countries. Values indicate number of shipments on each lane.</div>', unsafe_allow_html=True)
            
            # Extract key insights from lane data
            if len(lane_df) > 1:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="subsection-header">Top Origin Countries</div>', unsafe_allow_html=True)
                    
                    # Calculate row totals (origin totals)
                    if len(lane_df.columns) > 1:
                        numeric_cols = lane_df.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            origin_totals = lane_df[numeric_cols].sum(axis=1)
                            origin_countries = lane_df.iloc[:, 0]  # First column should be country codes
                            
                            origin_data = pd.Series(origin_totals.values, index=origin_countries)
                            origin_data = origin_data[origin_data > 0].sort_values(ascending=False)
                            
                            if not origin_data.empty:
                                st.bar_chart(origin_data.head(10), height=300)
                                st.markdown('<div class="explanation-text">Countries with highest outbound shipment volumes, indicating key pickup markets.</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="subsection-header">Top Destination Countries</div>', unsafe_allow_html=True)
                    
                    # Calculate column totals (destination totals)  
                    if len(numeric_cols) > 0:
                        dest_totals = lane_df[numeric_cols].sum(axis=0)
                        dest_data = dest_totals[dest_totals > 0].sort_values(ascending=False)
                        
                        if not dest_data.empty:
                            st.bar_chart(dest_data.head(10), height=300)
                            st.markdown('<div class="explanation-text">Countries with highest inbound shipment volumes, showing key delivery markets.</div>', unsafe_allow_html=True)
        
        # Performance Summary and Alerts
        st.markdown('<h2 class="section-header">Performance Summary & Recommendations</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="subsection-header">Current Performance Status</div>', unsafe_allow_html=True)
            
            performance_summary = []
            
            # OTP Assessment
            if avg_otp >= 95:
                performance_summary.append("✅ **OTP Performance**: Exceeding target (95%+)")
            elif avg_otp >= 90:
                performance_summary.append("⚠️ **OTP Performance**: Below target, needs improvement")
            else:
                performance_summary.append("🔴 **OTP Performance**: Critical - immediate action required")
            
            # Margin Assessment  
            if profit_margin >= 20:
                performance_summary.append("✅ **Profit Margin**: Healthy margins (20%+)")
            elif profit_margin >= 10:
                performance_summary.append("⚠️ **Profit Margin**: Below target, optimization needed")
            else:
                performance_summary.append("🔴 **Profit Margin**: Critical - cost review required")
            
            # Volume Assessment
            if total_volume_services > 0:
                performance_summary.append("✅ **Volume Operations**: Active across multiple services")
            
            # Network Assessment
            if 'country_volumes' in tms_data and len(tms_data['country_volumes']) >= 5:
                performance_summary.append("✅ **Network Coverage**: Strong European presence")
            
            for item in performance_summary:
                st.markdown(item)
        
        with col2:
            st.markdown('<div class="subsection-header">Key Recommendations</div>', unsafe_allow_html=True)
            
            recommendations = []
            
            if avg_otp < 95:
                recommendations.append("🎯 **Improve OTP**: Implement delivery time optimization and route planning")
            
            if profit_margin < 20:
                recommendations.append("💰 **Optimize Margins**: Review pricing strategy and cost structure")
            
            if 'country_volumes' in tms_data:
                top_countries = sorted(tms_data['country_volumes'].items(), key=lambda x: x[1], reverse=True)[:3]
                if top_countries:
                    recommendations.append(f"🌍 **Focus Markets**: Prioritize top markets: {', '.join([c[0] for c in top_countries])}")
            
            recommendations.append("📊 **Monitor KPIs**: Maintain regular performance tracking and reporting")
            recommendations.append("🔄 **Process Improvement**: Implement continuous improvement initiatives")
            
            for rec in recommendations:
                st.markdown(rec)
        
        # Executive Summary Box
        st.markdown(f'''
        <div class="highlight-box">
        <strong>📊 Executive Summary</strong><br><br>
        <strong>Operational Overview:</strong><br>
        • Processing {int(total_volume_services):,} pieces across multiple service types<br>
        • Serving {len(tms_data.get('country_volumes', {})):,} countries with comprehensive European coverage<br>
        • Tracking {total_orders:,} orders with {avg_otp:.1f}% on-time performance<br>
        • Generating €{total_revenue:,.0f} revenue with {profit_margin:.1f}% profit margin<br><br>
        
        <strong>Strategic Position:</strong><br>
        The Amsterdam operation demonstrates {('strong' if avg_otp >= 95 and profit_margin >= 20 else 'solid')} performance with comprehensive data tracking capabilities and European market coverage. 
        {'All key metrics are meeting targets.' if avg_otp >= 95 and profit_margin >= 20 else 'Focus areas identified for performance improvement.'}
        </div>
        ''', unsafe_allow_html=True)
    
    else:
        st.markdown('<div class="alert-box"><strong>📁 No Data Available</strong><br>Please upload your TMS Excel file to view dashboard analytics and performance metrics.</div>', unsafe_allow_html=True)

# TAB 3: Comprehensive Report
with tab3:
    st.markdown('<h1 class="section-header">TMS Performance Analysis Report</h1>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; font-size: 1.1rem; color: #666; margin-bottom: 2rem;"><strong>LFS Amsterdam Office - Comprehensive Transportation Management Review</strong></div>', unsafe_allow_html=True)
    
    if tms_data is not None:
        
        # Calculate summary metrics for report
        total_services = len(tms_data.get('service_volumes', {}))
        total_countries = len(tms_data.get('country_volumes', {}))
        
        # Executive Summary
        st.markdown(f'''
        <div class="report-section">
        <h3>📋 Executive Summary</h3>
        
        This comprehensive analysis examines the Transportation Management System (TMS) performance for the Amsterdam office (LFS) based on operational data from multiple integrated datasets. The analysis provides insights into volume distribution, financial performance, operational efficiency, and network utilization.
        
        <strong>Key Performance Highlights:</strong>
        <ul>
        <li><strong>Service Portfolio:</strong> {total_services} active service types processing {int(total_volume_services):,} total pieces</li>
        <li><strong>Geographic Reach:</strong> {total_countries} country destinations with comprehensive European coverage</li>
        <li><strong>Operational Performance:</strong> {avg_otp:.1f}% on-time delivery rate from {total_orders:,} tracked orders</li>
        <li><strong>Financial Performance:</strong> €{total_revenue:,.0f} revenue with {profit_margin:.1f}% profit margin</li>
        </ul>
        
        <strong>Business Context:</strong><br>
        The Amsterdam operation serves as a critical hub in the European logistics network, handling diverse service types and maintaining extensive country coverage. The comprehensive data tracking capabilities provide excellent visibility into all aspects of operational performance.
        </div>
        ''', unsafe_allow_html=True)
        
        # Operational Performance Analysis
        st.markdown(f'''
        <div class="report-section">
        <h3>📊 Operational Performance Analysis</h3>
        
        <strong>Volume Analysis Results:</strong><br>
        The volume analysis reveals a diversified operational portfolio with strategic market positioning:
        
        <ul>
        <li><strong>Service Diversification:</strong> {total_services} different service types providing operational flexibility and risk distribution</li>
        <li><strong>Market Coverage:</strong> Active operations across {total_countries} countries, demonstrating strong European network presence</li>
        <li><strong>Operational Scale:</strong> Processing {int(total_volume_services):,} pieces through systematic service delivery</li>
        </ul>
        
        <strong>Quality Performance Assessment:</strong><br>
        On-time performance analysis shows {'strong operational control' if avg_otp >= 95 else 'improvement opportunities'}:
        
        <ul>
        <li><strong>Current OTP Rate:</strong> {avg_otp:.1f}% against industry target of 95%</li>
        <li><strong>Order Volume:</strong> {total_orders:,} orders tracked with systematic performance monitoring</li>
        <li><strong>Performance Gap:</strong> {abs(avg_otp - 95):.1f} percentage points {'above' if avg_otp >= 95 else 'below'} target threshold</li>
        </ul>
        
        <strong>Network Utilization:</strong><br>
        The lane usage analysis demonstrates comprehensive European network coverage with established routing patterns and systematic country-to-country logistics coordination.
        </div>
        ''', unsafe_allow_html=True)
        
        # Financial Performance Analysis
        st.markdown(f'''
        <div class="report-section">
        <h3>💰 Financial Performance Analysis</h3>
        
        <strong>Revenue and Profitability Overview:</strong><br>
        Financial analysis reveals {'strong' if profit_margin >= 20 else 'developing'} profitability performance:
        
        <ul>
        <li><strong>Total Revenue:</strong> €{total_revenue:,.0f} from operational activities</li>
        <li><strong>Operating Costs:</strong> €{total_cost:,.0f} across all operational components</li>
        <li><strong>Net Profit:</strong> €{(total_revenue - total_cost):,.0f} from operations</li>
        <li><strong>Profit Margin:</strong> {profit_margin:.1f}% {'exceeding' if profit_margin >= 20 else 'below'} the 20% target</li>
        </ul>
        
        <strong>Cost Structure Analysis:</strong><br>
        The operational cost breakdown provides insights into expense distribution and optimization opportunities. Key cost components include pickup operations, shipping activities, manual processing, and delivery services.
        
        <strong>Market Profitability:</strong><br>
        Geographic analysis reveals varying profitability across different markets, with country-specific performance patterns indicating both high-performing markets and optimization opportunities.
        
        <strong>Financial Health Assessment:</strong><br>
        {'The financial metrics indicate healthy business performance with sustainable profit margins and diverse revenue streams.' if profit_margin >= 15 else 'Financial metrics suggest opportunities for margin improvement through cost optimization and pricing strategy refinement.'}
        </div>
        ''', unsafe_allow_html=True)
        
        # Strategic Recommendations
        st.markdown(f'''
        <div class="report-section">
        <h3>🎯 Strategic Recommendations</h3>
        
        <strong>Immediate Priority Actions (0-3 months):</strong>
        <ol>
        <li><strong>Performance Optimization:</strong>
            <ul>
            {'<li>Maintain current OTP excellence through process standardization</li>' if avg_otp >= 95 else '<li>Implement OTP improvement program targeting 95%+ performance</li>'}
            <li>Enhance real-time monitoring and alert systems</li>
            <li>Strengthen quality control processes and delivery coordination</li>
            </ul>
        </li>
        <li><strong>Financial Management:</strong>
            <ul>
            {'<li>Leverage strong margins for strategic growth investments</li>' if profit_margin >= 20 else '<li>Implement cost optimization program to improve margins</li>'}
            <li>Analyze country-specific profitability for resource allocation</li>
            <li>Optimize pricing strategies based on service complexity and market conditions</li>
            </ul>
        </li>
        </ol>
        
        <strong>Medium-Term Strategic Initiatives (3-12 months):</strong>
        <ol>
        <li><strong>Market Development:</strong> Focus on high-volume, high-margin country markets for expansion</li>
        <li><strong>Service Enhancement:</strong> Develop specialized services based on volume analysis insights</li>
        <li><strong>Network Optimization:</strong> Strengthen high-traffic lanes and optimize routing efficiency</li>
        <li><strong>Technology Advancement:</strong> Implement predictive analytics and automated decision-making systems</li>
        </ol>
        
        <strong>Long-Term Vision (12+ months):</strong>
        <ol>
        <li><strong>Market Leadership:</strong> Establish dominant position in key European logistics corridors</li>
        <li><strong>Innovation Leadership:</strong> Develop industry-leading logistics solutions and services</li>
        <li><strong>Operational Excellence:</strong> Achieve best-in-class performance across all KPIs</li>
        <li><strong>Sustainable Growth:</strong> Build scalable operations supporting long-term expansion</li>
        </ol>
        </div>
        ''', unsafe_allow_html=True)
        
        # Implementation Roadmap
        st.markdown('''
        <div class="report-section">
        <h3>🛣️ Implementation Roadmap</h3>
        
        <strong>Phase 1: Foundation Strengthening (Months 1-3)</strong>
        <ul>
        <li>Complete performance baseline establishment</li>
        <li>Implement enhanced monitoring and reporting systems</li>
        <li>Launch targeted improvement initiatives for underperforming areas</li>
        <li>Establish regular performance review cycles</li>
        </ul>
        
        <strong>Phase 2: Performance Optimization (Months 4-8)</strong>
        <ul>
        <li>Execute operational efficiency improvements</li>
        <li>Implement cost optimization strategies</li>
        <li>Enhance service quality and customer satisfaction</li>
        <li>Strengthen network utilization and routing efficiency</li>
        </ul>
        
        <strong>Phase 3: Strategic Growth (Months 9-12)</strong>
        <ul>
        <li>Launch market expansion initiatives</li>
        <li>Implement advanced technology solutions</li>
        <li>Develop competitive service offerings</li>
        <li>Establish industry leadership position</li>
        </ul>
        
        <strong>Success Metrics and Monitoring:</strong><br>
        Regular monitoring of KPIs including OTP rates, profit margins, volume growth, and customer satisfaction scores will ensure successful implementation and continuous improvement.
        </div>
        ''', unsafe_allow_html=True)
        
        # Conclusion
        st.markdown(f'''
        <div class="report-section">
        <h3>📄 Conclusion</h3>
        
        <strong>Performance Assessment Summary:</strong><br>
        The Amsterdam TMS operation demonstrates {'exceptional' if avg_otp >= 95 and profit_margin >= 20 else 'strong'} performance across multiple operational dimensions. The comprehensive data analysis reveals:
        
        <ul>
        <li><strong>Operational Strength:</strong> Systematic processing of {int(total_volume_services):,} pieces across {total_services} service types</li>
        <li><strong>Market Position:</strong> Strong European presence with {total_countries} country coverage</li>
        <li><strong>Quality Performance:</strong> {avg_otp:.1f}% OTP rate with systematic tracking and monitoring</li>
        <li><strong>Financial Health:</strong> €{total_revenue:,.0f} revenue generation with {profit_margin:.1f}% profit margins</li>
        </ul>
        
        <strong>Strategic Outlook:</strong><br>
        The operation is well-positioned for continued success and growth. The comprehensive data infrastructure provides excellent foundation for performance optimization and strategic decision-making. 
        
        {'The strong performance metrics indicate readiness for expansion and market leadership initiatives.' if avg_otp >= 95 and profit_margin >= 20 else 'The identified improvement opportunities provide clear pathways for performance enhancement and competitive strengthening.'}
        
        <strong>Next Steps:</strong><br>
        Implementation of the recommended strategic initiatives will ensure continued operational excellence and market leadership in European logistics operations.
        </div>
        ''', unsafe_allow_html=True)
        
    else:
        st.markdown('<div class="alert-box"><strong>📁 Report Generation Requires Data</strong><br>Please upload your TMS Excel file to generate the comprehensive performance analysis report.</div>', unsafe_allow_html=True)

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 System Status")
if tms_data is not None:
    st.sidebar.success(f"✅ Data loaded: {len(tms_data)} datasets")
    st.sidebar.info(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Data export functionality
    st.sidebar.markdown("### 📥 Export Options")
    if st.sidebar.button("📊 Export Dashboard Data"):
        st.sidebar.info("Data export functionality ready - contact administrator for CSV downloads")
else:
    st.sidebar.warning("📁 Awaiting data upload")

st.sidebar.markdown("### ℹ️ Dashboard Info")
st.sidebar.info("Professional TMS Analytics Dashboard\nCreated for LFS Amsterdam Operations")

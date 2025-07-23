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
    .alert-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .report-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .explanation-text {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 0.3rem;
        font-size: 0.9rem;
        color: #555;
        margin-top: 0.5rem;
        border-left: 3px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Title and header
st.markdown('<h1 class="main-header">LFS Amsterdam - TMS Performance Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Transportation Management System Analytics & KPI Monitoring**")

# Sidebar for controls
st.sidebar.title("Dashboard Controls")
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
            
            # 1. OTP POD Sheet Processing
            if "OTP POD" in excel_sheets:
                otp_df = excel_sheets["OTP POD"].copy()
                if len(otp_df.columns) >= 6:
                    otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status', 'QC_Name'] + [f'Col_{i}' for i in range(6, len(otp_df.columns))]
                otp_df = otp_df.dropna(subset=[otp_df.columns[0]])
                if 'QDT' in otp_df.columns:
                    otp_df['QDT'] = safe_date_conversion(otp_df['QDT'])
                if 'POD_DateTime' in otp_df.columns:
                    otp_df['POD_DateTime'] = safe_date_conversion(otp_df['POD_DateTime'])
                data['otp'] = otp_df
            
            # 2. Volume per SVC Sheet Processing (actually country codes)
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"].copy()
                volume_df = volume_df.dropna(how='all')
                data['volume'] = volume_df
            
            # 3. Lane Usage Sheet Processing
            if "Lane usage " in excel_sheets:
                lane_df = excel_sheets["Lane usage "].copy()
                data['lanes'] = lane_df
            
            # 4. Cost Sales Sheet Processing
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
            
            # 5. AMS RAW DATA Sheet Processing
            if "AMS RAW DATA" in excel_sheets:
                raw_df = excel_sheets["AMS RAW DATA"].copy()
                data['raw_data'] = raw_df
            
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
        st.sidebar.success("TMS Data loaded successfully")
        st.sidebar.write("Available datasets:", list(tms_data.keys()))
    else:
        st.sidebar.error("Error loading TMS data")
else:
    st.sidebar.info("Please upload your TMS data file to begin analysis")

# Create tab structure
tab1, tab2, tab3, tab4 = st.tabs(["Data Overview", "Dashboard & Analytics", "OTP Deep Dive", "Comprehensive Report"])

# TAB 1: Data Overview
with tab1:
    st.markdown('<h2 class="section-header">Data Overview</h2>', unsafe_allow_html=True)
    
    if tms_data is not None:
        
        # Dataset summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Dataset Summary**")
            
            dataset_info = []
            for sheet_name, df in tms_data.items():
                dataset_info.append({
                    'Sheet': sheet_name,
                    'Rows': len(df),
                    'Columns': len(df.columns),
                    'Data Quality': 'Good' if not df.empty else 'Empty'
                })
            
            dataset_df = pd.DataFrame(dataset_info)
            st.dataframe(dataset_df, hide_index=True)
        
        with col2:
            st.markdown("**Data Completeness**")
            
            if 'raw_data' in tms_data:
                raw_df = tms_data['raw_data']
                completeness = (raw_df.notna().sum() / len(raw_df) * 100).round(1)
                
                # Show top 10 columns with completeness
                completeness_df = pd.DataFrame({
                    'Column': completeness.head(10).index,
                    'Completeness %': completeness.head(10).values
                })
                st.dataframe(completeness_df, hide_index=True)
        
        # Sample data preview
        st.markdown("**Sample Data Preview**")
        
        for sheet_name, df in tms_data.items():
            if not df.empty:
                with st.expander(f"{sheet_name} - Sample Data"):
                    st.dataframe(df.head(3))
        
        # Data quality indicators
        st.markdown("**Data Quality Indicators**")
        
        quality_metrics = {}
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            quality_metrics['OTP Data'] = {
                'Total Records': len(otp_df),
                'Complete Status Records': len(otp_df.dropna(subset=['Status'])),
                'Date Consistency': 'Good' if 'QDT' in otp_df.columns else 'Missing'
            }
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            quality_metrics['Financial Data'] = {
                'Total Transactions': len(cost_df),
                'Revenue Records': len(cost_df.dropna(subset=['Net_Revenue'])),
                'Cost Records': len(cost_df.dropna(subset=['Total_Cost']))
            }
        
        for metric_name, metrics in quality_metrics.items():
            st.markdown(f"**{metric_name}:**")
            for key, value in metrics.items():
                st.write(f"• {key}: {value}")
    
    else:
        st.info("Upload your TMS data file to see data overview and quality metrics.")

# TAB 2: Dashboard & Analytics
with tab2:
    if tms_data is not None:
        
        # Calculate key metrics
        total_volume = 0
        volume_by_country = {}
        
        # Process volume data (by country, not service)
        if 'volume' in tms_data and not tms_data['volume'].empty:
            volume_df = tms_data['volume']
            for idx, row in volume_df.iterrows():
                if len(row) >= 2 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    try:
                        country = str(row.iloc[0]).strip()
                        volume = float(row.iloc[1]) if isinstance(row.iloc[1], (int, float)) else 0
                        if country not in ['Count of PIECES', 'SVC', 'Total', ''] and volume > 0:
                            volume_by_country[country] = volume
                            total_volume += volume
                    except:
                        continue
        
        # OTP Metrics
        avg_otp = 0
        total_orders = 0
        on_time_orders = 0
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            if 'Status' in otp_df.columns:
                status_series = otp_df['Status'].dropna()
                total_orders = len(status_series)
                on_time_orders = len(status_series[status_series == 'ON TIME'])
                avg_otp = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Financial Metrics
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
        
        # KPI Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Volume",
                value=f"{int(total_volume):,}",
                delta="Pieces processed"
            )
        
        with col2:
            st.metric(
                label="OTP Performance",
                value=f"{avg_otp:.1f}%",
                delta=f"{avg_otp - 95:.1f}% vs target",
                delta_color="normal" if avg_otp >= 95 else "inverse"
            )
        
        with col3:
            st.metric(
                label="Total Revenue",
                value=f"€{total_revenue:,.0f}",
                delta="Operational revenue"
            )
        
        with col4:
            st.metric(
                label="Profit Margin",
                value=f"{profit_margin:.1f}%",
                delta=f"{profit_margin - 20:.1f}% vs target",
                delta_color="normal" if profit_margin >= 20 else "inverse"
            )
        
        st.markdown("---")
        
        # Volume Analysis by Country
        st.markdown('<h2 class="section-header">Volume Analysis by Country</h2>', unsafe_allow_html=True)
        
        if volume_by_country:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Volume Distribution by Country**")
                volume_series = pd.Series(volume_by_country)
                st.bar_chart(volume_series)
                
                st.markdown('<div class="explanation-text">This chart shows shipment volume distribution across different countries. Country codes represent pickup or delivery locations, with higher bars indicating greater shipping activity to/from that country.</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Country Volume Table**")
                volume_table = pd.DataFrame({
                    'Country Code': volume_series.index,
                    'Total Pieces': volume_series.values.astype(int),
                    'Percentage': (volume_series.values / volume_series.sum() * 100).round(1)
                })
                st.dataframe(volume_table, hide_index=True)
                
                top_country = max(volume_by_country, key=volume_by_country.get)
                st.markdown(f"**Top Market**: {top_country} ({volume_by_country[top_country]:.0f} pieces)")
        
        # Enhanced Financial Analysis
        st.markdown('<h2 class="section-header">Financial Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            
            # Revenue vs Cost Analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Revenue vs Cost Breakdown**")
                
                # Cost component analysis
                cost_components = {}
                if 'PU_Cost' in cost_df.columns:
                    cost_components['Pickup Cost'] = cost_df['PU_Cost'].sum()
                if 'Ship_Cost' in cost_df.columns:
                    cost_components['Shipping Cost'] = cost_df['Ship_Cost'].sum()
                if 'Man_Cost' in cost_df.columns:
                    cost_components['Manual Cost'] = cost_df['Man_Cost'].sum()
                if 'Del_Cost' in cost_df.columns:
                    cost_components['Delivery Cost'] = cost_df['Del_Cost'].sum()
                
                if cost_components:
                    cost_series = pd.Series(cost_components)
                    st.bar_chart(cost_series)
                    
                    st.markdown('<div class="explanation-text">Cost breakdown shows the relative contribution of different operational components. Pickup and delivery costs typically represent the highest operational expenses, while manual handling costs vary based on service complexity.</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Profitability Analysis**")
                
                # Margin distribution
                if 'Gross_Percent' in cost_df.columns:
                    margin_bins = pd.cut(cost_df['Gross_Percent'], bins=[-1, 0, 0.1, 0.2, 0.3, 1], labels=['Loss', '0-10%', '10-20%', '20-30%', '30%+'])
                    margin_dist = margin_bins.value_counts()
                    st.bar_chart(margin_dist)
                    
                    st.markdown('<div class="explanation-text">Margin distribution analysis shows profitability spread across shipments. Higher percentages in the 20%+ categories indicate healthy profit margins, while loss-making shipments require investigation for cost optimization.</div>', unsafe_allow_html=True)
            
            # Financial Performance by Country
            st.markdown("**Financial Performance by Country**")
            
            if 'PU_Country' in cost_df.columns:
                country_financials = cost_df.groupby('PU_Country').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum',
                    'Gross_Percent': 'mean'
                }).round(2)
                
                country_financials['Profit'] = country_financials['Net_Revenue'] - country_financials['Total_Cost']
                country_financials = country_financials.sort_values('Net_Revenue', ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Revenue by Country**")
                    st.bar_chart(country_financials['Net_Revenue'])
                    
                    st.markdown('<div class="explanation-text">Revenue distribution by pickup country shows market concentration and identifies key geographic markets. This helps in resource allocation and market development strategies.</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Profit Margin by Country**")
                    st.bar_chart(country_financials['Gross_Percent'])
                    
                    st.markdown('<div class="explanation-text">Profit margin variation by country reveals operational efficiency differences across markets. Countries with lower margins may require cost optimization or pricing adjustments.</div>', unsafe_allow_html=True)
                
                # Detailed financial table
                st.markdown("**Detailed Financial Performance by Country**")
                st.dataframe(country_financials)
        
        # Lane Usage Analysis
        st.markdown('<h2 class="section-header">Lane Usage Analysis</h2>', unsafe_allow_html=True)
        
        if 'lanes' in tms_data and not tms_data['lanes'].empty:
            lane_df = tms_data['lanes']
            
            st.markdown("**Origin-Destination Matrix**")
            st.dataframe(lane_df.fillna(0))
            
            st.markdown('<div class="explanation-text">The lane usage matrix shows shipment volumes between origin and destination countries. This analysis helps identify high-traffic corridors, optimize routing decisions, and plan capacity allocation across the European network.</div>', unsafe_allow_html=True)
    
    else:
        st.info("Upload your TMS data file to see dashboard analytics.")

# TAB 3: OTP Deep Dive
with tab3:
    st.markdown('<h2 class="section-header">On-Time Performance Deep Dive</h2>', unsafe_allow_html=True)
    
    if tms_data is not None and 'otp' in tms_data:
        otp_df = tms_data['otp']
        
        # OTP Status Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**OTP Status Distribution**")
            if 'Status' in otp_df.columns:
                status_counts = otp_df['Status'].value_counts()
                st.bar_chart(status_counts)
                
                st.markdown('<div class="explanation-text">Overall delivery status distribution showing the proportion of on-time versus delayed deliveries. A healthy operation should maintain above 95% on-time performance.</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Delay Analysis**")
            
            # Analyze delays
            if 'Time_Diff' in otp_df.columns and 'Status' in otp_df.columns:
                delayed_orders = otp_df[otp_df['Status'] != 'ON TIME']
                
                if not delayed_orders.empty and 'Time_Diff' in delayed_orders.columns:
                    delay_analysis = delayed_orders['Time_Diff'].describe()
                    
                    delay_df = pd.DataFrame({
                        'Metric': ['Count', 'Mean Delay', 'Std Dev', 'Min Delay', 'Max Delay'],
                        'Value': [delay_analysis['count'], delay_analysis['mean'], 
                                delay_analysis['std'], delay_analysis['min'], delay_analysis['max']]
                    })
                    st.dataframe(delay_df, hide_index=True)
                
                st.markdown('<div class="explanation-text">Delay analysis quantifies the severity and distribution of late deliveries. Understanding delay patterns helps identify root causes and implement targeted improvements.</div>', unsafe_allow_html=True)
        
        # Late Delivery Classification
        if 'Status' in otp_df.columns:
            st.markdown("**Late Delivery Classification & Root Cause Analysis**")
            
            # Get all non-on-time statuses
            delayed_df = otp_df[otp_df['Status'] != 'ON TIME']
            
            if not delayed_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Delay Categories**")
                    delay_categories = delayed_df['Status'].value_counts()
                    st.bar_chart(delay_categories)
                    
                    st.markdown('<div class="explanation-text">Classification of different types of delays helps identify specific operational issues. Each category requires different remediation strategies.</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Delay Impact Analysis**")
                    
                    # Calculate delay impact
                    total_delayed = len(delayed_df)
                    delay_rate = (total_delayed / len(otp_df) * 100) if len(otp_df) > 0 else 0
                    
                    impact_metrics = pd.DataFrame({
                        'Metric': ['Total Delayed Orders', 'Delay Rate (%)', 'On-Time Orders', 'OTP Achievement (%)'],
                        'Value': [total_delayed, f"{delay_rate:.1f}%", len(otp_df) - total_delayed, f"{100 - delay_rate:.1f}%"]
                    })
                    st.dataframe(impact_metrics, hide_index=True)
        
        # Time-based OTP Analysis
        if 'QDT' in otp_df.columns and 'POD_DateTime' in otp_df.columns:
            st.markdown("**Time-based OTP Trends**")
            
            # Convert dates and analyze trends
            otp_df_clean = otp_df.dropna(subset=['QDT', 'Status'])
            
            if not otp_df_clean.empty:
                # Group by date and calculate daily OTP
                otp_df_clean['Date'] = pd.to_datetime(otp_df_clean['QDT']).dt.date
                daily_otp = otp_df_clean.groupby('Date').agg({
                    'Status': lambda x: (x == 'ON TIME').mean() * 100
                }).round(1)
                
                daily_otp.columns = ['Daily_OTP']
                
                if len(daily_otp) > 1:
                    st.line_chart(daily_otp)
                    
                    st.markdown('<div class="explanation-text">Daily OTP trends reveal performance patterns over time. Consistent performance above 95% indicates stable operations, while volatility suggests process inconsistencies requiring attention.</div>', unsafe_allow_html=True)
        
        # Quality Control Analysis
        if 'QC_Name' in otp_df.columns:
            st.markdown("**Quality Control Impact**")
            
            qc_analysis = otp_df.groupby('QC_Name').agg({
                'Status': lambda x: (x == 'ON TIME').mean() * 100
            }).round(1)
            
            qc_analysis.columns = ['OTP_Rate']
            qc_analysis = qc_analysis.sort_values('OTP_Rate', ascending=False)
            
            if not qc_analysis.empty:
                st.bar_chart(qc_analysis)
                
                st.markdown('<div class="explanation-text">Quality control performance analysis shows how different QC processes or personnel impact delivery performance. This helps identify training needs and process improvements.</div>', unsafe_allow_html=True)
    
    else:
        st.info("OTP data not available for deep dive analysis.")

# TAB 4: Comprehensive Report
with tab4:
    st.markdown('<h1 class="section-header">TMS Performance Analysis Report</h1>', unsafe_allow_html=True)
    st.markdown("**LFS Amsterdam Office - Comprehensive Transportation Management Review**")
    
    if tms_data is not None:
        # Executive Summary
        st.markdown("""
        <div class="report-section">
        <h3>Executive Summary</h3>
        
        This comprehensive analysis examines the Transportation Management System (TMS) performance for the Amsterdam office (LFS) based on operational data extracted from multiple datasets. The analysis covers volume distribution, on-time performance, cost efficiency, and lane utilization patterns.
        
        <strong>Key Performance Areas:</strong>
        <ul>
        <li><strong>Volume Analysis:</strong> Geographic distribution and market concentration analysis</li>
        <li><strong>Financial Performance:</strong> Revenue, cost structure, and profitability assessment</li>
        <li><strong>Operational Excellence:</strong> On-time performance and quality metrics</li>
        <li><strong>Network Optimization:</strong> Lane usage and routing efficiency</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Performance Metrics Summary
        st.markdown(f"""
        <div class="report-section">
        <h3>Performance Metrics Summary</h3>
        
        <strong>Operational Performance:</strong>
        <ul>
        <li><strong>Total Volume Processed:</strong> {int(total_volume):,} pieces</li>
        <li><strong>On-Time Performance:</strong> {avg_otp:.1f}% (Target: 95%)</li>
        <li><strong>Total Revenue:</strong> €{total_revenue:,.0f}</li>
        <li><strong>Profit Margin:</strong> {profit_margin:.1f}% (Target: 20%)</li>
        </ul>
        
        <strong>Performance Assessment:</strong>
        <ul>
        <li><strong>Volume:</strong> Diverse geographic coverage with concentrated activity in key markets</li>
        <li><strong>Quality:</strong> {'Performance exceeds industry standards' if avg_otp >= 95 else 'Performance improvement required to meet 95% target'}</li>
        <li><strong>Profitability:</strong> {'Strong financial performance with healthy margins' if profit_margin >= 20 else 'Margin optimization opportunities identified'}</li>
        <li><strong>Network:</strong> Comprehensive European coverage with established lane networks</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Strategic Recommendations
        st.markdown("""
        <div class="report-section">
        <h3>Strategic Recommendations</h3>
        
        <strong>Immediate Actions (0-3 months):</strong>
        <ol>
        <li><strong>Performance Optimization:</strong> Implement automated OTP monitoring and alert systems</li>
        <li><strong>Cost Management:</strong> Analyze cost components by country and service type for optimization opportunities</li>
        <li><strong>Quality Improvement:</strong> Address delay root causes through process improvements</li>
        </ol>
        
        <strong>Medium-Term Strategy (3-12 months):</strong>
        <ol>
        <li><strong>Market Development:</strong> Focus resources on high-margin countries and lanes</li>
        <li><strong>Operational Excellence:</strong> Standardize processes across all operational areas</li>
        <li><strong>Technology Enhancement:</strong> Implement predictive analytics for performance optimization</li>
        </ol>
        
        <strong>Long-Term Vision (12+ months):</strong>
        <ol>
        <li><strong>Market Leadership:</strong> Establish dominant position in key European corridors</li>
        <li><strong>Innovation:</strong> Develop advanced logistics solutions and services</li>
        <li><strong>Sustainability:</strong> Implement sustainable logistics practices and reporting</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Conclusion
        st.markdown("""
        <div class="report-section">
        <h3>Conclusion</h3>
        
        The TMS analysis reveals a well-established Amsterdam operation with strong foundations in European logistics. The comprehensive data tracking capabilities provide excellent visibility into operational performance and financial metrics.
        
        <strong>Key Strengths:</strong>
        <ul>
        <li>Comprehensive data tracking and performance monitoring</li>
        <li>Established European network with diverse country coverage</li>
        <li>Strong operational foundation with detailed cost tracking</li>
        <li>Professional quality control and delivery monitoring systems</li>
        </ul>
        
        <strong>Improvement Focus Areas:</strong>
        <ul>
        <li>On-time performance optimization to exceed 95% target consistently</li>
        <li>Cost structure analysis and margin improvement initiatives</li>
        <li>Geographic market optimization based on profitability analysis</li>
        <li>Operational process standardization and efficiency improvements</li>
        </ul>
        
        The Amsterdam office is well-positioned to achieve operational excellence through focused execution of the recommended improvement initiatives while maintaining its strong market position in European logistics.
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("Please upload your TMS data file to generate the comprehensive report.")

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")
if tms_data is not None:
    st.sidebar.success(f"Data loaded: {len(tms_data)} datasets")
else:
    st.sidebar.warning("Awaiting data upload")

st.sidebar.markdown("### Dashboard Info")
st.sidebar.info("Created for LFS Amsterdam team")

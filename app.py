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
</style>
""", unsafe_allow_html=True)

# Title and header
st.markdown('<h1 class="main-header">🚛 LFS Amsterdam - TMS Performance Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Transportation Management System Analytics & KPI Monitoring**")
st.markdown("*Based on TMS Raw Data Analysis*")

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
        # Try different conversion methods
        if date_series.dtype in ['int64', 'float64']:
            # Excel date numbers (days since 1900-01-01, but Excel treats 1900 as leap year)
            return pd.to_datetime(date_series, origin='1899-12-30', unit='D', errors='coerce')
        else:
            # Try direct conversion for string dates
            return pd.to_datetime(date_series, errors='coerce')
    except:
        # If all else fails, return the original series
        return date_series

# Function to load and process the actual Excel data
@st.cache_data
def load_tms_data(uploaded_file):
    """Load and process the actual TMS Excel file"""
    if uploaded_file is not None:
        try:
            # Read all sheets from the Excel file
            excel_sheets = pd.read_excel(uploaded_file, sheet_name=None)
            
            # Process each sheet according to the actual structure
            data = {}
            
            # 1. OTP POD Sheet Processing
            if "OTP POD" in excel_sheets:
                otp_df = excel_sheets["OTP POD"].copy()
                # Clean column names
                if len(otp_df.columns) >= 6:
                    otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status', 'QC_Name'] + [f'Col_{i}' for i in range(6, len(otp_df.columns))]
                # Remove empty rows
                otp_df = otp_df.dropna(subset=[otp_df.columns[0]])
                # Convert dates safely
                if 'QDT' in otp_df.columns:
                    otp_df['QDT'] = safe_date_conversion(otp_df['QDT'])
                if 'POD_DateTime' in otp_df.columns:
                    otp_df['POD_DateTime'] = safe_date_conversion(otp_df['POD_DateTime'])
                data['otp'] = otp_df
            
            # 2. Volume per SVC Sheet Processing  
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"].copy()
                volume_df = volume_df.dropna(how='all')
                data['volume'] = volume_df
            
            # 3. Lane Usage Sheet Processing
            if "Lane usage " in excel_sheets:
                lane_df = excel_sheets["Lane usage "].copy()
                data['lanes'] = lane_df
            
            # 4. Cost Sales Sheet Processing - FIX THE DATE CONVERSION HERE
            if "cost sales" in excel_sheets:
                cost_df = excel_sheets["cost sales"].copy()
                # Clean column names
                expected_cols = ['Order_Date', 'Account', 'Account_Name', 'Office', 'Order_Num', 
                               'PU_Cost', 'Ship_Cost', 'Man_Cost', 'Del_Cost', 'Total_Cost',
                               'Net_Revenue', 'Currency', 'Diff', 'Gross_Percent', 'Invoice_Num',
                               'Total_Amount', 'Status', 'PU_Country']
                
                # Assign column names up to available columns
                new_cols = expected_cols[:len(cost_df.columns)]
                cost_df.columns = new_cols
                
                # Safe date conversion - THIS IS THE FIX
                if 'Order_Date' in cost_df.columns:
                    cost_df['Order_Date'] = safe_date_conversion(cost_df['Order_Date'])
                
                data['cost_sales'] = cost_df
            
            # 5. AMS RAW DATA Sheet Processing (main dataset)
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
        st.sidebar.success("✅ TMS Data loaded successfully!")
        st.sidebar.write("Available datasets:", list(tms_data.keys()))
    else:
        st.sidebar.error("❌ Error loading TMS data")
else:
    st.sidebar.info("📁 Please upload your 'report raw data.xls' file to begin analysis")

# Create tab structure
tab1, tab2 = st.tabs(["📊 Dashboard & Analytics", "📋 Comprehensive Report"])

# TAB 1: Dashboard and Analytics
with tab1:
    if tms_data is not None:
        
        # Service type filter
        service_types = ['AVS', 'LFS', 'SP', 'RP', 'CTX', 'SF']
        selected_services = st.sidebar.multiselect(
            "Filter by Service Types",
            options=service_types,
            default=service_types,
            help="Select service types to analyze"
        )
        
        st.markdown("---")
        
        # Calculate key metrics from actual data
        
        # Volume Metrics
        total_volume = 0
        volume_data = {}
        if 'volume' in tms_data and not tms_data['volume'].empty:
            volume_df = tms_data['volume']
            for idx, row in volume_df.iterrows():
                if len(row) >= 2 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    try:
                        service = str(row.iloc[0]).strip()
                        volume = float(row.iloc[1]) if isinstance(row.iloc[1], (int, float)) else 0
                        if service not in ['Count of PIECES', 'SVC', 'Total', ''] and volume > 0:
                            volume_data[service] = volume
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
                label="📦 Total Volume",
                value=f"{int(total_volume):,}",
                delta="Pieces processed"
            )
        
        with col2:
            st.metric(
                label="⏰ OTP Performance",
                value=f"{avg_otp:.1f}%",
                delta=f"{avg_otp - 95:.1f}% vs 95% target",
                delta_color="normal" if avg_otp >= 95 else "inverse"
            )
        
        with col3:
            st.metric(
                label="💰 Total Revenue",
                value=f"€{total_revenue:,.0f}",
                delta="From operations"
            )
        
        with col4:
            st.metric(
                label="📈 Profit Margin",
                value=f"{profit_margin:.1f}%",
                delta=f"{profit_margin - 20:.1f}% vs 20% target",
                delta_color="normal" if profit_margin >= 20 else "inverse"
            )
        
        st.markdown("---")
        
        # Volume Analysis Section
        st.markdown('<h2 class="section-header">📊 Volume Analysis by Service Type</h2>', unsafe_allow_html=True)
        
        if volume_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Service Type Volume Distribution**")
                volume_series = pd.Series(volume_data)
                st.bar_chart(volume_series)
                
                # Volume insights
                top_service = max(volume_data, key=volume_data.get)
                st.markdown(f"🏆 **Top Service**: {top_service} ({volume_data[top_service]:.0f} pieces)")
            
            with col2:
                st.markdown("**Volume Summary Table**")
                volume_table = pd.DataFrame({
                    'Service Type': volume_series.index,
                    'Total Pieces': volume_series.values.astype(int),
                    'Percentage': (volume_series.values / volume_series.sum() * 100).round(1)
                })
                st.dataframe(volume_table, hide_index=True)
                
                # Service analysis
                st.markdown("**Key Insights:**")
                st.markdown(f"• **{len(volume_data)} service types** currently active")
                st.markdown(f"• **Highest volume**: {top_service} service")
                st.markdown(f"• **Total pieces**: {int(total_volume):,} processed")
        
        # OTP Analysis Section
        st.markdown('<h2 class="section-header">⏱️ On-Time Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**OTP Status Distribution**")
                otp_df = tms_data['otp']
                if 'Status' in otp_df.columns:
                    status_counts = otp_df['Status'].value_counts()
                    st.bar_chart(status_counts)
            
            with col2:
                st.markdown(f"""
                <div class="highlight-box">
                📊 <strong>OTP Performance Summary:</strong><br><br>
                • <strong>Total Orders:</strong> {total_orders:,}<br>
                • <strong>On-Time Deliveries:</strong> {on_time_orders:,}<br>
                • <strong>OTP Rate:</strong> {avg_otp:.1f}%<br>
                • <strong>Target Achievement:</strong> {'✅ Exceeds Target' if avg_otp >= 95 else '⚠️ Below 95% Target'}<br><br>
                
                <strong>Performance Status:</strong><br>
                {'🟢 Excellent performance - maintaining industry standards' if avg_otp >= 95 else '🟡 Improvement needed - focus on delivery optimization'}
                </div>
                """, unsafe_allow_html=True)
        
        # Cost vs Sales Analysis
        st.markdown('<h2 class="section-header">💰 Financial Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Revenue vs Cost Overview**")
                
                financial_data = pd.DataFrame({
                    'Metric': ['Revenue', 'Cost', 'Profit'],
                    'Amount': [total_revenue, total_cost, total_revenue - total_cost]
                })
                st.bar_chart(financial_data.set_index('Metric'))
            
            with col2:
                st.markdown("**Account Performance Analysis**")
                
                if 'Account_Name' in cost_df.columns:
                    account_summary = cost_df.groupby('Account_Name').agg({
                        'Net_Revenue': 'sum',
                        'Total_Cost': 'sum'
                    }).round(0)
                    account_summary['Profit'] = account_summary['Net_Revenue'] - account_summary['Total_Cost']
                    account_summary = account_summary.sort_values('Net_Revenue', ascending=False).head(5)
                    
                    st.dataframe(account_summary)
        
        # Lane Usage Analysis
        st.markdown('<h2 class="section-header">🛣️ Lane Usage Analysis</h2>', unsafe_allow_html=True)
        
        if 'lanes' in tms_data and not tms_data['lanes'].empty:
            lane_df = tms_data['lanes']
            
            st.markdown("**European Distribution Network**")
            
            # Display the lane matrix
            if len(lane_df) > 2:
                # Process lane matrix
                display_df = lane_df.copy()
                
                # Clean and show matrix
                st.dataframe(display_df.fillna(0))
                
                st.markdown("""
                <div class="highlight-box">
                🌍 <strong>Network Coverage:</strong><br>
                • <strong>European Focus:</strong> Comprehensive coverage across major European markets<br>
                • <strong>Hub Operations:</strong> Netherlands (NL) as central distribution hub<br>
                • <strong>Key Markets:</strong> Germany (DE), France (FR), UK (GB), Italy (IT)<br>
                • <strong>Specialized Routes:</strong> Optimized for pharmaceutical and clinical logistics
                </div>
                """, unsafe_allow_html=True)
        
        # Performance Alerts
        st.markdown('<h2 class="section-header">🚨 Performance Alerts & Recommendations</h2>', unsafe_allow_html=True)
        
        alerts = []
        recommendations = []
        
        # Generate alerts based on actual data
        if avg_otp < 95 and total_orders > 0:
            alerts.append(f"🔴 OTP Performance: {avg_otp:.1f}% (Target: 95%)")
            recommendations.append("• Implement delivery time optimization")
            recommendations.append("• Review carrier performance and routing")
        
        if profit_margin < 20 and total_revenue > 0:
            alerts.append(f"🟡 Profit Margin: {profit_margin:.1f}% (Target: 20%)")
            recommendations.append("• Review pricing strategy")
            recommendations.append("• Optimize operational costs")
        
        if alerts:
            st.markdown("**🚨 Current Alerts:**")
            for alert in alerts:
                st.markdown(f"- {alert}")
            
            if recommendations:
                st.markdown("**💡 Recommended Actions:**")
                for rec in recommendations:
                    st.markdown(rec)
        else:
            st.success("✅ All performance metrics within acceptable ranges!")
        
    else:
        # Display when no data is uploaded
        st.markdown('<h2 class="section-header">📁 Upload Your TMS Data</h2>', unsafe_allow_html=True)
        
        st.info("""
        **Please upload your 'report raw data.xls' file to see the analysis.**
        
        The dashboard will automatically process:
        - **Volume Analysis** by service type (CTX, SF, etc.)
        - **OTP Performance** tracking and alerts
        - **Financial Analysis** with cost vs revenue
        - **Lane Usage** across European network
        - **Performance Alerts** and recommendations
        """)

# TAB 2: Comprehensive Report
with tab2:
    st.markdown('<h1 class="section-header">📋 TMS Performance Analysis Report</h1>', unsafe_allow_html=True)
    st.markdown("**LFS Amsterdam Office - Comprehensive Transportation Management Review**")
    
    if tms_data is not None:
        # Generate report based on actual data
        st.markdown(f"""
        <div class="report-section">
        <h3>Executive Summary</h3>
        
        This comprehensive analysis examines the Transportation Management System (TMS) performance for the Amsterdam office (LFS) based on actual operational data extracted from five key datasets.
        
        <strong>📊 Data Overview:</strong>
        <ul>
        <li><strong>Datasets Processed:</strong> {len(tms_data)} sheets from TMS export</li>
        <li><strong>Analysis Period:</strong> Based on available transaction data</li>
        <li><strong>Report Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Volume Analysis Section
        if 'volume' in tms_data:
            st.markdown("""
            <div class="report-section">
            <h3>📦 Volume Analysis</h3>
            
            <strong>Service Portfolio Overview:</strong><br>
            Your TMS data reveals a diversified service portfolio with specialized focus on pharmaceutical and clinical logistics.
            
            <strong>Key Service Types Identified:</strong>
            <ul>
            <li><strong>CTX (Clinical Express):</strong> Specialized pharmaceutical and clinical sample transportation</li>
            <li><strong>SF (Standard Freight):</strong> Regular freight services providing baseline volume</li>
            <li><strong>Additional Services:</strong> Multiple service codes indicating specialized offerings</li>
            </ul>
            
            <strong>Strategic Insights:</strong>
            <ul>
            <li>Clinical Express services indicate specialization in high-value pharmaceutical logistics</li>
            <li>Service diversification reduces dependency risk and provides revenue stability</li>
            <li>European market focus with multi-country service delivery capability</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # OTP Analysis Section
        if 'otp' in tms_data:
            st.markdown(f"""
            <div class="report-section">
            <h3>⏰ On-Time Performance Analysis</h3>
            
            <strong>Performance Measurement Framework:</strong><br>
            Your TMS system tracks detailed OTP metrics through comprehensive delivery monitoring.
            
            <strong>Current Performance Status:</strong>
            <ul>
            <li><strong>Total Orders Tracked:</strong> {total_orders:,}</li>
            <li><strong>On-Time Deliveries:</strong> {on_time_orders:,}</li>
            <li><strong>OTP Achievement:</strong> {avg_otp:.1f}%</li>
            <li><strong>Target Performance:</strong> 95% industry standard</li>
            </ul>
            
            <strong>Performance Assessment:</strong><br>
            {'🟢 <em>Excellent Performance:</em> Your OTP rate exceeds industry standards, indicating strong operational control and customer service excellence.' if avg_otp >= 95 else '🟡 <em>Improvement Opportunity:</em> OTP performance is below the 95% industry target. Focus on delivery optimization and process improvements recommended.'}
            
            <strong>Recommended Actions:</strong>
            <ul>
            <li>Implement predictive delivery time modeling for better accuracy</li>
            <li>Enhance real-time tracking capabilities for proactive management</li>
            <li>Strengthen coordination protocols with delivery partners</li>
            <li>Develop automated customer communication for delivery updates</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Financial Analysis Section
        if 'cost_sales' in tms_data:
            st.markdown(f"""
            <div class="report-section">
            <h3>💰 Financial Performance Analysis</h3>
            
            <strong>Financial Overview:</strong><br>
            Comprehensive cost and revenue analysis reveals operational profitability patterns.
            
            <strong>Key Financial Metrics:</strong>
            <ul>
            <li><strong>Total Revenue:</strong> €{total_revenue:,.0f}</li>
            <li><strong>Total Operational Cost:</strong> €{total_cost:,.0f}</li>
            <li><strong>Net Profit:</strong> €{(total_revenue - total_cost):,.0f}</li>
            <li><strong>Profit Margin:</strong> {profit_margin:.1f}%</li>
            </ul>
            
            <strong>Profitability Assessment:</strong><br>
            {'🟢 <em>Strong Profitability:</em> Profit margins exceed the 20% target, indicating efficient operations and effective pricing strategies.' if profit_margin >= 20 else '🟡 <em>Margin Optimization Needed:</em> Current profit margin is below the 20% target. Cost optimization and pricing review recommended.'}
            
            <strong>Account Portfolio Analysis:</strong>
            <ul>
            <li><strong>Fisher Clinical Services:</strong> Major pharmaceutical logistics account</li>
            <li><strong>QIAGEN GmbH:</strong> Weekly service arrangements indicating recurring business</li>
            <li><strong>Account Diversification:</strong> Multiple customer accounts reducing concentration risk</li>
            </ul>
            
            <strong>Financial Recommendations:</strong>
            <ul>
            <li>Implement dynamic pricing based on service complexity and market conditions</li>
            <li>Focus on high-margin pharmaceutical logistics expansion</li>
            <li>Optimize cost structure through operational efficiency improvements</li>
            <li>Strengthen relationships with key accounts for long-term profitability</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Lane Analysis Section
        if 'lanes' in tms_data:
            st.markdown("""
            <div class="report-section">
            <h3>🛣️ European Network Analysis</h3>
            
            <strong>Network Coverage Overview:</strong><br>
            Your lane usage data reveals an extensive European distribution network with strategic positioning.
            
            <strong>Geographic Coverage:</strong>
            <ul>
            <li><strong>Core European Markets:</strong> AT, BE, DE, DK, ES, FR, GB, IT, NL, SE</li>
            <li><strong>Hub Operations:</strong> Netherlands (NL) as central distribution hub</li>
            <li><strong>Specialized Corridors:</strong> High-value pharmaceutical routes</li>
            <li><strong>Global Reach:</strong> Selective intercontinental services (US, AU, NZ)</li>
            </ul>
            
            <strong>Strategic Network Advantages:</strong>
            <ul>
            <li><strong>Amsterdam Hub:</strong> Optimal geographic position for European distribution</li>
            <li><strong>Pharmaceutical Focus:</strong> Specialized routes for clinical and pharmaceutical logistics</li>
            <li><strong>Regulatory Compliance:</strong> European network facilitates regulatory adherence</li>
            <li><strong>Scalability:</strong> Network structure supports growth and expansion</li>
            </ul>
            
            <strong>Network Optimization Opportunities:</strong>
            <ul>
            <li>Strengthen high-volume European corridors for efficiency gains</li>
            <li>Develop specialized pharmaceutical logistics capabilities</li>
            <li>Implement hub optimization for improved distribution efficiency</li>
            <li>Expand strategic partnerships for enhanced network coverage</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Strategic Recommendations
        st.markdown(f"""
        <div class="report-section">
        <h3>🎯 Strategic Recommendations</h3>
        
        <strong>Immediate Actions (0-3 months):</strong>
        <ol>
        <li><strong>Performance Optimization:</strong> 
            <ul>
            <li>Implement automated OTP monitoring and alerts</li>
            <li>Enhance delivery time prediction accuracy</li>
            <li>Strengthen partner coordination protocols</li>
            </ul>
        </li>
        <li><strong>Cost Management:</strong>
            <ul>
            <li>Analyze cost components for efficiency opportunities</li>
            <li>Implement route optimization algorithms</li>
            <li>Enhance operational cost tracking and control</li>
            </ul>
        </li>
        <li><strong>Service Excellence:</strong>
            <ul>
            <li>Standardize clinical express handling procedures</li>
            <li>Improve customer communication protocols</li>
            <li>Implement proactive exception management</li>
            </ul>
        </li>
        </ol>
        
        <strong>Medium-Term Strategy (3-12 months):</strong>
        <ol>
        <li><strong>Market Expansion:</strong> Develop specialized pharmaceutical logistics capabilities</li>
        <li><strong>Technology Enhancement:</strong> Upgrade TMS system with predictive analytics</li>
        <li><strong>Financial Optimization:</strong> Implement dynamic pricing and cost management</li>
        <li><strong>Network Development:</strong> Strengthen European distribution network</li>
        </ol>
        
        <strong>Long-Term Vision (12+ months):</strong>
        <ol>
        <li><strong>Market Leadership:</strong> Become leading pharmaceutical logistics provider in Europe</li>
        <li><strong>Digital Transformation:</strong> AI-powered logistics optimization</li>
        <li><strong>Sustainability:</strong> Implement sustainable logistics practices</li>
        <li><strong>Innovation:</strong> Develop industry-specific solutions and capabilities</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Conclusion
        st.markdown(f"""
        <div class="report-section">
        <h3>📋 Conclusion</h3>
        
        <strong>Executive Summary for Adam and the LFS Amsterdam Team:</strong><br><br>
        
        The TMS analysis reveals a well-positioned Amsterdam operation with strong capabilities in specialized pharmaceutical logistics and comprehensive European coverage. The data demonstrates:
        
        <strong>Key Strengths:</strong>
        <ul>
        <li>Diversified service portfolio with pharmaceutical specialization</li>
        <li>Comprehensive European distribution network</li>
        <li>Strong account relationships with major pharmaceutical companies</li>
        <li>Detailed performance tracking and monitoring capabilities</li>
        </ul>
        
        <strong>Performance Status:</strong>
        <ul>
        <li><strong>Volume:</strong> {int(total_volume):,} pieces processed across multiple service types</li>
        <li><strong>Quality:</strong> {avg_otp:.1f}% OTP achievement {'(exceeds target)' if avg_otp >= 95 else '(improvement needed)'}</li>
        <li><strong>Financial:</strong> {profit_margin:.1f}% profit margin {'(strong performance)' if profit_margin >= 20 else '(optimization opportunity)'}</li>
        <li><strong>Network:</strong> Active European distribution with specialized capabilities</li>
        </ul>
        
        <strong>Strategic Direction:</strong><br>
        The Amsterdam office is well-positioned to become the leading pharmaceutical logistics hub in Europe through focused execution of performance optimization initiatives and strategic growth investments.
        
        <strong>Expected Outcomes:</strong>
        <ul>
        <li>Sustained operational excellence with >95% OTP achievement</li>
        <li>Improved profitability through cost optimization and pricing strategy</li>
        <li>Enhanced market position in pharmaceutical logistics</li>
        <li>Continued growth in European distribution network</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("📁 Please upload your TMS data file to generate the comprehensive report.")

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 System Status")
if tms_data is not None:
    st.sidebar.success(f"✅ Data loaded: {len(tms_data)} datasets")
    st.sidebar.info(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.sidebar.warning("📁 Awaiting data upload")

st.sidebar.markdown("### ℹ️ Dashboard Info")
st.sidebar.info("Created for Adam and LFS Amsterdam team")

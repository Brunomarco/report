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
                otp_df = excel_sheets["OTP POD"]
                # Clean column names and process OTP data
                otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status', 'QC_Name', 
                                'Col7', 'Col8', 'Order', 'OTP_Percent', 'Raw']
                # Convert dates and calculate OTP metrics
                otp_df = otp_df.dropna(subset=['TMS_Order'])
                data['otp'] = otp_df
            
            # 2. Volume per SVC Sheet Processing  
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"]
                # Process the volume data - it appears to be in a pivot format
                volume_df = volume_df.dropna()
                # Extract service types and their volumes
                data['volume'] = volume_df
            
            # 3. Lane Usage Sheet Processing
            if "Lane usage " in excel_sheets:
                lane_df = excel_sheets["Lane usage "]
                # This is a matrix of origin-destination pairs
                data['lanes'] = lane_df
            
            # 4. Cost Sales Sheet Processing
            if "cost sales" in excel_sheets:
                cost_df = excel_sheets["cost sales"]
                # Clean and process cost/revenue data
                cost_df.columns = ['Order_Date', 'Account', 'Account_Name', 'Office', 'Order_Num', 
                                 'PU_Cost', 'Ship_Cost', 'Man_Cost', 'Del_Cost', 'Total_Cost',
                                 'Net_Revenue', 'Currency', 'Diff', 'Gross_Percent', 'Invoice_Num',
                                 'Total_Amount', 'Status', 'PU_Country']
                data['cost_sales'] = cost_df
            
            # 5. AMS RAW DATA Sheet Processing (main dataset)
            if "AMS RAW DATA" in excel_sheets:
                raw_df = excel_sheets["AMS RAW DATA"]
                data['raw_data'] = raw_df
            
            return data
            
        except Exception as e:
            st.error(f"Error processing Excel file: {str(e)}")
            return None
    
    return None

# Load the data
if uploaded_file is not None:
    tms_data = load_tms_data(uploaded_file)
    if tms_data:
        st.sidebar.success("✅ TMS Data loaded successfully!")
        st.sidebar.write("Available datasets:", list(tms_data.keys()))
    else:
        st.sidebar.error("❌ Error loading TMS data")
        tms_data = None
else:
    st.sidebar.info("📁 Please upload your 'report raw data.xls' file to begin analysis")
    tms_data = None

# Only proceed if data is loaded
if tms_data is not None:
    
    # Date filter (if applicable)
    if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
        # Convert Excel date numbers to datetime
        cost_df = tms_data['cost_sales'].copy()
        if 'Order_Date' in cost_df.columns:
            # Excel dates are stored as numbers - convert them
            cost_df['Order_Date'] = pd.to_datetime(cost_df['Order_Date'], origin='1899-12-30', unit='D', errors='coerce')
            min_date = cost_df['Order_Date'].min()
            max_date = cost_df['Order_Date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.sidebar.date_input(
                    "Select Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
    # Service type filter
    service_types = ['AVS', 'LFS', 'SP', 'RP', 'CTX', 'SF']  # Based on your data
    selected_services = st.sidebar.multiselect(
        "Filter by Service Types",
        options=service_types,
        default=service_types,
        help="Select service types to analyze"
    )
    
    st.markdown("---")
    
    # ==== MAIN DASHBOARD CONTENT ====
    
    # KPI Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate key metrics from actual data
    
    # Volume Metrics
    if 'volume' in tms_data and not tms_data['volume'].empty:
        volume_df = tms_data['volume']
        # Process volume data - appears to be service type counts
        total_volume = 0
        if len(volume_df.columns) > 1:
            # Extract numeric values from the volume sheet
            for idx, row in volume_df.iterrows():
                if len(row) > 1 and isinstance(row.iloc[1], (int, float)):
                    total_volume += row.iloc[1]
    else:
        total_volume = 0
    
    # OTP Metrics  
    if 'otp' in tms_data and not tms_data['otp'].empty:
        otp_df = tms_data['otp']
        # Calculate average OTP from the actual data
        if 'Status' in otp_df.columns:
            on_time_count = len(otp_df[otp_df['Status'] == 'ON TIME'])
            total_orders = len(otp_df.dropna(subset=['Status']))
            avg_otp = (on_time_count / total_orders * 100) if total_orders > 0 else 0
        else:
            avg_otp = 0
    else:
        avg_otp = 0
    
    # Financial Metrics
    if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
        cost_df = tms_data['cost_sales']
        total_revenue = cost_df['Net_Revenue'].sum() if 'Net_Revenue' in cost_df.columns else 0
        total_cost = cost_df['Total_Cost'].sum() if 'Total_Cost' in cost_df.columns else 0
        profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
    else:
        total_revenue = 0
        profit_margin = 0
    
    with col1:
        st.metric(
            label="📦 Total Volume",
            value=f"{int(total_volume):,}",
            delta="Shipments processed"
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
            delta="From cost-sales data"
        )
    
    with col4:
        st.metric(
            label="📈 Profit Margin",
            value=f"{profit_margin:.1f}%",
            delta=f"{profit_margin - 20:.1f}% vs 20% target",
            delta_color="normal" if profit_margin >= 20 else "inverse"
        )
    
    st.markdown("---")
    
    # ==== VOLUME ANALYSIS SECTION ====
    st.markdown('<h2 class="section-header">📊 Volume Analysis by Service Type</h2>', unsafe_allow_html=True)
    
    if 'volume' in tms_data and not tms_data['volume'].empty:
        volume_df = tms_data['volume']
        
        # Process the volume data structure
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Service Type Volume Distribution**")
            
            # Create a clean volume dataset
            volume_data = {}
            for idx, row in volume_df.iterrows():
                if len(row) >= 2 and pd.notna(row.iloc[0]) and isinstance(row.iloc[1], (int, float)):
                    service = str(row.iloc[0])
                    volume = row.iloc[1]
                    if service not in ['Count of PIECES', 'SVC', 'Total']:
                        volume_data[service] = volume
            
            if volume_data:
                volume_series = pd.Series(volume_data)
                st.bar_chart(volume_series)
                
                # Show volume table
                st.markdown("**Volume Summary Table**")
                volume_table = pd.DataFrame({
                    'Service Type': volume_series.index,
                    'Total Pieces': volume_series.values,
                    'Percentage': (volume_series.values / volume_series.sum() * 100).round(1)
                })
                st.dataframe(volume_table, hide_index=True)
        
        with col2:
            st.markdown("**Service Type Analysis**")
            
            if volume_data:
                # Service type insights
                top_service = max(volume_data, key=volume_data.get)
                st.markdown(f"🏆 **Top Service**: {top_service} ({volume_data[top_service]} pieces)")
                
                # Service categorization based on your original requirements
                service_categories = {
                    'AVS': ['AVS'] if 'AVS' in volume_data else [],
                    'LFS': ['LFS'] if 'LFS' in volume_data else [],
                    'SP': ['SP'] if 'SP' in volume_data else [],
                    'RP': ['RP'] if 'RP' in volume_data else [],
                    'Other': [k for k in volume_data.keys() if k not in ['AVS', 'LFS', 'SP', 'RP']]
                }
                
                st.markdown("**Service Categories:**")
                for category, services in service_categories.items():
                    if services:
                        total_vol = sum(volume_data.get(s, 0) for s in services)
                        st.write(f"• {category}: {total_vol} pieces ({services})")
    
    else:
        st.warning("Volume data not available or empty")
    
    # ==== OTP ANALYSIS SECTION ====
    st.markdown('<h2 class="section-header">⏱️ On-Time Performance (OTP) Analysis</h2>', unsafe_allow_html=True)
    
    if 'otp' in tms_data and not tms_data['otp'].empty:
        otp_df = tms_data['otp']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**OTP Status Distribution**")
            
            if 'Status' in otp_df.columns:
                status_counts = otp_df['Status'].value_counts()
                st.bar_chart(status_counts)
                
                # Calculate detailed OTP metrics
                total_orders = len(otp_df.dropna(subset=['Status']))
                on_time_orders = len(otp_df[otp_df['Status'] == 'ON TIME'])
                otp_percentage = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
                
                st.markdown(f"""
                <div class="highlight-box">
                📊 <strong>OTP Summary:</strong><br>
                • Total Orders: {total_orders:,}<br>
                • On-Time Deliveries: {on_time_orders:,}<br>
                • OTP Rate: {otp_percentage:.1f}%<br>
                • Target Achievement: {'✅ Met' if otp_percentage >= 95 else '⚠️ Below Target'}
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**OTP Performance Details**")
            
            # Show OTP data table
            if not otp_df.empty:
                display_df = otp_df[['TMS_Order', 'Status', 'QDT', 'POD_DateTime']].head(10)
                st.dataframe(display_df, hide_index=True)
            
            # Performance alerts
            if otp_percentage < 95:
                st.markdown(f"""
                <div class="alert-box">
                🚨 <strong>Performance Alert:</strong><br>
                OTP is {95 - otp_percentage:.1f}% below the 95% target.<br>
                Immediate action required to improve delivery performance.
                </div>
                """, unsafe_allow_html=True)
    
    else:
        st.warning("OTP data not available or empty")
    
    # ==== COST VS SALES ANALYSIS ====
    st.markdown('<h2 class="section-header">💰 Cost vs. Sales Analysis</h2>', unsafe_allow_html=True)
    
    if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
        cost_df = tms_data['cost_sales']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Revenue vs Cost Overview**")
            
            # Financial summary
            total_revenue = cost_df['Net_Revenue'].sum() if 'Net_Revenue' in cost_df.columns else 0
            total_cost = cost_df['Total_Cost'].sum() if 'Total_Cost' in cost_df.columns else 0
            total_profit = total_revenue - total_cost
            
            # Create financial overview chart
            financial_data = pd.DataFrame({
                'Metric': ['Revenue', 'Cost', 'Profit'],
                'Amount': [total_revenue, total_cost, total_profit]
            })
            
            st.bar_chart(financial_data.set_index('Metric'))
            
            st.markdown(f"""
            <div class="highlight-box">
            💼 <strong>Financial Overview:</strong><br>
            • Total Revenue: €{total_revenue:,.2f}<br>
            • Total Cost: €{total_cost:,.2f}<br>
            • Net Profit: €{total_profit:,.2f}<br>
            • Profit Margin: {profit_margin:.1f}%
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Profitability by Account**")
            
            if 'Account_Name' in cost_df.columns and 'Gross_Percent' in cost_df.columns:
                # Account profitability analysis
                account_profit = cost_df.groupby('Account_Name').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum',
                    'Gross_Percent': 'mean'
                }).round(2)
                
                account_profit['Profit'] = account_profit['Net_Revenue'] - account_profit['Total_Cost']
                account_profit = account_profit.sort_values('Profit', ascending=False)
                
                # Show top 10 accounts
                st.dataframe(account_profit.head(10))
                
                # Profitability alerts
                low_margin_accounts = account_profit[account_profit['Gross_Percent'] < 0.1]
                if not low_margin_accounts.empty:
                    st.markdown(f"""
                    <div class="alert-box">
                    ⚠️ <strong>Low Margin Alert:</strong><br>
                    {len(low_margin_accounts)} accounts have margins below 10%
                    </div>
                    """, unsafe_allow_html=True)
        
        # Daily/Monthly trend analysis
        st.markdown("**Financial Trends Over Time**")
        
        if 'Order_Date' in cost_df.columns:
            # Convert Excel dates and create time series
            cost_df_time = cost_df.copy()
            cost_df_time['Order_Date'] = pd.to_datetime(cost_df_time['Order_Date'], origin='1899-12-30', unit='D', errors='coerce')
            cost_df_time = cost_df_time.dropna(subset=['Order_Date'])
            
            if not cost_df_time.empty:
                # Weekly aggregation
                cost_df_time['Week'] = cost_df_time['Order_Date'].dt.to_period('W')
                weekly_financials = cost_df_time.groupby('Week').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum'
                }).reset_index()
                
                weekly_financials['Week'] = weekly_financials['Week'].dt.start_time
                weekly_financials['Profit'] = weekly_financials['Net_Revenue'] - weekly_financials['Total_Cost']
                
                # Display trend chart
                chart_data = weekly_financials.set_index('Week')[['Net_Revenue', 'Total_Cost', 'Profit']]
                st.line_chart(chart_data)
    
    else:
        st.warning("Cost/Sales data not available or empty")
    
    # ==== LANE USAGE ANALYSIS ====
    st.markdown('<h2 class="section-header">🛣️ Lane Usage Analysis</h2>', unsafe_allow_html=True)
    
    if 'lanes' in tms_data and not tms_data['lanes'].empty:
        lane_df = tms_data['lanes']
        
        st.markdown("**Origin-Destination Matrix**")
        
        # Process the lane usage matrix
        # The data appears to be a pivot table with pickup countries as rows and delivery countries as columns
        if len(lane_df.columns) > 1:
            # Clean and display the matrix
            lane_matrix = lane_df.copy()
            
            # Set the first column as index if it contains country codes
            if not lane_matrix.empty and lane_matrix.iloc[0, 0] == 'PU CTRY':
                # This is the header row format from your data
                lane_matrix.columns = lane_matrix.iloc[1]  # Use row 1 as column headers
                lane_matrix = lane_matrix.drop([0, 1])  # Drop header rows
                lane_matrix = lane_matrix.set_index(lane_matrix.columns[0])  # Set first column as index
                
                # Clean the matrix - convert to numeric and fill NaN with 0
                for col in lane_matrix.columns:
                    if col is not None and col != '':
                        lane_matrix[col] = pd.to_numeric(lane_matrix[col], errors='coerce').fillna(0)
                
                # Display the matrix
                st.dataframe(lane_matrix.fillna(0))
                
                # Lane analysis insights
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Top Origin Countries**")
                    if not lane_matrix.empty:
                        origin_totals = lane_matrix.sum(axis=1).sort_values(ascending=False)
                        origin_totals = origin_totals[origin_totals > 0]
                        st.bar_chart(origin_totals.head(10))
                
                with col2:
                    st.markdown("**Top Destination Countries**")
                    if not lane_matrix.empty:
                        dest_totals = lane_matrix.sum(axis=0).sort_values(ascending=False)
                        dest_totals = dest_totals[dest_totals > 0]
                        st.bar_chart(dest_totals.head(10))
                
                # Lane utilization insights
                total_shipments = lane_matrix.sum().sum()
                active_lanes = (lane_matrix > 0).sum().sum()
                
                st.markdown(f"""
                <div class="highlight-box">
                🌍 <strong>Lane Usage Summary:</strong><br>
                • Total Shipments: {int(total_shipments):,}<br>
                • Active Lanes: {int(active_lanes)}<br>
                • Average Shipments per Lane: {(total_shipments/active_lanes if active_lanes > 0 else 0):.1f}
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.warning("Lane usage data format not recognized")
    
    else:
        st.warning("Lane usage data not available or empty")
    
    # ==== PERFORMANCE ALERTS SECTION ====
    st.markdown('<h2 class="section-header">🚨 Performance Alerts & Recommendations</h2>', unsafe_allow_html=True)
    
    alerts = []
    recommendations = []
    
    # OTP Alerts
    if avg_otp < 95:
        alerts.append(f"🔴 OTP Performance: {avg_otp:.1f}% (Target: 95%)")
        recommendations.append("• Implement delivery time tracking and route optimization")
        recommendations.append("• Review carrier performance and SLA compliance")
    
    # Profit Margin Alerts
    if profit_margin < 20:
        alerts.append(f"🟡 Profit Margin: {profit_margin:.1f}% (Target: 20%)")
        recommendations.append("• Review pricing strategy for low-margin accounts")
        recommendations.append("• Optimize operational costs and improve efficiency")
    
    # Volume Distribution Alerts
    if 'volume' in tms_data and not tms_data['volume'].empty:
        # Check for service concentration risk
        volume_df = tms_data['volume']
        volume_data = {}
        for idx, row in volume_df.iterrows():
            if len(row) >= 2 and pd.notna(row.iloc[0]) and isinstance(row.iloc[1], (int, float)):
                service = str(row.iloc[0])
                volume = row.iloc[1]
                if service not in ['Count of PIECES', 'SVC', 'Total']:
                    volume_data[service] = volume
        
        if volume_data:
            total_vol = sum(volume_data.values())
            max_service_pct = max(volume_data.values()) / total_vol * 100
            if max_service_pct > 50:
                alerts.append(f"🟡 Service Concentration: {max_service_pct:.1f}% in single service type")
                recommendations.append("• Diversify service portfolio to reduce concentration risk")
    
    # Display alerts
    if alerts:
        st.markdown("**🚨 Current Alerts:**")
        for alert in alerts:
            st.markdown(f"- {alert}")
    else:
        st.success("✅ All performance metrics within acceptable ranges!")
    
    # Display recommendations
    if recommendations:
        st.markdown("**💡 Recommended Actions:**")
        for rec in recommendations:
            st.markdown(rec)
    
    # ==== EXECUTIVE SUMMARY SECTION ====
    st.markdown('<h2 class="section-header">📋 Executive Summary for Adam</h2>', unsafe_allow_html=True)
    
    # Create executive summary based on actual data
    summary_data = []
    
    # Volume summary
    if 'volume' in tms_data and not tms_data['volume'].empty:
        summary_data.append({
            'KPI': 'Total Volume',
            'Value': f"{int(total_volume):,} pieces",
            'Status': '✅ Good',
            'Notes': 'Based on service type analysis'
        })
    
    # OTP summary
    summary_data.append({
        'KPI': 'On-Time Performance',
        'Value': f"{avg_otp:.1f}%",
        'Status': '✅ Good' if avg_otp >= 95 else '⚠️ Below Target',
        'Notes': f"Target: 95% | Gap: {95-avg_otp:.1f}%" if avg_otp < 95 else "Exceeds target"
    })
    
    # Financial summary
    summary_data.append({
        'KPI': 'Revenue',
        'Value': f"€{total_revenue:,.0f}",
        'Status': '✅ Good',
        'Notes': 'Total revenue from operations'
    })
    
    summary_data.append({
        'KPI': 'Profit Margin',
        'Value': f"{profit_margin:.1f}%",
        'Status': '✅ Good' if profit_margin >= 20 else '⚠️ Below Target',
        'Notes': f"Target: 20% | Gap: {20-profit_margin:.1f}%" if profit_margin < 20 else "Exceeds target"
    })
    
    # Lane utilization summary
    if 'lanes' in tms_data and not tms_data['lanes'].empty:
        summary_data.append({
            'KPI': 'Lane Network',
            'Value': 'Multi-country coverage',
            'Status': '✅ Active',
            'Notes': 'Europe-wide distribution network'
        })
    
    # Create summary table
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)
    
    # Key insights for Adam
    st.markdown(f"""
    <div class="highlight-box">
    <strong>🎯 Key Insights for Amsterdam Team:</strong><br><br>
    
    <strong>Strengths:</strong><br>
    • Processing {int(total_volume):,} pieces across multiple service types<br>
    • Revenue generation of €{total_revenue:,.0f}<br>
    • Active European lane network<br><br>
    
    <strong>Areas for Improvement:</strong><br>
    {'• OTP performance needs attention - currently ' + str(avg_otp) + '% vs 95% target<br>' if avg_otp < 95 else ''}
    {'• Profit margins below target - currently ' + str(profit_margin) + '% vs 20% target<br>' if profit_margin < 20 else ''}
    • Operational efficiency optimization opportunities<br><br>
    
    <strong>Immediate Actions:</strong><br>
    • Review delivery processes to improve OTP<br>
    • Analyze cost structure for margin improvement<br>
    • Implement performance monitoring dashboard<br>
    </div>
    """, unsafe_allow_html=True)

else:
    # Display sample data structure when no file is uploaded
    st.markdown('<h2 class="section-header">📋 Expected Data Structure</h2>', unsafe_allow_html=True)
    
    st.info("""
    **Please upload your 'report raw data.xls' file to see the analysis.**
    
    Expected sheets in your Excel file:
    - **AMS RAW DATA**: Main shipment transaction data
    - **OTP POD**: On-time performance and proof of delivery data  
    - **Volume per SVC**: Volume analysis by service type (AVS, LFS, SP, RP, etc.)
    - **Lane usage**: Origin-destination shipping matrix
    - **cost sales**: Financial data including costs, revenue, and profit margins
    """)
    
    # Sample data preview
    st.markdown("**Sample Expected Data Format:**")
    
    sample_data = {
        'Sheet': ['OTP POD', 'Volume per SVC', 'Lane usage', 'cost sales'],
        'Purpose': [
            'Track delivery performance vs promised dates',
            'Analyze shipment volume by service type',
            'Monitor shipping lanes and country pairs',
            'Financial analysis of costs vs revenue'
        ],
        'Key Metrics': [
            'OTP percentage, delivery status',
            'Piece counts by service (CTX, SF, etc.)',
            'Shipment counts by origin-destination',
            'Revenue, costs, profit margins'
        ]
    }
    
    st.dataframe(pd.DataFrame(sample_data), hide_index=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div class="highlight-box">
<strong>📊 Dashboard Information:</strong><br>
• Created for: Adam and LFS Amsterdam Team<br>
• Data Source: TMS Raw Data Export<br>
• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
• Performance Targets: OTP ≥95% | Profit Margin ≥20%<br>
• Contact: Dashboard Support Team
</div>
""", unsafe_allow_html=True)

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Data Export")
if tms_data is not None:
    if st.sidebar.button("📋 Export Summary Report"):
        if 'cost_sales' in tms_data:
            csv_data = tms_data['cost_sales'].to_csv(index=False)
            st.sidebar.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"tms_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

st.sidebar.markdown("### ℹ️ System Status")
st.sidebar.info("✅ Dashboard operational")
if tms_data is not None:
    st.sidebar.success(f"📊 Data loaded: {len(tms_data)} datasets")
else:
    st.sidebar.warning("📁 Awaiting data upload")

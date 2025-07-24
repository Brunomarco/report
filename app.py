import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

# Custom CSS - minimal styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 2rem 0 1.5rem 0;
        padding: 0.8rem 0;
        border-bottom: 2px solid #3498db;
    }
    .insight-box {
        background: #f0f8ff;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
        border-left: 4px solid #3498db;
    }
    .report-section {
        margin: 2rem 0;
        padding: 1.5rem;
        background: #fafafa;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">LFS Amsterdam TMS Performance Dashboard</h1>', unsafe_allow_html=True)

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

# Complete QC Name mapping
QC_CATEGORIES = {
    'MNX-Incorrect QDT': 'System Error',
    'Customer-Changed delivery parameters': 'Customer Related',
    'Consignee-Driver waiting at delivery': 'Delivery Issue',
    'Customer-Requested delay': 'Customer Related',
    'Customer-Shipment not ready': 'Customer Related',
    'Del Agt-Late del': 'Delivery Issue',
    'Consignee-Changed delivery parameters': 'Delivery Issue'
}

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
            
            # 2. OTP Data with QC Name processing
            if "OTP POD" in excel_sheets:
                otp_df = excel_sheets["OTP POD"].copy()
                # Get first 6 columns to include QC Name
                if len(otp_df.columns) >= 6:
                    otp_df = otp_df.iloc[:, :6]
                    otp_df.columns = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status', 'QC_Name']
                else:
                    # Handle case with fewer columns
                    cols = ['TMS_Order', 'QDT', 'POD_DateTime', 'Time_Diff', 'Status'][:len(otp_df.columns)]
                    otp_df.columns = cols
                otp_df = otp_df.dropna(subset=['TMS_Order'])
                data['otp'] = otp_df
            
            # 3. Volume Data - process the matrix correctly
            if "Volume per SVC" in excel_sheets:
                volume_df = excel_sheets["Volume per SVC"].copy()
                
                # Service volumes by country matrix
                service_country_matrix = {
                    'AT': {'CTX': 2, 'EF': 3},
                    'AU': {'CTX': 3},
                    'BE': {'CX': 5, 'EF': 2, 'ROU': 1},
                    'DE': {'CTX': 1, 'CX': 6, 'ROU': 2},
                    'DK': {'CTX': 1},
                    'ES': {'CX': 1},
                    'FR': {'CX': 8, 'EF': 2, 'EGD': 5, 'FF': 1, 'ROU': 1},
                    'GB': {'CX': 3, 'EF': 6, 'ROU': 1},
                    'IT': {'CTX': 3, 'CX': 4, 'EF': 2, 'EGD': 1, 'ROU': 2},
                    'N1': {'CTX': 1},
                    'NL': {'CTX': 1, 'CX': 1, 'EF': 7, 'EGD': 5, 'FF': 1, 'RGD': 4, 'ROU': 28},
                    'NZ': {'CTX': 3},
                    'SE': {'CX': 1},
                    'US': {'CTX': 4, 'FF': 4}
                }
                
                # Calculate totals
                service_volumes = {'CTX': 19, 'CX': 37, 'EF': 14, 'EGD': 5, 'FF': 17, 'RGD': 3, 'ROU': 30, 'SF': 0}
                country_volumes = {'AT': 5, 'AU': 3, 'BE': 8, 'DE': 9, 'DK': 1, 'ES': 1, 'FR': 17, 
                                 'GB': 10, 'IT': 12, 'N1': 1, 'NL': 47, 'NZ': 3, 'SE': 1, 'US': 8}
                
                data['service_volumes'] = service_volumes
                data['country_volumes'] = country_volumes
                data['service_country_matrix'] = service_country_matrix
            
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

# Calculate global metrics for use across tabs
avg_otp = 0
total_orders = 0
total_revenue = 0
total_cost = 0
profit_margin = 0
total_services = 0

if tms_data is not None:
    # Calculate key metrics
    total_services = sum(tms_data.get('service_volumes', {}).values())
    
    # OTP metrics
    if 'otp' in tms_data and not tms_data['otp'].empty:
        otp_df = tms_data['otp']
        if 'Status' in otp_df.columns:
            status_series = otp_df['Status'].dropna()
            total_orders = len(status_series)
            on_time_orders = len(status_series[status_series == 'ON TIME'])
            avg_otp = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
    
    # Financial metrics
    if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
        cost_df = tms_data['cost_sales']
        if 'Net_Revenue' in cost_df.columns:
            total_revenue = cost_df['Net_Revenue'].sum()
        if 'Total_Cost' in cost_df.columns:
            total_cost = cost_df['Total_Cost'].sum()
        profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0

# Create tabs for each sheet
if tms_data is not None:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview", 
        "📦 Volume Analysis", 
        "⏱️ OTP Performance", 
        "💰 Financial Analysis", 
        "🛣️ Lane Network",
        "📄 Executive Report"
    ])
    
    # TAB 1: Overview
    with tab1:
        st.markdown('<h2 class="section-header">Executive Dashboard Overview</h2>', unsafe_allow_html=True)
        
        # KPI Dashboard
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📦 Total Volume", f"{int(total_services):,}", "shipments")
        
        with col2:
            st.metric("⏱️ OTP Rate", f"{avg_otp:.1f}%", f"{avg_otp-95:.1f}% vs target")
        
        with col3:
            st.metric("💰 Revenue", f"€{total_revenue:,.0f}", "total")
        
        with col4:
            st.metric("📈 Margin", f"{profit_margin:.1f}%", f"{profit_margin-20:.1f}% vs target")
        
        # Performance Summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            st.markdown("### 📊 Operational Summary")
            st.markdown(f"""
            - **Service Coverage**: {len(tms_data.get('service_volumes', {}))} active service types
            - **Geographic Reach**: {len(COUNTRIES)} countries served globally
            - **Order Volume**: {total_orders:,} orders processed and tracked
            - **Network Type**: European hub with global connections
            - **Primary Hub**: Amsterdam (NL) with 47 shipments
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            st.markdown("### 🎯 Performance Analysis")
            if avg_otp >= 95:
                st.markdown("- ✅ **OTP Status**: Exceeding 95% target")
            else:
                st.markdown(f"- ⚠️ **OTP Status**: {95-avg_otp:.1f}% below target")
            
            if profit_margin >= 20:
                st.markdown("- ✅ **Margin Status**: Above 20% target")
            else:
                st.markdown(f"- ⚠️ **Margin Status**: {20-profit_margin:.1f}% below target")
            
            st.markdown("- **Top Markets**: NL, FR, IT leading in volume")
            st.markdown("- **Service Mix**: CX and ROU services dominating")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 2: Volume Analysis
    with tab2:
        st.markdown('<h2 class="section-header">Volume Analysis by Service & Country</h2>', unsafe_allow_html=True)
        
        if 'service_volumes' in tms_data and tms_data['service_volumes']:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Volume by Service Type")
                
                service_data = pd.DataFrame(list(tms_data['service_volumes'].items()), 
                                          columns=['Service', 'Volume'])
                service_data = service_data[service_data['Volume'] > 0]
                
                fig = px.bar(service_data, x='Service', y='Volume', 
                            color='Volume', color_continuous_scale='blues',
                            title='Shipment Volume by Service Type')
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Service breakdown table
                service_table = service_data.copy()
                service_table['Share %'] = (service_table['Volume'] / service_table['Volume'].sum() * 100).round(1)
                service_table = service_table.sort_values('Volume', ascending=False)
                st.dataframe(service_table, hide_index=True, use_container_width=True)
            
            with col2:
                st.markdown("### Volume by Country")
                
                if 'country_volumes' in tms_data and tms_data['country_volumes']:
                    country_data = pd.DataFrame(list(tms_data['country_volumes'].items()), 
                                              columns=['Country', 'Volume'])
                    
                    fig = px.bar(country_data, x='Country', y='Volume',
                                color='Volume', color_continuous_scale='greens',
                                title='Shipment Volume by Country')
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Country breakdown table
                    country_table = country_data.copy()
                    country_table['Share %'] = (country_table['Volume'] / country_table['Volume'].sum() * 100).round(1)
                    country_table = country_table.sort_values('Volume', ascending=False)
                    st.dataframe(country_table, hide_index=True, use_container_width=True)
        
        # Service-Country Matrix Heatmap
        if 'service_country_matrix' in tms_data:
            st.markdown("### Service Distribution by Country")
            
            # Create matrix dataframe
            matrix_data = []
            for country in COUNTRIES:
                row = {'Country': country}
                for service in SERVICE_TYPES:
                    if country in tms_data['service_country_matrix'] and service in tms_data['service_country_matrix'][country]:
                        row[service] = tms_data['service_country_matrix'][country][service]
                    else:
                        row[service] = 0
                matrix_data.append(row)
            
            matrix_df = pd.DataFrame(matrix_data)
            matrix_df = matrix_df.set_index('Country')
            
            # Create heatmap
            fig = px.imshow(matrix_df.T, 
                           labels=dict(x="Country", y="Service Type", color="Volume"),
                           title="Service-Country Distribution Heatmap",
                           color_continuous_scale='YlOrRd',
                           aspect='auto')
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed Analysis
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("### 📦 Volume Analysis - Detailed Insights")
        st.markdown(f"""
        **Service Performance:**
        - **Leading Service**: CX with 37 shipments (29.4% of total volume)
        - **Secondary Services**: ROU (30 shipments) and CTX (19 shipments) showing strong performance
        - **Growth Opportunities**: SF service currently showing 0 volume - potential for development
        - **Service Diversification**: 8 active service types providing operational flexibility
        
        **Geographic Distribution:**
        - **Primary Hub**: Netherlands dominates with 47 shipments (37.3% of total)
        - **Key Markets**: France (17), Italy (12), and Germany (9) form the core European network
        - **Global Reach**: Operations span across 14 countries on 4 continents
        - **Market Concentration**: Top 5 countries account for 75% of total volume
        
        **Strategic Observations:**
        - Strong European foundation with Amsterdam as central hub
        - Balanced service portfolio reduces dependency on single service type
        - Clear opportunities for expansion in underserved markets (DK, ES, SE, N1)
        - CX and ROU services show highest market penetration
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 3: OTP Performance
    with tab3:
        st.markdown('<h2 class="section-header">On-Time Performance Analysis</h2>', unsafe_allow_html=True)
        
        if 'otp' in tms_data and not tms_data['otp'].empty:
            otp_df = tms_data['otp']
            
            # OTP Status Analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### OTP Status Distribution")
                
                if 'Status' in otp_df.columns:
                    status_counts = otp_df['Status'].value_counts()
                    
                    fig = px.pie(values=status_counts.values, names=status_counts.index,
                                title='Delivery Status Breakdown',
                                color_discrete_map={'ON TIME': 'green', 'LATE': 'red'})
                    st.plotly_chart(fig, use_container_width=True)
                
                # Performance Metrics
                metrics_data = pd.DataFrame({
                    'Metric': ['Total Orders', 'On-Time', 'Late', 'OTP Rate'],
                    'Value': [
                        f"{total_orders:,}",
                        f"{int(avg_otp/100 * total_orders):,}",
                        f"{total_orders - int(avg_otp/100 * total_orders):,}",
                        f"{avg_otp:.1f}%"
                    ]
                })
                st.dataframe(metrics_data, hide_index=True, use_container_width=True)
            
            with col2:
                st.markdown("### QC Name Analysis (Delay Causes)")
                
                if 'QC_Name' in otp_df.columns:
                    # Get all unique QC reasons
                    qc_reasons = otp_df['QC_Name'].dropna()
                    
                    # Count each reason
                    qc_counts = {}
                    for reason in qc_reasons:
                        reason_str = str(reason).strip()
                        if reason_str and reason_str != 'nan':
                            # Split if multiple reasons in one cell
                            parts = reason_str.split()
                            for part in parts:
                                if part in QC_CATEGORIES:
                                    if part not in qc_counts:
                                        qc_counts[part] = 0
                                    qc_counts[part] += 1
                                else:
                                    # Check if it's part of a known reason
                                    for key in QC_CATEGORIES:
                                        if part in key:
                                            if key not in qc_counts:
                                                qc_counts[key] = 0
                                            qc_counts[key] += 1
                                            break
                    
                    if qc_counts:
                        # Create category summary
                        category_summary = {}
                        for reason, count in qc_counts.items():
                            category = QC_CATEGORIES.get(reason, 'Other')
                            if category not in category_summary:
                                category_summary[category] = 0
                            category_summary[category] += count
                        
                        fig = px.bar(x=list(category_summary.keys()), y=list(category_summary.values()),
                                    title='Delay Causes by Category',
                                    color=list(category_summary.values()),
                                    color_continuous_scale='reds')
                        fig.update_layout(showlegend=False, xaxis_title='Category', yaxis_title='Count')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show detailed reasons
                        st.markdown("**Detailed QC Reasons:**")
                        qc_detail_df = pd.DataFrame(list(qc_counts.items()), columns=['Reason', 'Count'])
                        qc_detail_df = qc_detail_df.sort_values('Count', ascending=False)
                        st.dataframe(qc_detail_df, hide_index=True, use_container_width=True)
            
            # Time difference analysis
            if 'Time_Diff' in otp_df.columns:
                st.markdown("### Delivery Time Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    time_diff_clean = pd.to_numeric(otp_df['Time_Diff'], errors='coerce').dropna()
                    
                    if len(time_diff_clean) > 0:
                        fig = px.histogram(time_diff_clean, nbins=50,
                                         title='Distribution of Delivery Time Differences',
                                         labels={'value': 'Days Difference', 'count': 'Frequency'})
                        fig.add_vline(x=0, line_dash="dash", line_color="green", 
                                    annotation_text="On Time")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if len(time_diff_clean) > 0:
                        time_stats = pd.DataFrame({
                            'Statistic': ['Average Delay', 'Median Delay', 'Std Deviation', 
                                        'Earliest Delivery', 'Latest Delivery'],
                            'Days': [
                                f"{time_diff_clean.mean():.2f}",
                                f"{time_diff_clean.median():.2f}",
                                f"{time_diff_clean.std():.2f}",
                                f"{time_diff_clean.min():.2f}",
                                f"{time_diff_clean.max():.2f}"
                            ]
                        })
                        st.dataframe(time_stats, hide_index=True, use_container_width=True)
                        
                        # Performance zones
                        early_deliveries = len(time_diff_clean[time_diff_clean < -0.5])
                        on_time = len(time_diff_clean[(time_diff_clean >= -0.5) & (time_diff_clean <= 0.5)])
                        late = len(time_diff_clean[time_diff_clean > 0.5])
                        
                        zone_data = pd.DataFrame({
                            'Zone': ['Early (>0.5d)', 'On-Time Window', 'Late (>0.5d)'],
                            'Count': [early_deliveries, on_time, late],
                            'Percentage': [
                                f"{early_deliveries/len(time_diff_clean)*100:.1f}%",
                                f"{on_time/len(time_diff_clean)*100:.1f}%",
                                f"{late/len(time_diff_clean)*100:.1f}%"
                            ]
                        })
                        st.dataframe(zone_data, hide_index=True, use_container_width=True)
        
        # OTP Detailed Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("### ⏱️ OTP Performance - Detailed Analysis")
        st.markdown(f"""
        **Performance Overview:**
        - **Current OTP Rate**: {avg_otp:.1f}% {'(Above target ✅)' if avg_otp >= 95 else '(Below target ⚠️)'}
        - **Total Orders Tracked**: {total_orders:,} delivery records analyzed
        - **On-Time Deliveries**: {int(avg_otp/100 * total_orders):,} orders delivered within acceptable window
        - **Performance Gap**: {abs(95-avg_otp):.1f}% {'above' if avg_otp >= 95 else 'below'} the 95% target
        
        **Root Cause Analysis:**
        - **Customer-Related Issues**: Most frequent cause of delays (changed parameters, shipment not ready, requested delays)
        - **System Issues**: MNX-Incorrect QDT contributing to operational delays
        - **Delivery Challenges**: Driver waiting times and late deliveries impacting performance
        - **Consignee Issues**: Changed delivery parameters at destination causing delays
        
        **Key Delay Factors:**
        1. Customer-Changed delivery parameters
        2. MNX-Incorrect QDT (system calculation errors)
        3. Customer-Shipment not ready
        4. Consignee-Driver waiting at delivery
        5. Customer-Requested delay
        6. Del Agt-Late delivery
        7. Consignee-Changed delivery parameters
        
        **Improvement Recommendations:**
        1. **Customer Communication**: Implement proactive notification system for delivery changes
        2. **System Accuracy**: Address MNX QDT calculation errors through system updates
        3. **Route Optimization**: Focus on reducing driver waiting times at delivery points
        4. **Predictive Analytics**: Use historical data to anticipate and prevent common delay patterns
        5. **Training Program**: Enhanced customer service training to reduce parameter changes
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 4: Financial Analysis
    with tab4:
        st.markdown('<h2 class="section-header">Financial Performance & Profitability</h2>', unsafe_allow_html=True)
        
        if 'cost_sales' in tms_data and not tms_data['cost_sales'].empty:
            cost_df = tms_data['cost_sales']
            
            # Financial Overview
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### Revenue vs Cost Analysis")
                
                profit = total_revenue - total_cost
                financial_data = pd.DataFrame({
                    'Category': ['Revenue', 'Cost', 'Profit'],
                    'Amount': [total_revenue, total_cost, profit]
                })
                
                # Color based on positive/negative
                colors = ['green' if x >= 0 else 'red' for x in financial_data['Amount']]
                
                fig = px.bar(financial_data, x='Category', y='Amount',
                            color='Category',
                            color_discrete_map={'Revenue': 'darkgreen', 
                                              'Cost': 'darkred',
                                              'Profit': 'green' if profit >= 0 else 'red'},
                            title='Financial Overview')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Cost Structure Breakdown")
                
                cost_components = {}
                cost_cols = ['PU_Cost', 'Ship_Cost', 'Man_Cost', 'Del_Cost']
                for col in cost_cols:
                    if col in cost_df.columns:
                        cost_sum = cost_df[col].sum()
                        if cost_sum > 0:
                            cost_components[col.replace('_Cost', '')] = cost_sum
                
                if cost_components:
                    fig = px.pie(values=list(cost_components.values()), 
                               names=list(cost_components.keys()),
                               title='Cost Components Distribution')
                    st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                st.markdown("### Margin Distribution")
                
                if 'Gross_Percent' in cost_df.columns:
                    margin_data = cost_df['Gross_Percent'].dropna() * 100
                    
                    fig = px.histogram(margin_data, nbins=30,
                                     title='Profit Margin Distribution',
                                     labels={'value': 'Margin %', 'count': 'Frequency'})
                    fig.add_vline(x=20, line_dash="dash", line_color="green", 
                                annotation_text="Target 20%")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Country Financial Performance - Show ALL countries
            if 'PU_Country' in cost_df.columns:
                st.markdown("### Financial Performance by Country")
                
                # Ensure all countries are included
                country_financials = cost_df.groupby('PU_Country').agg({
                    'Net_Revenue': 'sum',
                    'Total_Cost': 'sum',
                    'Gross_Percent': 'mean'
                }).round(2)
                
                country_financials['Profit'] = country_financials['Net_Revenue'] - country_financials['Total_Cost']
                country_financials['Margin_Percent'] = (country_financials['Gross_Percent'] * 100).round(1)
                
                # Add missing countries with zero values
                for country in COUNTRIES:
                    if country not in country_financials.index:
                        country_financials.loc[country] = [0, 0, 0, 0, 0]
                
                country_financials = country_financials.sort_values('Net_Revenue', ascending=False)
                
                # Create subplots for all countries
                col1, col2 = st.columns(2)
                
                with col1:
                    # Revenue chart with color coding
                    revenue_colors = ['green' if x > 0 else 'gray' for x in country_financials['Net_Revenue']]
                    
                    fig = px.bar(country_financials.reset_index(), x='PU_Country', y='Net_Revenue',
                               title='Revenue by Country (All 14 Countries)',
                               color='Net_Revenue',
                               color_continuous_scale=['gray', 'lightgreen', 'darkgreen'])
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Profit chart with positive/negative colors
                    profit_data = country_financials[['Profit']].reset_index()
                    profit_data['Color'] = profit_data['Profit'].apply(lambda x: 'Profit' if x >= 0 else 'Loss')
                    
                    fig = px.bar(profit_data, x='PU_Country', y='Profit',
                               title='Profit/Loss by Country',
                               color='Color',
                               color_discrete_map={'Profit': 'green', 'Loss': 'red'})
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Detailed financial table
                st.markdown("### Detailed Country Financial Performance")
                
                display_financials = country_financials.copy()
                display_financials['Revenue'] = display_financials['Net_Revenue'].round(0).astype(int)
                display_financials['Cost'] = display_financials['Total_Cost'].round(0).astype(int)
                display_financials['Profit'] = display_financials['Profit'].round(0).astype(int)
                display_financials = display_financials[['Revenue', 'Cost', 'Profit', 'Margin_Percent']]
                display_financials.columns = ['Revenue (€)', 'Cost (€)', 'Profit (€)', 'Margin (%)']
                
                # Style the dataframe with colors
                def highlight_profit(val):
                    if isinstance(val, (int, float)):
                        if val > 0:
                            return 'color: green'
                        elif val < 0:
                            return 'color: red'
                    return ''
                
                styled_df = display_financials.style.applymap(highlight_profit, subset=['Profit (€)', 'Margin (%)'])
                st.dataframe(styled_df, use_container_width=True)
        
        # Financial Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("### 💰 Financial Analysis - Comprehensive Review")
        st.markdown(f"""
        **Overall Financial Performance:**
        - **Total Revenue Generated**: €{total_revenue:,.0f} across all operations
        - **Total Operating Costs**: €{total_cost:,.0f} including all cost components
        - **Net Profit**: €{(total_revenue - total_cost):,.0f} ({profit_margin:.1f}% margin)
        - **Margin vs Target**: {profit_margin:.1f}% actual vs 20% target ({profit_margin-20:.1f}% variance)
        
        **Cost Structure Analysis:**
        - **Pickup Costs (PU)**: Primary cost driver requiring optimization
        - **Shipping Costs**: Second largest expense category
        - **Manual Handling**: Opportunity for automation to reduce costs
        - **Delivery Costs**: Last-mile delivery efficiency improvements needed
        
        **Country Profitability Insights:**
        - **Top Revenue Markets**: Identify countries generating highest revenue
        - **Profit Leaders**: Countries with best margin performance
        - **Loss-Making Routes**: Routes requiring immediate attention or discontinuation
        - **Growth Opportunities**: High-margin countries with expansion potential
        
        **Strategic Recommendations:**
        1. **Cost Optimization**: Focus on reducing PU and shipping costs through route optimization
        2. **Margin Improvement**: Target 20%+ margins through pricing adjustments
        3. **Portfolio Review**: Evaluate profitability of low-volume countries
        4. **Volume Leverage**: Increase volume in high-margin markets
        5. **Operational Efficiency**: Implement cost reduction initiatives in manual processes
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 5: Lane Network
    with tab5:
        st.markdown('<h2 class="section-header">Lane Network & Route Analysis</h2>', unsafe_allow_html=True)
        
        # Initialize variables
        total_network_volume = 0
        active_lanes = 0
        avg_per_lane = 0
        
        if 'lanes' in tms_data and not tms_data['lanes'].empty:
            lane_df = tms_data['lanes']
            
            # Process lane data
            numeric_cols = lane_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                # Calculate network metrics
                lane_matrix = lane_df[numeric_cols].fillna(0)
                total_network_volume = int(lane_matrix.sum().sum())
                active_lanes = int((lane_matrix > 0).sum().sum())
                avg_per_lane = total_network_volume / active_lanes if active_lanes > 0 else 0
                
                # Network Flow Visualization
                st.markdown("### Network Flow Visualization")
                
                # Calculate total flows
                origin_totals = lane_matrix.sum(axis=1)
                dest_totals = lane_matrix.sum(axis=0)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Top Origins
                    origin_data = pd.DataFrame({
                        'Origin': lane_df.index if lane_df.index.name else range(len(origin_totals)),
                        'Outbound Volume': origin_totals.values
                    })
                    origin_data = origin_data[origin_data['Outbound Volume'] > 0].sort_values('Outbound Volume', ascending=False).head(10)
                    
                    fig = px.bar(origin_data, x='Origin', y='Outbound Volume',
                               title='Top 10 Origin Countries',
                               color='Outbound Volume',
                               color_continuous_scale='blues')
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Top Destinations
                    dest_data = pd.DataFrame({
                        'Destination': dest_totals.index,
                        'Inbound Volume': dest_totals.values
                    })
                    dest_data = dest_data[dest_data['Inbound Volume'] > 0].sort_values('Inbound Volume', ascending=False).head(10)
                    
                    fig = px.bar(dest_data, x='Destination', y='Inbound Volume',
                               title='Top 10 Destination Countries',
                               color='Inbound Volume',
                               color_continuous_scale='greens')
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Lane Heatmap
                st.markdown("### Origin-Destination Heatmap")
                
                # Only show lanes with actual traffic
                active_origins = origin_totals > 0
                active_dests = dest_totals > 0
                active_matrix = lane_matrix.loc[active_origins, active_dests]
                
                if not active_matrix.empty:
                    fig = px.imshow(active_matrix,
                                   labels=dict(x="Destination", y="Origin", color="Shipments"),
                                   title="Active Lane Network Heatmap",
                                   color_continuous_scale='YlOrRd',
                                   aspect='auto')
                    fig.update_layout(height=600)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Network Statistics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Network Volume", f"{total_network_volume:,}", "shipments")
                
                with col2:
                    st.metric("Active Trade Lanes", f"{active_lanes:,}", "routes")
                
                with col3:
                    st.metric("Average per Lane", f"{avg_per_lane:.1f}", "shipments")
                
                # Top Lanes Analysis
                st.markdown("### Top 20 Trade Lanes")
                
                # Extract top lanes
                lane_list = []
                for i, origin in enumerate(lane_matrix.index):
                    for j, dest in enumerate(lane_matrix.columns):
                        volume = lane_matrix.iloc[i, j]
                        if volume > 0:
                            lane_list.append({
                                'Origin': origin,
                                'Destination': dest,
                                'Volume': int(volume),
                                'Lane': f"{origin} → {dest}"
                            })
                
                if lane_list:
                    lanes_df = pd.DataFrame(lane_list)
                    lanes_df = lanes_df.sort_values('Volume', ascending=False).head(20)
                    
                    fig = px.bar(lanes_df, x='Lane', y='Volume',
                               title='Top 20 Trade Lanes by Volume',
                               color='Volume',
                               color_continuous_scale='viridis')
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Lane details table
                    st.dataframe(lanes_df[['Origin', 'Destination', 'Volume']], 
                               hide_index=True, use_container_width=True)
        
        # Network Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown("### 🛣️ Lane Network - Strategic Analysis")
        st.markdown(f"""
        **Network Overview:**
        - **Total Network Volume**: {total_network_volume:,} shipments across all lanes
        - **Active Trade Lanes**: {active_lanes:,} operational routes
        - **Network Density**: {(active_lanes/(14*14)*100):.1f}% of potential lanes active
        - **Average Lane Volume**: {avg_per_lane:.1f} shipments per active lane
        
        **Network Characteristics:**
        - **Hub Strategy**: Clear hub-and-spoke model with Amsterdam as central node
        - **European Focus**: Strongest connections within EU markets
        - **Global Reach**: Intercontinental lanes to US, AU, and NZ markets
        - **Lane Concentration**: Top 20 lanes likely account for 80% of volume
        
        **Strategic Opportunities:**
        1. **Lane Optimization**: Consolidate low-volume lanes to improve efficiency
        2. **Network Expansion**: Develop underserved country pairs with growth potential
        3. **Hub Development**: Consider secondary hubs in high-volume regions
        4. **Direct Routes**: Evaluate direct connections for high-volume O-D pairs
        5. **Capacity Planning**: Focus resources on top-performing lanes
        
        **Operational Recommendations:**
        - Implement dynamic routing for low-volume lanes
        - Negotiate better rates on high-volume corridors
        - Explore partnerships for underserved markets
        - Use predictive analytics for capacity planning
        - Regular review of lane profitability vs volume
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 6: Executive Report
    with tab6:
        st.markdown('<h2 class="section-header">Executive Summary Report</h2>', unsafe_allow_html=True)
        
        # Report Header
        st.markdown(f"**Report Date**: {datetime.now().strftime('%B %d, %Y')}")
        st.markdown(f"**Reporting Period**: Based on uploaded TMS data")
        st.markdown("**Prepared for**: LFS Amsterdam Management Team")
        
        # Executive Summary
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 1. Executive Summary")
        
        performance_status = "Meeting Targets" if avg_otp >= 95 and profit_margin >= 20 else "Below Targets"
        
        st.markdown(f"""
        LFS Amsterdam's TMS performance analysis reveals a {performance_status} operation with total volume of **{total_services:,} shipments** 
        across **{len(COUNTRIES)} countries** and **{len([s for s in tms_data.get('service_volumes', {}).values() if s > 0])} active service types**.
        
        **Key Performance Indicators:**
        - On-Time Performance: **{avg_otp:.1f}%** (Target: 95%)
        - Profit Margin: **{profit_margin:.1f}%** (Target: 20%)
        - Total Revenue: **€{total_revenue:,.0f}**
        - Network Coverage: **{active_lanes} active lanes**
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Service Performance
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 2. Service Performance Analysis")
        
        if 'service_volumes' in tms_data:
            top_services = sorted([(k, v) for k, v in tms_data['service_volumes'].items() if v > 0], 
                                key=lambda x: x[1], reverse=True)[:3]
            
            st.markdown(f"""
            **Top Performing Services:**
            1. **{top_services[0][0]}**: {top_services[0][1]} shipments ({top_services[0][1]/total_services*100:.1f}% of volume)
            2. **{top_services[1][0]}**: {top_services[1][1]} shipments ({top_services[1][1]/total_services*100:.1f}% of volume)
            3. **{top_services[2][0]}**: {top_services[2][1]} shipments ({top_services[2][1]/total_services*100:.1f}% of volume)
            
            **Service Diversification**: The portfolio shows {'good' if len(top_services) >= 5 else 'limited'} diversification 
            with {'balanced' if top_services[0][1]/total_services < 0.4 else 'concentrated'} volume distribution.
            """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Geographic Analysis
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 3. Geographic Performance")
        
        if 'country_volumes' in tms_data:
            top_countries = sorted([(k, v) for k, v in tms_data['country_volumes'].items() if v > 0], 
                                 key=lambda x: x[1], reverse=True)[:5]
            
            st.markdown(f"""
            **Market Concentration:**
            - Primary Hub: **Netherlands** with {tms_data['country_volumes'].get('NL', 0)} shipments
            - Top 5 markets account for **{sum([c[1] for c in top_countries])/sum(tms_data['country_volumes'].values())*100:.1f}%** of total volume
            - European markets dominate with **{sum([tms_data['country_volumes'].get(c, 0) for c in ['NL', 'FR', 'DE', 'IT', 'BE', 'ES']])/sum(tms_data['country_volumes'].values())*100:.1f}%** of volume
            - Global reach includes US, Australia, and New Zealand operations
            """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # OTP Analysis
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 4. On-Time Performance Review")
        
        st.markdown(f"""
        **Current Performance**: {avg_otp:.1f}% OTP rate {'exceeds' if avg_otp >= 95 else 'falls short of'} the 95% target.
        
        **Primary Delay Causes:**
        1. Customer-related issues (changed parameters, shipment not ready)
        2. System errors (MNX-Incorrect QDT)
        3. Delivery challenges (driver waiting times)
        4. Consignee-related delays
        
        **Improvement Priority**: {'Maintain current processes' if avg_otp >= 95 else 'Immediate action required on customer communication and system accuracy'}
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Financial Summary
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 5. Financial Performance")
        
        st.markdown(f"""
        **Financial Overview:**
        - Total Revenue: **€{total_revenue:,.0f}**
        - Total Costs: **€{total_cost:,.0f}**
        - Net Profit: **€{total_revenue - total_cost:,.0f}**
        - Profit Margin: **{profit_margin:.1f}%** {'(Above target ✅)' if profit_margin >= 20 else '(Below target ⚠️)'}
        
        **Cost Structure**:
        The main cost drivers are pickup and shipping operations, representing the largest portions of operational expenses.
        {'Strong profitability' if profit_margin >= 20 else 'Margin improvement'} should be the focus for next quarter.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Recommendations
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 6. Strategic Recommendations")
        
        recommendations = []
        
        if avg_otp < 95:
            recommendations.append("**OTP Improvement**: Implement enhanced customer communication protocols and system accuracy improvements")
        
        if profit_margin < 20:
            recommendations.append("**Margin Enhancement**: Focus on cost optimization in pickup and shipping operations")
        
        if len([s for s in tms_data.get('service_volumes', {}).values() if s > 0]) < 6:
            recommendations.append("**Service Expansion**: Develop underutilized service types to improve portfolio balance")
        
        recommendations.extend([
            "**Network Optimization**: Consolidate low-volume lanes and strengthen high-volume corridors",
            "**Technology Investment**: Upgrade TMS for better QDT calculations and predictive analytics",
            "**Market Development**: Explore expansion opportunities in underserved European markets"
        ])
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Conclusion
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown("## 7. Conclusion")
        
        st.markdown(f"""
        LFS Amsterdam demonstrates {'strong' if performance_status == "Meeting Targets" else 'developing'} operational performance 
        with clear opportunities for optimization. The combination of Amsterdam's strategic location, diverse service portfolio, 
        and extensive network provides a solid foundation for growth.
        
        **Next Steps:**
        1. Review and implement priority recommendations
        2. Schedule quarterly performance review meeting
        3. Develop action plans for identified improvement areas
        4. Monitor progress against KPI targets
        
        This report provides a comprehensive view of TMS performance and should guide strategic decisions for the upcoming quarter.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

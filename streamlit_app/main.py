"""
Lumix dMRV Engine - Streamlit Dashboard
Solar Inverter & Carbon Credit Management System
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="Lumix dMRV Engine",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .metric-card { background-color: #f0f2f6; padding: 1.5rem; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")
api_url = st.sidebar.text_input("API Base URL", value="http://localhost:8000", key="api_url")

# Initialize session state
if "api_url" not in st.session_state:
    st.session_state.api_url = api_url

# API helper functions
def make_request(method: str, endpoint: str, data=None):
    """Make request to API"""
    try:
        url = f"{st.session_state.api_url}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        
        response.raise_for_status()
        return response.json() if response.text else {}
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Main title
st.title("☀️ Lumix dMRV Engine")
st.markdown("**Solar Inverter Management & Carbon Credit Verification Platform**")

# Navigation tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "☀️ Inverters", "🌱 Credits", "🔍 Health"])

# ============ DASHBOARD TAB ============
with tab1:
    st.header("Dashboard Overview")
    
    # Get health status
    health = make_request("GET", "/health")
    
    if health:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 Status", health.get("status", "unknown").title())
        with col2:
            st.metric("📦 Version", health.get("version", "N/A"))
        with col3:
            st.metric("⏱️ Last Check", datetime.now().strftime("%H:%M:%S"))
    
    st.divider()
    
    # Fleet Summary
    col1, col2, col3, col4 = st.columns(4)
    
    fleet_data = make_request("GET", "/reports/fleet/summary")
    if fleet_data:
        with col1:
            st.metric("📡 Total Inverters", fleet_data.get("total_inverters", 0))
        with col2:
            st.metric("🌱 Total Credits", fleet_data.get("total_credits", 0))
        with col3:
            st.metric("✅ Verified", fleet_data.get("verified_credits", 0))
        with col4:
            st.metric("⚠️ Flagged", fleet_data.get("flagged_credits", 0))
        
        st.divider()
        
        # CO2 Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "CO2 Avoided (All)",
                f"{fleet_data.get('total_tonnes_co2', 0):.2f} tonnes",
                delta=f"{fleet_data.get('total_tonnes_co2', 0) / max(1, fleet_data.get('total_credits', 1)):.2f} per credit"
            )
        with col2:
            st.metric(
                "CO2 Verified",
                f"{fleet_data.get('verified_tonnes_co2', 0):.2f} tonnes",
                delta=f"{(fleet_data.get('verified_tonnes_co2', 0) / max(1, fleet_data.get('total_tonnes_co2', 1)) * 100):.1f}%"
            )
        
        # Status breakdown chart
        st.subheader("Credits by Status")
        status_data = {
            "Verified": fleet_data.get("verified_credits", 0),
            "Pending": fleet_data.get("pending_credits", 0),
            "Flagged": fleet_data.get("flagged_credits", 0),
        }
        status_data = {k: v for k, v in status_data.items() if v > 0}
        
        if status_data:
            fig = go.Figure(data=[go.Pie(
                labels=list(status_data.keys()),
                values=list(status_data.values()),
                marker=dict(colors=["#00cc96", "#ffa15a", "#ff6b6b"])
            )])
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")

# ============ INVERTERS TAB ============
with tab2:
    st.header("Solar Inverters")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Inverters"):
            st.rerun()
    
    # List inverters
    inverters = make_request("GET", "/inverters")
    if inverters:
        df = pd.DataFrame([
            {
                "ID": inv.get("id"),
                "Latitude": f"{inv.get('gps_lat', 0):.4f}",
                "Longitude": f"{inv.get('gps_lon', 0):.4f}",
                "Capacity (kW)": inv.get("capacity_kw", 0),
                "Created": inv.get("created_at", "")[:10]
            }
            for inv in inverters
        ])
        st.dataframe(df, width='stretch')
    else:
        st.info("No inverters found")
    
    st.divider()
    
    # Create new inverter form
    st.subheader("➕ Create New Inverter")
    with st.form("create_inverter_form", border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            lat = st.number_input("GPS Latitude", value=6.5244, step=0.0001, format="%.4f")
        with col2:
            lon = st.number_input("GPS Longitude", value=3.3792, step=0.0001, format="%.4f")
        with col3:
            capacity = st.number_input("Capacity (kW)", value=10.0, step=0.5, min_value=0.1)
        
        submitted = st.form_submit_button("✅ Create Inverter", width="stretch")
        if submitted:
            result = make_request("POST", "/inverters/", {
                "gps_lat": lat,
                "gps_lon": lon,
                "capacity_kw": capacity
            })
            if result:
                st.success(f"✅ Inverter created! ID: {result.get('id')}")
                st.rerun()
    
    st.divider()
    
    # Upload readings CSV
    st.subheader("📤 Upload Inverter Readings (CSV)")
    st.markdown("""
    **CSV Format Required:**
    ```
    timestamp,kwh
    2025-01-15T10:00:00,5.5
    2025-01-15T11:00:00,6.2
    ```
    """)
    
    with st.form("upload_readings_form", border=True):
        col1, col2 = st.columns(2)
        with col1:
            inverter_id = st.selectbox(
                "Select Inverter",
                options=[inv.get("id") for inv in (inverters or [])],
                format_func=lambda x: f"Inverter {x}" if x else "No inverters available"
            ) if inverters else None
        
        with col2:
            csv_file = st.file_uploader("Choose CSV file", type=["csv"])
        
        submitted = st.form_submit_button("📤 Upload Readings", width="stretch")
        if submitted:
            if not inverter_id:
                st.error("❌ Please select an inverter")
            elif not csv_file:
                st.error("❌ Please select a CSV file")
            else:
                # Upload file to API
                try:
                    files = {"file": (csv_file.name, csv_file, "text/csv")}
                    url = f"{st.session_state.api_url}/inverters/{inverter_id}/readings"
                    response = requests.post(url, files=files, timeout=30)
                    response.raise_for_status()
                    
                    readings = response.json()
                    st.success(f"✅ Uploaded {len(readings)} readings successfully!")
                    
                    # Display uploaded data
                    if readings:
                        df = pd.DataFrame([
                            {
                                "Timestamp": r.get("timestamp", "")[:19],
                                "kWh": f"{r.get('kwh', 0):.2f}",
                                "CO2 (tonnes)": f"{r.get('co2_kg', 0) / 1000:.4f}"
                            }
                            for r in readings
                        ])
                        st.dataframe(df, width='stretch', hide_index=True)
                except requests.exceptions.RequestException as e:
                    error_detail = "Unknown error"
                    try:
                        error_detail = e.response.json().get("detail", str(e))
                    except:
                        error_detail = str(e)
                    st.error(f"❌ Error uploading readings: {error_detail}")

# ============ CREDITS TAB ============
with tab3:
    st.header("Carbon Credits")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🔄 Refresh Credits"):
            st.rerun()
    
    # Filter by status
    with col3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "VERIFIED", "PENDING", "FLAGGED", "SUBMITTED"],
            key="credit_status_filter"
        )
    
    # Get credits
    endpoint = "/reports/credits" if status_filter == "All" else f"/reports/credits?status={status_filter}"
    credits = make_request("GET", endpoint)
    
    if credits:
        df = pd.DataFrame([
            {
                "ID": credit.get("id"),
                "Date": credit.get("credit_date", "")[:10],
                "Inverter ID": credit.get("inverter_id"),
                "Tonnes CO2": f"{credit.get('tonnes', 0):.2f}",
                "Status": credit.get("status", ""),
                "Correlation": f"{credit.get('correlation', 0) * 100:.1f}%" if credit.get('correlation') else "N/A",
                "Flagged Reason": credit.get("flagged_reason", "-")
            }
            for credit in credits
        ])
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info(f"No {status_filter.lower() if status_filter != 'All' else ''} credits found")
    
    st.divider()
    
    # Record new credit
    st.subheader("📝 Record New Carbon Credit")
    with st.form("create_credit_form", border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            inverter_id = st.number_input("Inverter ID", value=1, step=1, min_value=1)
        with col2:
            tonnes = st.number_input("CO2 Tonnes", value=1.5, step=0.1, min_value=0.0)
        with col3:
            credit_date = st.date_input("Date", value=datetime.now().date())
        
        status = st.selectbox("Status", ["PENDING", "VERIFIED", "FLAGGED", "SUBMITTED"])
        correlation = st.slider("Correlation (0-1)", 0.0, 1.0, 0.85, step=0.01)
        flagged_reason = st.text_input("Flagged Reason (if applicable)", placeholder="Leave blank if not flagged")
        
        submitted = st.form_submit_button("✅ Record Credit", width="stretch")
        if submitted:
            payload = {
                "credit_date": str(credit_date),
                "inverter_id": inverter_id,
                "tonnes": tonnes,
                "status": status,
                "correlation": correlation
            }
            if flagged_reason:
                payload["flagged_reason"] = flagged_reason
            
            result = make_request("POST", "/credits/", payload)
            if result:
                st.success(f"✅ Credit recorded! ID: {result.get('id')}")
                st.rerun()

# ============ HEALTH TAB ============
with tab4:
    st.header("API Health & Diagnostics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏥 API Information")
        health = make_request("GET", "/health")
        if health:
            st.json(health)
        
        st.subheader("🔗 Connection Test")
        if st.button("Test Connection"):
            try:
                response = requests.get(f"{st.session_state.api_url}/health", timeout=5)
                if response.status_code == 200:
                    st.success(f"✅ Connected! (Status: {response.status_code})")
                else:
                    st.error(f"❌ Unexpected status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")
    
    with col2:
        st.subheader("📈 API Endpoints")
        endpoints = [
            ("GET", "/health", "API health check"),
            ("GET", "/inverters", "List all inverters"),
            ("POST", "/inverters/", "Create inverter"),
            ("GET", "/reports/fleet/summary", "Fleet summary"),
            ("GET", "/reports/credits", "List credits"),
            ("POST", "/credits/", "Record credit"),
        ]
        
        df_endpoints = pd.DataFrame(endpoints, columns=["Method", "Endpoint", "Description"])
        st.dataframe(df_endpoints, width='stretch', hide_index=True)

# Footer
st.divider()
st.markdown("---")
st.markdown(
    f"**Lumix dMRV Engine** | API: {st.session_state.api_url} | "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

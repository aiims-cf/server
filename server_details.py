import streamlit as st
import pandas as pd
import time
from utils.ansible_manager import AnsibleManager
from utils.data_processor import DataProcessor
from utils.visualization import create_server_details_chart, create_resource_timeline
from utils.mariadb_manager import MariaDBManager
 
# Page configuration
st.set_page_config(
   page_title="Server Details | Server Management Dashboard",
   page_icon="🖥️",
   layout="wide"
)
 
# Initialize session state if needed
if 'ansible_manager' not in st.session_state:
   st.session_state.ansible_manager = AnsibleManager()
if 'data_processor' not in st.session_state:
   st.session_state.data_processor = DataProcessor()
if 'db_manager' not in st.session_state:
   try:
       st.session_state.db_manager = MariaDBManager()
   except Exception as e:
       st.error(f"Failed to connect to MariaDB: {str(e)}")
if 'selected_server' not in st.session_state:
   st.session_state.selected_server = None
if 'history_days' not in st.session_state:
   st.session_state.history_days = 1
 
# Function to get server from URL query parameters
def get_server_from_query_params():
   query_params = st.experimental_get_query_params()
   if 'server' in query_params:
       return query_params['server'][0]
   return None
 
# Check URL for server parameter
server_param = get_server_from_query_params()
if server_param and not st.session_state.selected_server:
   st.session_state.selected_server = server_param
 
# Header
st.title("Server Details")
 
# Server selection
servers_data = st.session_state.data_processor.cached_data
server_options = ["Select a server..."] + sorted([s['hostname'] for s in servers_data])
 
# Only show dropdown if we have server data
if len(server_options) > 1:
   selected_server_index = 0
   if st.session_state.selected_server in server_options:
       selected_server_index = server_options.index(st.session_state.selected_server)
  
   selected_server = st.selectbox(
       "Select a server to view details",
       options=server_options,
       index=selected_server_index
   )
  
   if selected_server != "Select a server...":
       st.session_state.selected_server = selected_server
else:
   st.warning("No server data available. Please go to the main dashboard to collect server data.")
   st.stop()
 
# If no server is selected, stop here
if not st.session_state.selected_server or st.session_state.selected_server == "Select a server...":
   st.info("Please select a server from the dropdown to view details.")
   st.stop()
 
# Get server details from cached data
server_data = st.session_state.data_processor.get_server_by_hostname(st.session_state.selected_server)
 
if not server_data:
   st.error(f"Server {st.session_state.selected_server} not found in cached data. Please go back to the main dashboard.")
   st.stop()
 
# History selection
history_days_options = {
   "Last 24 Hours": 1,
   "Last 7 Days": 7,
   "Last 30 Days": 30
}
 
col1, col2 = st.columns([3, 1])
with col2:
   selected_history = st.selectbox(
       "Historical Data Range",
       options=list(history_days_options.keys()),
       index=0
   )
   st.session_state.history_days = history_days_options[selected_history]
  
   if st.button("Refresh Data"):
       st.rerun()
 
# Main content - Server Info
st.subheader("Server Information")
 
# Create columns for basic server info
info_col1, info_col2, info_col3, info_col4 = st.columns(4)
 
with info_col1:
   st.metric("Hostname", server_data['hostname'])
   st.metric("OS", f"{server_data['os_name']} {server_data['os_version']}")
 
with info_col2:
   st.metric("IP Address", server_data['ip_address'])
   st.metric("Server Type", server_data['server_type'])
 
with info_col3:
   st.metric("Server Group", server_data['group'])
   st.metric("CPU Count", server_data['cpu_count'])
 
with info_col4:
   status_color = {
       'Up': 'green',
       'Down': 'red',
       'Warning': 'orange',
       'Critical': 'darkred'
   }.get(server_data['status'], 'gray')
  
   st.markdown(f"<h3 style='color: {status_color};'>Status: {server_data['status']}</h3>", unsafe_allow_html=True)
   st.metric("Uptime", server_data['uptime'])
 
# Create gauges for resource utilization
st.subheader("Current Resource Utilization")
 
charts = create_server_details_chart(server_data)
gauge_col1, gauge_col2, gauge_col3 = st.columns(3)
 
with gauge_col1:
   if 'cpu_gauge' in charts:
       st.plotly_chart(charts['cpu_gauge'], use_container_width=True)
   else:
       st.warning("CPU utilization data not available")
 
with gauge_col2:
   if 'ram_gauge' in charts:
       st.plotly_chart(charts['ram_gauge'], use_container_width=True)
   else:
       st.warning("RAM utilization data not available")
 
with gauge_col3:
   if 'disk_gauge' in charts:
       st.plotly_chart(charts['disk_gauge'], use_container_width=True)
   else:
       st.warning("Disk utilization data not available")
 
# Get historical data from database
try:
   with st.spinner(f"Retrieving {st.session_state.history_days} day(s) of historical data..."):
       history_data = st.session_state.db_manager.get_server_history(
           hostname=st.session_state.selected_server,
           days=st.session_state.history_days
       )
      
   if history_data:
       st.subheader("Historical Resource Utilization")
      
       # Create tabs for historical data
       history_tab1, history_tab2, history_tab3 = st.tabs(["CPU History", "RAM History", "Disk History"])
      
       with history_tab1:
           cpu_timeline = create_resource_timeline(history_data, 'cpu_utilization', 'CPU')
           st.plotly_chart(cpu_timeline, use_container_width=True)
      
       with history_tab2:
           ram_timeline = create_resource_timeline(history_data, 'ram_utilization', 'RAM')
           st.plotly_chart(ram_timeline, use_container_width=True)
      
       with history_tab3:
           disk_timeline = create_resource_timeline(history_data, 'disk_utilization', 'Disk')
           st.plotly_chart(disk_timeline, use_container_width=True)
      
       # Show raw history data in expandable section
       with st.expander("View Raw History Data"):
           history_df = pd.DataFrame(history_data)
           if 'collected_at' in history_df.columns:
               history_df['collected_at'] = history_df['collected_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
           st.dataframe(history_df)
   else:
       st.info(f"No historical data available for the past {st.session_state.history_days} day(s). Data will accumulate over time.")
      
except Exception as e:
   st.error(f"Error retrieving historical data: {str(e)}")
 
# Display all server details in expandable section
with st.expander("All Server Details"):
   # Convert to DataFrame for better display
   details_df = pd.DataFrame([server_data])
   st.dataframe(details_df)
 
# Bottom navigation
st.markdown("---")
st.markdown("← [Return to Dashboard](./)")

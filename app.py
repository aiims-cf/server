

import streamlit as st
import pandas as pd
import time
import os
from utils.ansible_manager import AnsibleManager
from utils.data_processor import DataProcessor
from utils.visualization import create_status_chart, create_resource_chart
from utils.mariadb_manager import MariaDBManager
from dotenv import load_dotenv

load_dotenv()
 
# Page configuration
st.set_page_config(
   page_title="Server Management Dashboard",
   page_icon="🖥️",
   layout="wide",
   initial_sidebar_state="expanded"
)
 
# Initialize session state variables if they don't exist
if 'refresh_interval' not in st.session_state:
   st.session_state.refresh_interval = 60  # Default refresh interval in seconds
if 'last_refresh' not in st.session_state:
   st.session_state.last_refresh = time.time()
if 'ansible_manager' not in st.session_state:
   st.session_state.ansible_manager = AnsibleManager()
if 'data_processor' not in st.session_state:
   st.session_state.data_processor = DataProcessor()
if 'db_manager' not in st.session_state:
   try:
       st.session_state.db_manager = MariaDBManager()
   except Exception as e:
       st.error(f"Failed to connect to MariaDB: {str(e)}")
if 'filter_status' not in st.session_state:
   st.session_state.filter_status = "All"
if 'filter_group' not in st.session_state:
   st.session_state.filter_group = "All"
if 'filter_type' not in st.session_state:
   st.session_state.filter_type = "All"
if 'search_query' not in st.session_state:
   st.session_state.search_query = ""
if 'last_cleanup_date' not in st.session_state:
   st.session_state.last_cleanup_date = time.strftime("%Y-%m-%d")
 
# Sidebar
with st.sidebar:
   st.title("Server Dashboard")
  
   # Refresh settings
   st.header("Refresh Settings")
   st.session_state.refresh_interval = st.slider(
       "Refresh Interval (seconds)",
       min_value=10,
       max_value=300,
       value=st.session_state.refresh_interval,
       step=10
   )
  
   if st.button("Refresh Now"):
       st.session_state.last_refresh = time.time()
       st.rerun()
  
   # Auto refresh logic
   if time.time() - st.session_state.last_refresh > st.session_state.refresh_interval:
       st.session_state.last_refresh = time.time()
       st.rerun()
  
   # Filters
   st.header("Filters")
  
   # Get available groups from the data processor
   available_groups = ["All"] + st.session_state.data_processor.get_server_groups()
   st.session_state.filter_group = st.selectbox(
       "Server Group",
       options=available_groups,
       index=available_groups.index(st.session_state.filter_group)
   )
  
   # Status filter
   status_options = ["All", "Up", "Down", "Warning", "Critical"]
   st.session_state.filter_status = st.selectbox(
       "Status",
       options=status_options,
       index=status_options.index(st.session_state.filter_status)
   )
  
   # Type filter
   type_options = ["All", "Physical", "Virtual"]
   st.session_state.filter_type = st.selectbox(
       "Server Type",
       options=type_options,
       index=type_options.index(st.session_state.filter_type)
   )
  
   # Search filter
   st.session_state.search_query = st.text_input(
       "Search Servers",
       value=st.session_state.search_query
   )
  
   # Display last refresh time
   st.caption(f"Last refreshed: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_refresh))}")
 
# Main content
st.title("Server Management Dashboard")
 
# Fetch and process data
try:
   with st.spinner("Collecting server data..."):
       # Get data from Ansible
       servers_data = st.session_state.ansible_manager.collect_server_data()
      
       # Process the data
       processed_data = st.session_state.data_processor.process_data(servers_data)
      
       # Apply filters
       filtered_data = st.session_state.data_processor.filter_data(
           processed_data,
           status=st.session_state.filter_status,
           group=st.session_state.filter_group,
           server_type=st.session_state.filter_type,
           search_query=st.session_state.search_query
       )
      
       # Schedule cleanup of old metrics (once per day)
       current_date = time.strftime("%Y-%m-%d")
       if 'last_cleanup_date' not in st.session_state or st.session_state.last_cleanup_date != current_date:
           try:
               st.session_state.db_manager.clean_old_metrics(days_to_keep=30)
               st.session_state.last_cleanup_date = current_date
           except Exception as e:
               st.warning(f"Database maintenance skipped: {str(e)}")
      
   # Display summary metrics
   col1, col2, col3, col4 = st.columns(4)
  
   total_servers = len(processed_data)
   up_servers = len([s for s in processed_data if s['status'] == 'Up'])
   warning_servers = len([s for s in processed_data if s['status'] == 'Warning'])
   critical_servers = len([s for s in processed_data if s['status'] == 'Critical'])
  
   col1.metric("Total Servers", total_servers)
   col2.metric("Up", up_servers, f"{up_servers/total_servers:.1%}" if total_servers > 0 else "0%")
   col3.metric("Warning", warning_servers)
   col4.metric("Critical", critical_servers, delta_color="inverse")
  
   # Status overview chart
   st.subheader("Server Status Overview")
   status_chart = create_status_chart(processed_data)
   st.plotly_chart(status_chart, use_container_width=True)
  
   # Resource utilization overview
   st.subheader("Resource Utilization Overview")
  
   # Create tabs for different resource metrics
   cpu_tab, ram_tab, disk_tab = st.tabs(["CPU Utilization", "RAM Utilization", "Disk Utilization"])
  
   with cpu_tab:
       cpu_chart = create_resource_chart(processed_data, 'cpu_utilization', 'CPU')
       st.plotly_chart(cpu_chart, use_container_width=True)
  
   with ram_tab:
       ram_chart = create_resource_chart(processed_data, 'ram_utilization', 'RAM')
       st.plotly_chart(ram_chart, use_container_width=True)
  
   with disk_tab:
       disk_chart = create_resource_chart(processed_data, 'disk_utilization', 'Disk')
       st.plotly_chart(disk_chart, use_container_width=True)
  
   # Servers table
   st.subheader("Servers List")
   if filtered_data:
       # Convert to DataFrame for display
       df = pd.DataFrame(filtered_data)
      
       # Define columns to display
       display_columns = ['hostname', 'status', 'server_type', 'group', 'ip_address',
                         'cpu_utilization', 'ram_utilization', 'disk_utilization']
      
       # Show the table with conditional formatting
       st.dataframe(
           df[display_columns].sort_values('status', ascending=False),
           column_config={
               "hostname": st.column_config.TextColumn("Hostname"),
               "status": st.column_config.TextColumn("Status"),
               "server_type": st.column_config.TextColumn("Type"),
               "group": st.column_config.TextColumn("Group"),
               "ip_address": st.column_config.TextColumn("IP Address"),
               "cpu_utilization": st.column_config.ProgressColumn(
                   "CPU Usage",
                   format="%d%%",
                   min_value=0,
                   max_value=100,
               ),
               "ram_utilization": st.column_config.ProgressColumn(
                   "RAM Usage",
                   format="%d%%",
                   min_value=0,
                   max_value=100,
               ),
               "disk_utilization": st.column_config.ProgressColumn(
                   "Disk Usage",
                   format="%d%%",
                   min_value=0,
                   max_value=100,
               ),
           },
           use_container_width=True,
           hide_index=True,
       )
      
       # Server details expander
       with st.expander("Click on a server in the table for detailed information"):
           st.write("The table above shows a summary of all servers. Click on any row to see detailed metrics and information about that server.")
   else:
       st.warning("No servers match the current filters. Try adjusting your filter criteria.")
 
except Exception as e:
   st.error(f"Error loading server data: {str(e)}")
   st.exception(e)

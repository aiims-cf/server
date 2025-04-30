import streamlit as st
import pandas as pd
import time
from utils.data_processor import DataProcessor
from utils.visualization import create_server_count_by_type
import plotly.graph_objects as go
 
# Page configuration
st.set_page_config(
   page_title="System Overview | Server Management Dashboard",
   page_icon="🖥️",
   layout="wide"
)
 
# Initialize session state if needed
if 'data_processor' not in st.session_state:
   st.session_state.data_processor = DataProcessor()
 
# Header
st.title("System Overview")
 
# Get cached data
if not st.session_state.data_processor.cached_data:
   st.warning("No server data available. Please go to the main dashboard to collect server data.")
   st.stop()
 
# Calculate summary metrics
summary = st.session_state.data_processor.calculate_summary_metrics()
 
# Summary metrics in cards
st.subheader("System Summary")
col1, col2, col3, col4, col5 = st.columns(5)
 
with col1:
   st.metric("Total Servers", summary['total_servers'])
 
with col2:
   st.metric("Servers Up", summary['up_servers'], f"{summary['up_percentage']:.1f}%")
 
with col3:
   st.metric("Servers Down", summary['down_servers'])
 
with col4:
   st.metric("Warning", summary['warning_servers'])
 
with col5:
   st.metric("Critical", summary['critical_servers'])
 
# System-wide resource utilization
st.subheader("System-wide Resource Utilization")
 
res_col1, res_col2, res_col3 = st.columns(3)
 
with res_col1:
   # CPU utilization
   fig_cpu = go.Figure(go.Indicator(
       mode="gauge+number",
       value=summary['avg_cpu'],
       title={"text": "Avg. CPU Utilization"},
       gauge={
           'axis': {'range': [0, 100]},
           'bar': {'color': "blue"},
           'steps': [
               {'range': [0, 80], 'color': "lightgray"},
               {'range': [80, 90], 'color': "orange"},
               {'range': [90, 100], 'color': "red"}
           ],
           'threshold': {
               'line': {'color': "red", 'width': 4},
               'thickness': 0.75,
               'value': 90
           }
       }
   ))
   st.plotly_chart(fig_cpu, use_container_width=True)
 
with res_col2:
   # RAM utilization
   fig_ram = go.Figure(go.Indicator(
       mode="gauge+number",
       value=summary['avg_ram'],
       title={"text": "Avg. RAM Utilization"},
       gauge={
           'axis': {'range': [0, 100]},
           'bar': {'color': "green"},
           'steps': [
               {'range': [0, 80], 'color': "lightgray"},
               {'range': [80, 90], 'color': "orange"},
               {'range': [90, 100], 'color': "red"}
           ],
           'threshold': {
               'line': {'color': "red", 'width': 4},
               'thickness': 0.75,
               'value': 90
           }
       }
   ))
   st.plotly_chart(fig_ram, use_container_width=True)
 
with res_col3:
   # Disk utilization
   fig_disk = go.Figure(go.Indicator(
       mode="gauge+number",
       value=summary['avg_disk'],
       title={"text": "Avg. Disk Utilization"},
       gauge={
           'axis': {'range': [0, 100]},
           'bar': {'color': "purple"},
           'steps': [
               {'range': [0, 80], 'color': "lightgray"},
               {'range': [80, 90], 'color': "orange"},
               {'range': [90, 100], 'color': "red"}
           ],
           'threshold': {
               'line': {'color': "red", 'width': 4},
               'thickness': 0.75,
               'value': 90
           }
       }
   ))
   st.plotly_chart(fig_disk, use_container_width=True)
 
# Server Type distribution
st.subheader("Server Type Distribution")
server_type_chart = create_server_count_by_type(st.session_state.data_processor.cached_data)
st.plotly_chart(server_type_chart, use_container_width=True)
 
# Servers with resource issues
st.subheader("Servers with Resource Issues")
 
# Get servers with resource issues
resource_issues = st.session_state.data_processor.get_resource_threshold_breaches()
 
tab1, tab2, tab3 = st.tabs(["CPU Issues", "RAM Issues", "Disk Issues"])
 
with tab1:
   if resource_issues['cpu']:
       cpu_df = pd.DataFrame(resource_issues['cpu'])
       cpu_df = cpu_df[['hostname', 'ip_address', 'server_type', 'group', 'cpu_utilization']]
       cpu_df = cpu_df.sort_values('cpu_utilization', ascending=False)
      
       st.dataframe(
           cpu_df,
           column_config={
               "hostname": st.column_config.TextColumn("Hostname"),
               "ip_address": st.column_config.TextColumn("IP Address"),
               "server_type": st.column_config.TextColumn("Type"),
               "group": st.column_config.TextColumn("Group"),
               "cpu_utilization": st.column_config.ProgressColumn(
                   "CPU Usage",
                   format="%d%%",
                   min_value=0,
                   max_value=100,
               ),
           },
           use_container_width=True,
           hide_index=True,
       )
   else:
       st.info("No servers with CPU utilization above threshold.")
 
with tab2:
   if resource_issues['ram']:
       ram_df = pd.DataFrame(resource_issues['ram'])
       ram_df = ram_df[['hostname', 'ip_address', 'server_type', 'group', 'ram_utilization']]
       ram_df = ram_df.sort_values('ram_utilization', ascending=False)
      
       st.dataframe(
           ram_df,
           column_config={
               "hostname": st.column_config.TextColumn("Hostname"),
               "ip_address": st.column_config.TextColumn("IP Address"),
               "server_type": st.column_config.TextColumn("Type"),
               "group": st.column_config.TextColumn("Group"),
               "ram_utilization": st.column_config.ProgressColumn(
                   "RAM Usage",
                   format="%d%%",
                   min_value=0,
                   max_value=100,
               ),
           },
           use_container_width=True,
           hide_index=True,
       )
   else:
       st.info("No servers with RAM utilization above threshold.")
 
with tab3:
   if resource_issues['disk']:
       disk_df = pd.DataFrame(resource_issues['disk'])
       disk_df = disk_df[['hostname', 'ip_address', 'server_type', 'group', 'disk_utilization']]
       disk_df = disk_df.sort_values('disk_utilization', ascending=False)
      
       st.dataframe(
           disk_df,
           column_config={
               "hostname": st.column_config.TextColumn("Hostname"),
               "ip_address": st.column_config.TextColumn("IP Address"),
               "server_type": st.column_config.TextColumn("Type"),
               "group": st.column_config.TextColumn("Group"),
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
   else:
       st.info("No servers with disk utilization above threshold.")
 
# Bottom navigation
st.markdown("---")
st.markdown("← [Return to Dashboard](./)")

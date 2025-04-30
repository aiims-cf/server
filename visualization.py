import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any
 
def create_status_chart(data: List[Dict[str, Any]]) -> go.Figure:
   """
   Create a pie chart showing the distribution of server statuses.
  
   Args:
       data: List of dictionaries containing server data
      
   Returns:
       Plotly figure object
   """
   # Count servers by status
   status_counts = {}
   for server in data:
       status = server.get('status', 'Unknown')
       status_counts[status] = status_counts.get(status, 0) + 1
  
   # Define status colors
   status_colors = {
       'Up': 'green',
       'Down': 'red',
       'Warning': 'orange',
       'Critical': 'darkred',
       'Unknown': 'gray'
   }
  
   # Get labels and values
   labels = list(status_counts.keys())
   values = list(status_counts.values())
   colors = [status_colors.get(status, 'gray') for status in labels]
  
   # Create the pie chart
   fig = go.Figure(data=[go.Pie(
       labels=labels,
       values=values,
       hole=.4,
       marker_colors=colors
   )])
  
   fig.update_layout(
       legend_title="Server Status",
       margin=dict(t=0, b=0, l=0, r=0)
   )
  
   return fig
 
def create_resource_chart(data: List[Dict[str, Any]], resource_field: str, resource_name: str) -> go.Figure:
   """
   Create a histogram showing the distribution of resource utilization.
  
   Args:
       data: List of dictionaries containing server data
       resource_field: Field containing resource utilization data
       resource_name: Display name for the resource
      
   Returns:
       Plotly figure object
   """
   # Extract resource utilization data
   resource_values = []
   for server in data:
       value = server.get(resource_field)
       if value is not None and isinstance(value, (int, float)):
           resource_values.append(value)
  
   # Create the histogram
   fig = go.Figure(data=[go.Histogram(
       x=resource_values,
       nbinsx=20,
       marker_color='rgba(0, 123, 255, 0.5)',
       marker_line=dict(color='rgba(0, 123, 255, 1)', width=1)
   )])
  
   fig.update_layout(
       title=f"{resource_name} Utilization Distribution",
       xaxis_title=f"{resource_name} Utilization (%)",
       yaxis_title="Number of Servers",
       bargap=0.1,
       margin=dict(t=30, b=30, l=30, r=30)
   )
  
   # Add a vertical line at 80% (warning threshold)
   fig.add_vline(x=80, line_width=2, line_dash="dash", line_color="orange")
  
   # Add a vertical line at 90% (critical threshold)
   fig.add_vline(x=90, line_width=2, line_dash="dash", line_color="red")
  
   return fig
 
def create_resource_gauge(value: float, title: str) -> go.Figure:
   """
   Create a gauge chart for a single resource utilization value.
  
   Args:
       value: Resource utilization percentage
       title: Title for the gauge
      
   Returns:
       Plotly figure object
   """
   # Determine color based on value
   if value >= 90:
       color = "red"
   elif value >= 80:
       color = "orange"
   else:
       color = "green"
  
   # Create the gauge chart
   fig = go.Figure(go.Indicator(
       mode="gauge+number",
       value=value,
       title={'text': title},
       domain={'x': [0, 1], 'y': [0, 1]},
       gauge={
           'axis': {'range': [0, 100]},
           'bar': {'color': color},
           'steps': [
               {'range': [0, 80], 'color': 'lightgray'},
               {'range': [80, 90], 'color': 'orange'},
               {'range': [90, 100], 'color': 'red'}
           ],
           'threshold': {
               'line': {'color': "black", 'width': 4},
               'thickness': 0.75,
               'value': value
           }
       }
   ))
  
   fig.update_layout(
       margin=dict(t=30, b=0, l=30, r=30),
       height=150
   )
  
   return fig
 
def create_server_details_chart(server_data: Dict[str, Any]) -> Dict[str, go.Figure]:
   """
   Create detailed charts for a specific server.
  
   Args:
       server_data: Dictionary containing server data
      
   Returns:
       Dictionary of Plotly figure objects
   """
   charts = {}
  
   # CPU utilization gauge
   cpu_util = server_data.get('cpu_utilization', 0)
   if isinstance(cpu_util, (int, float)):
       charts['cpu_gauge'] = create_resource_gauge(cpu_util, "CPU Utilization")
  
   # RAM utilization gauge
   ram_util = server_data.get('ram_utilization', 0)
   if isinstance(ram_util, (int, float)):
       charts['ram_gauge'] = create_resource_gauge(ram_util, "RAM Utilization")
  
   # Disk utilization gauge
   disk_util = server_data.get('disk_utilization', 0)
   if isinstance(disk_util, (int, float)):
       charts['disk_gauge'] = create_resource_gauge(disk_util, "Disk Utilization")
  
   return charts
 
def create_resource_timeline(data_over_time: List[Dict[str, Any]], resource_field: str, resource_name: str) -> go.Figure:
   """
   Create a line chart showing resource utilization over time.
  
   Args:
       data_over_time: List of dictionaries containing server data over time
       resource_field: Field containing resource utilization data
       resource_name: Display name for the resource
      
   Returns:
       Plotly figure object
   """
   # Extract timestamps and resource values
   timestamps = []
   resource_values = []
  
   for point in data_over_time:
       timestamp = point.get('collected_at')
       value = point.get(resource_field)
      
       if timestamp and value is not None and isinstance(value, (int, float)):
           timestamps.append(timestamp)
           resource_values.append(value)
  
   # Create the line chart
   fig = go.Figure()
  
   fig.add_trace(go.Scatter(
       x=timestamps,
       y=resource_values,
       mode='lines+markers',
       name=resource_name,
       line=dict(color='blue', width=2)
   ))
  
   # Add warning and critical threshold lines
   fig.add_hline(y=80, line_width=1, line_dash="dash", line_color="orange", annotation_text="Warning")
   fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="red", annotation_text="Critical")
  
   fig.update_layout(
       title=f"{resource_name} Utilization Over Time",
       xaxis_title="Time",
       yaxis_title=f"{resource_name} Utilization (%)",
       yaxis_range=[0, 100],
       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
       margin=dict(t=40, b=40, l=40, r=40)
   )
  
   return fig
 
def create_server_count_by_type(data: List[Dict[str, Any]]) -> go.Figure:
   """
   Create a bar chart showing server counts by type.
  
   Args:
       data: List of dictionaries containing server data
      
   Returns:
       Plotly figure object
   """
   # Count servers by type
   type_counts = {}
   for server in data:
       server_type = server.get('server_type', 'Unknown')
       type_counts[server_type] = type_counts.get(server_type, 0) + 1
  
   # Create the bar chart
   fig = go.Figure(data=[go.Bar(
       x=list(type_counts.keys()),
       y=list(type_counts.values()),
       marker_color=['rgba(0, 123, 255, 0.7)', 'rgba(255, 123, 0, 0.7)']
   )])
  
   fig.update_layout(
       title="Server Count by Type",
       xaxis_title="Server Type",
       yaxis_title="Count",
       margin=dict(t=30, b=30, l=30, r=30)
   )
  
   return fig

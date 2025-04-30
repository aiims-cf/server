import logging
from typing import List, Dict, Any, Optional
import time
 
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
 
class DataProcessor:
   """
   Class to process and filter server data.
   Handles operations like data filtering, sorting, and formatting.
   """
  
   def __init__(self):
       """Initialize the data processor"""
       self.cached_data = []
       self.server_groups = []
       self.last_processed = time.time()
       logger.info("Data Processor initialized")
  
   def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
       """
       Process the raw server data to ensure consistent format.
      
       Args:
           data: List of dictionaries containing server data
          
       Returns:
           Processed data with consistent format
       """
       processed_data = []
      
       for server in data:
           # Ensure all required fields exist
           processed_server = {
               'hostname': server.get('hostname', 'Unknown'),
               'ip_address': server.get('ip_address', 'Unknown'),
               'server_type': server.get('server_type', 'Unknown'),
               'group': server.get('group', 'Default'),
               'os_family': server.get('os_family', 'Unknown'),
               'os_name': server.get('os_name', 'Unknown'),
               'os_version': server.get('os_version', 'Unknown'),
               'cpu_count': server.get('cpu_count', 0),
               'cpu_utilization': server.get('cpu_utilization', 0),
               'ram_total': server.get('ram_total', 0),
               'ram_utilization': server.get('ram_utilization', 0),
               'disk_utilization': server.get('disk_utilization', 0),
               'health_status': server.get('health_status', 'unknown'),
               'status': server.get('status', 'Unknown'),
               'uptime': server.get('uptime', 'Unknown')
           }
          
           # Handle empty or null values
           for key, value in processed_server.items():
               if value is None:
                   if key in ['cpu_utilization', 'ram_utilization', 'disk_utilization', 'cpu_count', 'ram_total']:
                       processed_server[key] = 0
                   else:
                       processed_server[key] = 'Unknown'
          
           # Cap utilization percentages at 100%
           for util_key in ['cpu_utilization', 'ram_utilization', 'disk_utilization']:
               try:
                   util_value = float(processed_server[util_key])
                   processed_server[util_key] = min(max(0, util_value), 100)
               except (ValueError, TypeError):
                   processed_server[util_key] = 0
          
           processed_data.append(processed_server)
      
       # Update cached data and server groups
       self.cached_data = processed_data
       self.server_groups = sorted(list(set(server['group'] for server in processed_data)))
       self.last_processed = time.time()
      
       logger.info(f"Processed {len(processed_data)} server records")
       return processed_data
  
   def filter_data(self,
                   data: List[Dict[str, Any]],
                   status: str = "All",
                   group: str = "All",
                   server_type: str = "All",
                   search_query: str = "") -> List[Dict[str, Any]]:
       """
       Filter server data based on provided criteria.
      
       Args:
           data: List of dictionaries containing server data
           status: Filter by status (All, Up, Down, Warning, Critical)
           group: Filter by server group
           server_type: Filter by server type (All, Physical, Virtual)
           search_query: Search query to filter by hostname or IP
          
       Returns:
           Filtered data matching the criteria
       """
       filtered_data = data.copy()
      
       # Filter by status
       if status != "All":
           filtered_data = [server for server in filtered_data if server['status'] == status]
      
       # Filter by group
       if group != "All":
           filtered_data = [server for server in filtered_data if server['group'] == group]
      
       # Filter by server type
       if server_type != "All":
           filtered_data = [server for server in filtered_data if server['server_type'] == server_type]
      
       # Filter by search query
       if search_query:
           search_query = search_query.lower()
           filtered_data = [
               server for server in filtered_data
               if search_query in server['hostname'].lower() or
                  search_query in server.get('ip_address', '').lower()
           ]
      
       logger.info(f"Filtered data: {len(filtered_data)} servers match criteria (status={status}, group={group}, type={server_type}, search='{search_query}')")
       return filtered_data
  
   def get_server_groups(self) -> List[str]:
       """
       Get the list of unique server groups from cached data.
      
       Returns:
           List of unique server groups
       """
       return self.server_groups
  
   def get_server_by_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
       """
       Get details for a specific server by hostname.
      
       Args:
           hostname: Hostname of the server to find
          
       Returns:
           Server details or None if not found
       """
       for server in self.cached_data:
           if server['hostname'] == hostname:
               return server
       return None
  
   def get_critical_servers(self) -> List[Dict[str, Any]]:
       """
       Get a list of servers with critical status.
      
       Returns:
           List of servers with critical status
       """
       return [server for server in self.cached_data if server['status'] == 'Critical']
  
   def get_warning_servers(self) -> List[Dict[str, Any]]:
       """
       Get a list of servers with warning status.
      
       Returns:
           List of servers with warning status
       """
       return [server for server in self.cached_data if server['status'] == 'Warning']
  
   def calculate_summary_metrics(self) -> Dict[str, Any]:
       """
       Calculate summary metrics for all servers.
      
       Returns:
           Dictionary with summary metrics
       """
       total_servers = len(self.cached_data)
       if total_servers == 0:
           return {
               'total_servers': 0,
               'up_servers': 0,
               'down_servers': 0,
               'warning_servers': 0,
               'critical_servers': 0,
               'up_percentage': 0,
               'avg_cpu': 0,
               'avg_ram': 0,
               'avg_disk': 0
           }
      
       up_servers = len([s for s in self.cached_data if s['status'] == 'Up'])
       down_servers = len([s for s in self.cached_data if s['status'] == 'Down'])
       warning_servers = len([s for s in self.cached_data if s['status'] == 'Warning'])
       critical_servers = len([s for s in self.cached_data if s['status'] == 'Critical'])
      
       # Calculate averages
       cpu_values = [s['cpu_utilization'] for s in self.cached_data if isinstance(s['cpu_utilization'], (int, float))]
       ram_values = [s['ram_utilization'] for s in self.cached_data if isinstance(s['ram_utilization'], (int, float))]
       disk_values = [s['disk_utilization'] for s in self.cached_data if isinstance(s['disk_utilization'], (int, float))]
      
       avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
       avg_ram = sum(ram_values) / len(ram_values) if ram_values else 0
       avg_disk = sum(disk_values) / len(disk_values) if disk_values else 0
      
       return {
           'total_servers': total_servers,
           'up_servers': up_servers,
           'down_servers': down_servers,
           'warning_servers': warning_servers,
           'critical_servers': critical_servers,
           'up_percentage': (up_servers / total_servers) * 100 if total_servers > 0 else 0,
           'avg_cpu': avg_cpu,
           'avg_ram': avg_ram,
           'avg_disk': avg_disk
       }
  
   def get_resource_threshold_breaches(self,
                                     cpu_threshold: float = 80.0,
                                     ram_threshold: float = 80.0,
                                     disk_threshold: float = 80.0) -> Dict[str, List[Dict[str, Any]]]:
       """
       Get servers that exceed resource utilization thresholds.
      
       Args:
           cpu_threshold: CPU utilization threshold percentage
           ram_threshold: RAM utilization threshold percentage
           disk_threshold: Disk utilization threshold percentage
          
       Returns:
           Dictionary with lists of servers exceeding each threshold
       """
       cpu_breaches = [
           server for server in self.cached_data
           if isinstance(server['cpu_utilization'], (int, float)) and server['cpu_utilization'] > cpu_threshold
       ]
      
       ram_breaches = [
           server for server in self.cached_data
           if isinstance(server['ram_utilization'], (int, float)) and server['ram_utilization'] > ram_threshold
       ]
      
       disk_breaches = [
           server for server in self.cached_data
           if isinstance(server['disk_utilization'], (int, float)) and server['disk_utilization'] > disk_threshold
       ]
      
       return {
           'cpu': cpu_breaches,
           'ram': ram_breaches,
           'disk': disk_breaches
       }

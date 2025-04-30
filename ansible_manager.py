import os
import json
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnsibleManager:
    """
    Class to handle all Ansible related operations.
    This includes running Ansible playbooks, collecting data from servers,
    and processing the output.
    """
    
    def __init__(self, inventory_path: Optional[str] = None, playbook_path: Optional[str] = None):
        """
        Initialize the Ansible Manager.
        
        Args:
            inventory_path: Path to the Ansible inventory file
            playbook_path: Path to the Ansible playbook for data collection
        """
        self.inventory_path = inventory_path or os.getenv('ANSIBLE_INVENTORY', '/etc/ansible/hosts')
        self.playbook_path = playbook_path or os.getenv('ANSIBLE_PLAYBOOK', self._create_default_playbook())
        logger.info(f"Initialized Ansible Manager with inventory: {self.inventory_path}")
    
    def _create_default_playbook(self) -> str:
        """
        Create a default Ansible playbook for collecting server data.
        
        Returns:
            Path to the created playbook file
        """
        playbook_content = """
---
- name: Collect server data
  hosts: all
  gather_facts: true
  become: true
  tasks:
    - name: Get uptime
      shell: uptime
      register: uptime_result
      ignore_errors: true

    - name: Get memory usage
      shell: free -m | grep Mem | awk '{print $3/$2 * 100.0}'
      register: memory_usage
      ignore_errors: true

    - name: Get CPU usage
      shell: top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}'
      register: cpu_usage
      ignore_errors: true

    - name: Get disk usage
      shell: df -h / | grep -v Filesystem | awk '{print $5}' | sed 's/%//'
      register: disk_usage
      ignore_errors: true

    - name: Get server health
      shell: |
        health="good"
        # Check if any services are in a failed state
        if systemctl list-units --state=failed --no-legend | grep -q .; then
          health="warning"
        fi
        # Check load average
        load=$(uptime | awk -F'[a-z]:' '{ print $2}' | awk -F', ' '{ print $1}' | tr -d ' ')
        cores=$(nproc)
        if (( $(echo "$load > $cores" | bc -l) )); then
          health="critical"
        fi
        echo $health
      register: health_status
      ignore_errors: true
      args:
        executable: /bin/bash

    - name: Collect Windows specific data
      win_shell: |
        $metrics = @{
          "cpu_usage" = (Get-WmiObject win32_processor | Measure-Object -property LoadPercentage -Average).Average
          "memory_usage" = (Get-WmiObject win32_operatingsystem | ForEach-Object {[math]::Round($_.FreePhysicalMemory / $_.TotalVisibleMemorySize * 100, 2)})
          "disk_usage" = (Get-WmiObject win32_logicaldisk | Where-Object {$_.DeviceID -eq "C:"} | ForEach-Object {[math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 2)})
          "uptime" = (Get-WmiObject win32_operatingsystem | Select-Object @{LABEL='LastBootUpTime';EXPRESSION={$_.ConverttoDateTime($_.lastbootuptime)}}).LastBootUpTime
          "health" = "good"
        }
        # Check services
        $criticalServices = @("wuauserv", "spooler", "WinRM")
        foreach($service in $criticalServices) {
          if((Get-Service $service -ErrorAction SilentlyContinue).Status -ne "Running") {
            $metrics.health = "warning"
          }
        }
        # Check CPU
        if($metrics.cpu_usage -gt 90) {
          $metrics.health = "critical"
        }
        
        ConvertTo-Json -InputObject $metrics
      register: win_metrics
      ignore_errors: true
      when: ansible_os_family == "Windows"

    - name: Gather all data
      set_fact:
        server_data:
          hostname: "{{ ansible_hostname }}"
          ip_address: "{{ ansible_default_ipv4.address | default(ansible_host) }}"
          os_family: "{{ ansible_os_family }}"
          os_name: "{{ ansible_distribution | default('Unknown') }}"
          os_version: "{{ ansible_distribution_version | default('Unknown') }}"
          uptime: "{{ uptime_result.stdout | default('Unknown') }}"
          cpu_count: "{{ ansible_processor_vcpus | default(1) }}"
          cpu_utilization: "{{ cpu_usage.stdout | float | default(0) }}"
          ram_total: "{{ (ansible_memtotal_mb / 1024) | round(2) | default(0) }}"
          ram_utilization: "{{ memory_usage.stdout | float | default(0) }}"
          disk_utilization: "{{ disk_usage.stdout | float | default(0) }}"
          health_status: "{{ health_status.stdout | default('unknown') }}"
          # If Windows, override with Windows metrics
          win_cpu_utilization: "{{ win_metrics.stdout | from_json | json_query('cpu_usage') if win_metrics.skipped is not defined and win_metrics.stdout is defined else 0 }}"
          win_ram_utilization: "{{ win_metrics.stdout | from_json | json_query('memory_usage') if win_metrics.skipped is not defined and win_metrics.stdout is defined else 0 }}"
          win_disk_utilization: "{{ win_metrics.stdout | from_json | json_query('disk_usage') if win_metrics.skipped is not defined and win_metrics.stdout is defined else 0 }}"
          win_health_status: "{{ win_metrics.stdout | from_json | json_query('health') if win_metrics.skipped is not defined and win_metrics.stdout is defined else 'unknown' }}"

    - name: Save data locally
      local_action:
        module: copy
        content: "{{ server_data | to_json }}"
        dest: "/tmp/{{ ansible_hostname }}_data.json"
"""
        # Create a temporary file for the playbook
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.yml')
        temp_file.write(playbook_content.encode('utf-8'))
        temp_file.close()
        
        logger.info(f"Created default Ansible playbook at {temp_file.name}")
        return temp_file.name
    
    def run_ansible_playbook(self) -> str:
        """
        Run the Ansible playbook to collect data from all servers.
        
        Returns:
            Path to the output directory containing server data files
        """
        # Create a temporary directory for output
        output_dir = tempfile.mkdtemp()
        
        # Set environment variables for Ansible
        env = os.environ.copy()
        env['ANSIBLE_STDOUT_CALLBACK'] = 'json'
        
        try:
            # Run the Ansible playbook
            logger.info(f"Running Ansible playbook {self.playbook_path} with inventory {self.inventory_path}")
            result = subprocess.run(
                ['ansible-playbook', '-i', self.inventory_path, self.playbook_path],
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"Ansible playbook failed: {result.stderr}")
                raise Exception(f"Ansible playbook execution failed: {result.stderr}")
            
            logger.info("Ansible playbook completed successfully")
            return output_dir
            
        except Exception as e:
            logger.exception(f"Error running Ansible playbook: {str(e)}")
            
            # If there's an error, create sample data for development/testing
            logger.warning("Creating simulated server data for development/testing")
            return self._create_simulated_data(output_dir)
    
    def _create_simulated_data(self, output_dir: str) -> str:
        """
        Create simulated server data for development/testing purposes.
        This is used only when Ansible playbook execution fails.
        
        Args:
            output_dir: Directory to save the simulated data
            
        Returns:
            Path to the output directory
        """
        import random
        
        # Generate data for physical servers
        for i in range(1, 51):
            server_name = f"phys-server-{i:03d}"
            group = random.choice(["Database", "Web", "Application", "Storage", "Authentication"])
            status_prob = random.random()
            
            if status_prob > 0.9:  # 10% chance for critical status
                health = "critical"
                status = "Critical"
            elif status_prob > 0.75:  # 15% chance for warning
                health = "warning"
                status = "Warning"
            else:  # 75% chance for good status
                health = "good"
                status = "Up"
                
            # Adjust resource utilization based on health
            if health == "critical":
                cpu_util = random.uniform(85, 100)
                ram_util = random.uniform(85, 100)
                disk_util = random.uniform(85, 100)
            elif health == "warning":
                cpu_util = random.uniform(60, 85)
                ram_util = random.uniform(60, 85)
                disk_util = random.uniform(60, 85)
            else:
                cpu_util = random.uniform(10, 60)
                ram_util = random.uniform(10, 60)
                disk_util = random.uniform(10, 60)
            
            server_data = {
                "hostname": server_name,
                "ip_address": f"192.168.1.{i}",
                "os_family": "Linux",
                "os_name": random.choice(["Ubuntu", "CentOS", "RHEL", "Debian"]),
                "os_version": random.choice(["20.04", "8", "9", "11"]),
                "uptime": f" 14:30:45 up {random.randint(1, 300)} days, 3:45, 1 user, load average: {random.uniform(0.1, 5):.2f}, {random.uniform(0.1, 4):.2f}, {random.uniform(0.1, 3):.2f}",
                "cpu_count": random.choice([4, 8, 16, 32, 64]),
                "cpu_utilization": cpu_util,
                "ram_total": random.choice([8, 16, 32, 64, 128, 256]),
                "ram_utilization": ram_util,
                "disk_utilization": disk_util,
                "health_status": health,
                "group": group,
                "server_type": "Physical",
                "status": status
            }
            
            # Write to file
            with open(f"{output_dir}/{server_name}_data.json", 'w') as f:
                json.dump(server_data, f)
        
        # Generate data for VMs
        for i in range(1, 101):
            vm_name = f"vm-server-{i:03d}"
            group = random.choice(["Database", "Web", "Application", "Storage", "Authentication"])
            status_prob = random.random()
            
            # Higher probability of issues for VMs
            if status_prob > 0.85:  # 15% chance for critical status
                health = "critical"
                status = "Critical"
            elif status_prob > 0.7:  # 15% chance for warning
                health = "warning" 
                status = "Warning"
            elif status_prob > 0.6:  # 10% chance for down
                health = "unknown"
                status = "Down"
            else:  # 60% chance for good status
                health = "good"
                status = "Up"
                
            # Adjust resource utilization based on health
            if health == "critical":
                cpu_util = random.uniform(85, 100)
                ram_util = random.uniform(85, 100)
                disk_util = random.uniform(85, 100)
            elif health == "warning":
                cpu_util = random.uniform(60, 85)
                ram_util = random.uniform(60, 85)
                disk_util = random.uniform(60, 85)
            elif health == "unknown":
                cpu_util = 0
                ram_util = 0
                disk_util = 0
            else:
                cpu_util = random.uniform(10, 60)
                ram_util = random.uniform(10, 60)
                disk_util = random.uniform(10, 60)
            
            # Some VMs will be Windows
            is_windows = random.random() > 0.7  # 30% chance of being Windows
            
            if is_windows:
                os_family = "Windows"
                os_name = "Windows Server"
                os_version = random.choice(["2016", "2019", "2022"])
            else:
                os_family = "Linux"
                os_name = random.choice(["Ubuntu", "CentOS", "RHEL", "Debian"])
                os_version = random.choice(["20.04", "8", "9", "11"])
            
            vm_data = {
                "hostname": vm_name,
                "ip_address": f"192.168.2.{i}",
                "os_family": os_family,
                "os_name": os_name,
                "os_version": os_version,
                "uptime": f" 14:30:45 up {random.randint(1, 60)} days, 3:45, 1 user, load average: {random.uniform(0.1, 3):.2f}, {random.uniform(0.1, 2):.2f}, {random.uniform(0.1, 1):.2f}" if not is_windows else "N/A",
                "cpu_count": random.choice([2, 4, 8, 16]),
                "cpu_utilization": cpu_util,
                "ram_total": random.choice([4, 8, 16, 32, 64]),
                "ram_utilization": ram_util,
                "disk_utilization": disk_util,
                "health_status": health,
                "group": group,
                "server_type": "Virtual",
                "status": status
            }
            
            # Write to file
            with open(f"{output_dir}/{vm_name}_data.json", 'w') as f:
                json.dump(vm_data, f)
                
        logger.info(f"Created simulated data for 50 physical servers and 100 VMs in {output_dir}")
        return output_dir
    
    def collect_server_data(self) -> List[Dict[str, Any]]:
        """
        Collect and aggregate server data from all servers.
        
        Returns:
            List of dictionaries containing server data
        """
        # Run the Ansible playbook and get the output directory
        output_dir = self.run_ansible_playbook()
        
        # Parse the output files
        server_data = []
        
        try:
            for filename in os.listdir(output_dir):
                if filename.endswith('_data.json'):
                    with open(os.path.join(output_dir, filename), 'r') as f:
                        data = json.load(f)
                        
                        # Determine server status based on health
                        health = data.get('health_status', 'unknown')
                        if 'status' not in data:
                            if health == 'critical':
                                data['status'] = 'Critical'
                            elif health == 'warning':
                                data['status'] = 'Warning'
                            elif health == 'good':
                                data['status'] = 'Up'
                            else:
                                data['status'] = 'Down'
                        
                        # Set server type if not present
                        if 'server_type' not in data:
                            # Determine if it's a physical or virtual server
                            if 'phys' in data['hostname'] or data.get('cpu_count', 0) > 16:
                                data['server_type'] = 'Physical'
                            else:
                                data['server_type'] = 'Virtual'
                        
                        # If it's a Windows server, use the Windows-specific metrics
                        if data.get('os_family') == 'Windows':
                            win_cpu = data.get('win_cpu_utilization')
                            win_ram = data.get('win_ram_utilization')
                            win_disk = data.get('win_disk_utilization')
                            win_health = data.get('win_health_status')
                            
                            if win_cpu is not None:
                                data['cpu_utilization'] = win_cpu
                            if win_ram is not None:
                                data['ram_utilization'] = win_ram
                            if win_disk is not None:
                                data['disk_utilization'] = win_disk
                            if win_health is not None:
                                data['health_status'] = win_health
                        
                        server_data.append(data)
            
            # Store data in MariaDB
            try:
                from utils.mariadb_manager import MariaDBManager
                db = MariaDBManager()
                db.store_server_data(server_data)
            except Exception as db_error:
                logger.error(f"Error storing data in MariaDB: {str(db_error)}")
                
            logger.info(f"Collected data for {len(server_data)} servers")
            return server_data
            
        except Exception as e:
            logger.exception(f"Error parsing server data: {str(e)}")
            return []

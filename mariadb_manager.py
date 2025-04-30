import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
 
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
 
class MariaDBManager:
   def __init__(self):
       """Initialize the database connection."""
       # Get database connection info from environment variables or use defaults
       db_user = os.getenv('DB_USER', 'dashboard_user')
       db_password = os.getenv('DB_PASSWORD', 'your_secure_password')
       db_host = os.getenv('DB_HOST', 'localhost')
       db_port = os.getenv('DB_PORT', '3306')
       db_name = os.getenv('DB_NAME', 'server_dashboard')

       # Debug: Log raw DB_HOST value
       logger.debug(f"Raw DB_HOST from environment: {os.getenv('DB_HOST')}")

        # Validate and correct DB_HOST
       if db_host.startswith('123') or '@' in db_host:
           logger.error(f"Invalid DB_HOST detected: {db_host}. Forcing to 'localhost'")
           db_host = 'localhost'

        # Log connection parameters (avoid logging password)
       logger.info(f"Attempting to connect to MariaDB at {db_host}:{db_port}/{db_name} as {db_user}")



       # Create database connection string for MariaDB
       self.db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

       try:
           # Create SQLAlchemy engine
           self.engine = create_engine(self.db_url)
           # Create a session factory
           self.Session = sessionmaker(bind=self.engine)
           logger.info("MariaDB connection established")

           # Create tables if they don't exist
           self._create_tables_if_not_exist()
       except Exception as e:
           logger.error(f"Error connecting to MariaDB: {str(e)}")
           raise

  
   def _create_tables_if_not_exist(self):
       """Create database tables if they don't exist."""
       try:
           with self.engine.connect() as conn:
               # Create servers table
               conn.execute(text("""
                   CREATE TABLE IF NOT EXISTS servers (
                       id INT AUTO_INCREMENT PRIMARY KEY,
                       hostname VARCHAR(255) NOT NULL,
                       ip_address VARCHAR(50),
                       server_type VARCHAR(50),
                       group_name VARCHAR(100),
                       os_family VARCHAR(50),
                       os_name VARCHAR(100),
                       os_version VARCHAR(50),
                       cpu_count INT,
                       ram_total FLOAT,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
               """))
              
               # Create server_metrics table
               conn.execute(text("""
                   CREATE TABLE IF NOT EXISTS server_metrics (
                       id INT AUTO_INCREMENT PRIMARY KEY,
                       server_id INT,
                       status VARCHAR(50),
                       cpu_utilization FLOAT,
                       ram_utilization FLOAT,
                       disk_utilization FLOAT,
                       health_status VARCHAR(50),
                       uptime TEXT,
                       collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY (server_id) REFERENCES servers(id)
                   )
               """))
              
               # Create indexes
               conn.execute(text(
                   "CREATE INDEX IF NOT EXISTS idx_server_metrics_server_id ON server_metrics(server_id)"
               ))
               conn.execute(text(
                   "CREATE INDEX IF NOT EXISTS idx_server_metrics_collected_at ON server_metrics(collected_at)"
               ))
              
               conn.commit()
              
           logger.info("Database tables created or already exist")
       except Exception as e:
           logger.error(f"Error creating database tables: {str(e)}")
           raise
  
   def store_server_data(self, servers_data: List[Dict[str, Any]]) -> None:
       """
       Store server data in the database.
      
       Args:
           servers_data: List of dictionaries containing server data
       """
       try:
           with self.Session() as session:
               for server in servers_data:
                   # Check if server already exists
                   result = session.execute(
                       text("SELECT id FROM servers WHERE hostname = :hostname"),
                       {"hostname": server.get('hostname')}
                   ).fetchone()
                  
                   # If server doesn't exist, insert it
                   if not result:
                       session.execute(
                           text("""
                               INSERT INTO servers (
                                   hostname, ip_address, server_type, group_name,
                                   os_family, os_name, os_version, cpu_count, ram_total
                               ) VALUES (
                                   :hostname, :ip_address, :server_type, :group,
                                   :os_family, :os_name, :os_version, :cpu_count, :ram_total
                               )
                           """),
                           {
                               "hostname": server.get('hostname'),
                               "ip_address": server.get('ip_address'),
                               "server_type": server.get('server_type'),
                               "group": server.get('group'),
                               "os_family": server.get('os_family'),
                               "os_name": server.get('os_name'),
                               "os_version": server.get('os_version'),
                               "cpu_count": server.get('cpu_count'),
                               "ram_total": server.get('ram_total')
                           }
                       )
                       # Get the last inserted ID in MariaDB
                       server_id_result = session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()
                       server_id = server_id_result[0]
                   else:
                       server_id = result[0]
                  
                   # Insert server metrics
                   session.execute(
                       text("""
                           INSERT INTO server_metrics (
                               server_id, status, cpu_utilization, ram_utilization,
                               disk_utilization, health_status, uptime
                           ) VALUES (
                               :server_id, :status, :cpu_utilization, :ram_utilization,
                               :disk_utilization, :health_status, :uptime
                           )
                       """),
                       {
                           "server_id": server_id,
                           "status": server.get('status'),
                           "cpu_utilization": server.get('cpu_utilization'),
                           "ram_utilization": server.get('ram_utilization'),
                           "disk_utilization": server.get('disk_utilization'),
                           "health_status": server.get('health_status'),
                           "uptime": server.get('uptime')
                       }
                   )
              
               # Commit the transaction
               session.commit()
               logger.info(f"Stored data for {len(servers_data)} servers in the database")
       except Exception as e:
           logger.error(f"Error storing server data: {str(e)}")
           raise
  
   def get_latest_server_data(self) -> List[Dict[str, Any]]:
       """
       Get the latest server data from the database.
      
       Returns:
           List of dictionaries containing the latest server data
       """
       try:
           # MariaDB syntax for getting latest metrics for each server
           query = """
               SELECT
                   s.hostname,
                   s.ip_address,
                   s.server_type,
                   s.group_name as `group`,
                   s.os_family,
                   s.os_name,
                   s.os_version,
                   s.cpu_count,
                   s.ram_total,
                   m.status,
                   m.cpu_utilization,
                   m.ram_utilization,
                   m.disk_utilization,
                   m.health_status,
                   m.uptime,
                   m.collected_at
               FROM servers s
               JOIN (
                   SELECT server_id, MAX(collected_at) as max_collected_at
                   FROM server_metrics
                   GROUP BY server_id
               ) latest ON latest.server_id = s.id
               JOIN server_metrics m ON m.server_id = latest.server_id AND m.collected_at = latest.max_collected_at
               ORDER BY s.hostname
           """
          
           with self.engine.connect() as connection:
               result = connection.execute(text(query))
               servers = [dict(row) for row in result]
          
           logger.info(f"Retrieved latest data for {len(servers)} servers from the database")
           return servers
       except Exception as e:
           logger.error(f"Error retrieving latest server data: {str(e)}")
           raise
  
   def get_server_history(self, hostname: str, days: int = 1) -> List[Dict[str, Any]]:
       """
       Get historical data for a specific server.
      
       Args:
           hostname: The hostname of the server
           days: Number of days of history to retrieve
          
       Returns:
           List of dictionaries containing historical server data
       """
       try:
           query = """
               SELECT
                   s.hostname,
                   m.status,
                   m.cpu_utilization,
                   m.ram_utilization,
                   m.disk_utilization,
                   m.health_status,
                   m.collected_at
               FROM servers s
               JOIN server_metrics m ON s.id = m.server_id
               WHERE s.hostname = :hostname
               AND m.collected_at > :start_date
               ORDER BY m.collected_at
           """
          
           start_date = datetime.now() - timedelta(days=days)
          
           with self.engine.connect() as connection:
               result = connection.execute(
                   text(query),
                   {"hostname": hostname, "start_date": start_date}
               )
               history = [dict(row) for row in result]
          
           logger.info(f"Retrieved {len(history)} historical records for server {hostname}")
           return history
       except Exception as e:
           logger.error(f"Error retrieving server history: {str(e)}")
           raise
  
   def clean_old_metrics(self, days_to_keep: int = 30) -> None:
       """
       Clean up old metrics data to prevent database bloat.
      
       Args:
           days_to_keep: Number of days of metrics to keep
       """
       try:
           cutoff_date = datetime.now() - timedelta(days=days_to_keep)
          
           with self.Session() as session:
               result = session.execute(
                   text("DELETE FROM server_metrics WHERE collected_at < :cutoff_date"),
                   {"cutoff_date": cutoff_date}
               )
               session.commit()
              
           logger.info(f"Cleaned up old metrics data older than {days_to_keep} days")
       except Exception as e:
           logger.error(f"Error cleaning old metrics: {str(e)}")
           raise

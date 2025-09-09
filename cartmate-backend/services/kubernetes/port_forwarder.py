import asyncio
import logging
import subprocess
import signal
import os
import sys
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class KubernetesPortForwarder:
    """Manages kubectl port forwarding for external services."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.forwarding_configs = {
            "productcatalogservice": {
                "service": "productcatalogservice",
                "local_port": 3550,
                "remote_port": 3550,
                "required": True
            },
            "cartservice": {
                "service": "cartservice", 
                "local_port": 50052,
                "remote_port": 50052,
                "required": False
            },
            "paymentservice": {
                "service": "paymentservice",
                "local_port": 50051,
                "remote_port": 50051,
                "required": False
            }
        }
    
    async def start_port_forwarding(self) -> bool:
        """Start port forwarding for all configured services."""
        logger.info("Starting Kubernetes port forwarding...")
        
        success_count = 0
        total_required = sum(1 for config in self.forwarding_configs.values() if config["required"])
        
        for service_name, config in self.forwarding_configs.items():
            try:
                if await self._start_single_port_forward(service_name, config):
                    success_count += 1
                    logger.info(f"✅ Port forwarding started for {service_name}: localhost:{config['local_port']} -> {config['service']}:{config['remote_port']}")
                else:
                    if config["required"]:
                        logger.error(f"❌ Failed to start required port forwarding for {service_name}")
                    else:
                        logger.warning(f"⚠️ Failed to start optional port forwarding for {service_name}")
            except Exception as e:
                if config["required"]:
                    logger.error(f"❌ Error starting port forwarding for {service_name}: {e}")
                else:
                    logger.warning(f"⚠️ Error starting optional port forwarding for {service_name}: {e}")
        
        # Check if all required services are available
        if success_count >= total_required:
            logger.info(f"✅ Port forwarding setup complete: {success_count}/{len(self.forwarding_configs)} services available")
            return True
        else:
            logger.error(f"❌ Port forwarding setup incomplete: {success_count}/{total_required} required services available")
            return False
    
    async def _start_single_port_forward(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Start port forwarding for a single service."""
        try:
            # Check if kubectl is available
            if not await self._check_kubectl_available():
                logger.error("kubectl not found or not configured")
                return False
            
            # Check if the service exists in the cluster
            if not await self._check_service_exists(config["service"]):
                logger.warning(f"Service {config['service']} not found in cluster")
                return False
            
            # Start the port forwarding process
            cmd = [
                "kubectl", "port-forward", 
                f"svc/{config['service']}", 
                f"{config['local_port']}:{config['remote_port']}"
            ]
            
            logger.debug(f"Starting port forward: {' '.join(cmd)}")
            
            # Start the process in the background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            
            # Store the process for cleanup
            self.processes[service_name] = process
            
            # Give it a moment to start and check if it's still running
            await asyncio.sleep(2)
            
            if process.poll() is None:
                logger.debug(f"Port forwarding process for {service_name} started successfully (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Port forwarding process for {service_name} failed to start. stdout: {stdout}, stderr: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting port forwarding for {service_name}: {e}")
            return False
    
    async def _check_kubectl_available(self) -> bool:
        """Check if kubectl is available and configured."""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def _check_service_exists(self, service_name: str) -> bool:
        """Check if a service exists in the current cluster."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "svc", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    
    async def stop_port_forwarding(self):
        """Stop all port forwarding processes."""
        logger.info("Stopping Kubernetes port forwarding...")
        
        for service_name, process in self.processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    logger.debug(f"Stopping port forwarding for {service_name} (PID: {process.pid})")
                    
                    if sys.platform == "win32":
                        # On Windows, send CTRL_BREAK_EVENT to the process group
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        # On Unix-like systems, send SIGTERM
                        process.terminate()
                    
                    # Wait for the process to terminate
                    try:
                        process.wait(timeout=5)
                        logger.debug(f"Port forwarding for {service_name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't stop gracefully
                        process.kill()
                        logger.debug(f"Port forwarding for {service_name} force killed")
                        
            except Exception as e:
                logger.error(f"Error stopping port forwarding for {service_name}: {e}")
        
        self.processes.clear()
        logger.info("Port forwarding cleanup completed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of all port forwarding processes."""
        status = {}
        for service_name, process in self.processes.items():
            status[service_name] = {
                "running": process.poll() is None,
                "pid": process.pid if process.poll() is None else None,
                "config": self.forwarding_configs[service_name]
            }
        return status

# Global instance
port_forwarder = KubernetesPortForwarder()

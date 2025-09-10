"""
Agent Manager - Handles startup, shutdown, and lifecycle of all agents
"""
import logging
import asyncio
from typing import List, Dict
from agents.orchestrator import orchestrator_agent
from agents.product_discovery import product_discovery_agent
from agents.price_comparison import price_comparison_agent

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages the lifecycle of all agents in the system"""
    
    def __init__(self):
        self.agents = []
        self.running = False
        
    def register_agents(self):
        """Register all agents that should be started"""
        self.agents = [
            orchestrator_agent,
            product_discovery_agent,
            price_comparison_agent,
            # Add more agents here as they're implemented
        ]
        logger.info(f"Registered {len(self.agents)} agents for startup")
    
    async def start_all_agents(self):
        """Start all registered agents"""
        if self.running:
            logger.warning("Agents are already running")
            return
            
        logger.info("Starting all agents...")
        
        startup_tasks = []
        for agent in self.agents:
            logger.info(f"Starting agent: {agent.agent_id} ({agent.agent_type})")
            task = asyncio.create_task(agent.start())
            startup_tasks.append(task)
        
        # Wait for all agents to start
        try:
            await asyncio.gather(*startup_tasks)
            self.running = True
            logger.info("All agents started successfully")
        except Exception as e:
            logger.error(f"Error starting agents: {e}")
            # Try to stop any that did start
            await self.stop_all_agents()
            raise
    
    async def stop_all_agents(self):
        """Stop all running agents"""
        if not self.running:
            logger.warning("Agents are not running")
            return
            
        logger.info("Stopping all agents...")
        
        shutdown_tasks = []
        for agent in self.agents:
            logger.info(f"Stopping agent: {agent.agent_id}")
            task = asyncio.create_task(agent.stop())
            shutdown_tasks.append(task)
        
        # Wait for all agents to stop
        try:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            self.running = False
            logger.info("All agents stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping agents: {e}")
    
    def get_agent_by_id(self, agent_id: str):
        """Get agent by ID"""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def get_agent_by_type(self, agent_type: str):
        """Get first agent of specified type"""
        for agent in self.agents:
            if agent.agent_type == agent_type:
                return agent
        return None
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        status = {
            "running": self.running,
            "total_agents": len(self.agents),
            "agents": []
        }
        
        for agent in self.agents:
            agent_info = {
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "capabilities": agent.registration.capabilities,
                "is_running": agent.is_running
            }
            status["agents"].append(agent_info)
        
        return status

# Global agent manager instance
agent_manager = AgentManager()


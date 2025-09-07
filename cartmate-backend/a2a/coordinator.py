import logging
from typing import Dict, List, Optional
from models.a2a import A2ARegistration
from services.storage.redis_client import redis_client
import json

logger = logging.getLogger(__name__)

class A2ACoordinator:
    """Coordinates agent registration, discovery, and routing"""
    
    def __init__(self):
        self.agents: Dict[str, A2ARegistration] = {}
        self.agent_types: Dict[str, List[str]] = {}  # agent_type -> list of agent_ids
        
    async def register_agent(self, registration: A2ARegistration) -> bool:
        """Register an agent with the coordinator"""
        try:
            self.agents[registration.agent_id] = registration
            
            # Update agent types index
            if registration.agent_type not in self.agent_types:
                self.agent_types[registration.agent_type] = []
            if registration.agent_id not in self.agent_types[registration.agent_type]:
                self.agent_types[registration.agent_type].append(registration.agent_id)
            
            # Store in Redis for persistence
            key = f"a2a:agent:{registration.agent_id}"
            await redis_client.set(key, registration.model_dump_json())
            
            logger.info(f"Registered agent {registration.agent_id} of type {registration.agent_type}")
            return True
        except Exception as e:
            logger.error(f"Error registering agent {registration.agent_id}: {e}")
            return False
    
    async def deregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the coordinator"""
        try:
            if agent_id in self.agents:
                agent_type = self.agents[agent_id].agent_type
                del self.agents[agent_id]
                
                # Update agent types index
                if agent_type in self.agent_types and agent_id in self.agent_types[agent_type]:
                    self.agent_types[agent_type].remove(agent_id)
                    if not self.agent_types[agent_type]:
                        del self.agent_types[agent_type]
                
                # Remove from Redis
                key = f"a2a:agent:{agent_id}"
                await redis_client.delete(key)
                
                logger.info(f"Deregistered agent {agent_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deregistering agent {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[A2ARegistration]:
        """Get agent registration by ID"""
        return self.agents.get(agent_id)
    
    def find_agent_by_type(self, agent_type: str) -> Optional[A2ARegistration]:
        """Find an available agent of a specific type"""
        if agent_type in self.agent_types and self.agent_types[agent_type]:
            agent_id = self.agent_types[agent_type][0]  # Get first available
            return self.agents.get(agent_id)
        return None
    
    def list_agents(self) -> List[A2ARegistration]:
        """List all registered agents"""
        return list(self.agents.values())
    
    def list_agent_types(self) -> List[str]:
        """List all available agent types"""
        return list(self.agent_types.keys())
    
    async def load_agents_from_storage(self):
        """Load agent registrations from storage on startup"""
        # This would typically scan Redis for stored agents
        # For now, we'll rely on agents registering themselves at startup
        pass

# Global A2A coordinator instance
a2a_coordinator = A2ACoordinator()
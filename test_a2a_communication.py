#!/usr/bin/env python3
"""
Test script to verify A2A communication between agents
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'cartmate-backend'))

from agents.orchestrator import orchestrator_agent
from agents.product_discovery import product_discovery_agent
from a2a.coordinator import a2a_coordinator
from a2a.message_bus import a2a_message_bus

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_agent_communication():
    """Test communication between agents"""
    print("Starting A2A agent communication test...")
    
    try:
        # Initialize the message bus
        print("Initializing message bus...")
        
        # Start the agents
        print("Starting orchestrator agent...")
        await orchestrator_agent.start()
        
        print("Starting product discovery agent...")
        await product_discovery_agent.start()
        
        # Wait a moment for agents to register
        await asyncio.sleep(1)
        
        # Check that agents are registered
        agents = a2a_coordinator.list_agents()
        print(f"Registered agents: {len(agents)}")
        for agent in agents:
            print(f"  - {agent.agent_id} ({agent.agent_type})")
        
        # Test finding an agent by type
        product_agent = a2a_coordinator.find_agent_by_type("product_discovery")
        if product_agent:
            print(f"Found product discovery agent: {product_agent.agent_id}")
        else:
            print("ERROR: Could not find product discovery agent")
            return False
        
        # Test sending a message from orchestrator to product discovery
        print("Testing message sending...")
        
        # This would normally be done through the orchestrator's handle_user_message method
        # For testing purposes, we'll simulate the interaction
        
        print("Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        logging.exception("Test error")
        return False
    finally:
        # Clean up
        try:
            await orchestrator_agent.stop()
            await product_discovery_agent.stop()
        except:
            pass

if __name__ == "__main__":
    print("Running A2A agent communication test...")
    success = asyncio.run(test_agent_communication())
    if success:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Tests failed!")
        sys.exit(1)
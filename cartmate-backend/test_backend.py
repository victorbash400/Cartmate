#!/usr/bin/env python3
"""
Simple test script to verify backend functionality
"""
import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection to backend"""
    uri = "ws://localhost:8000/ws/chat"
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connected successfully")
            
            # Send a test message
            test_message = "Hello, I'm testing the connection"
            await websocket.send(test_message)
            logger.info(f"📤 Sent: {test_message}")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            logger.info(f"📥 Received: {response}")
            
            # Try to parse as JSON
            try:
                response_data = json.loads(response)
                logger.info(f"✅ Response parsed as JSON: {response_data}")
            except:
                logger.info(f"ℹ️  Response is plain text: {response}")
                
            return True
            
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        return False

async def test_health_endpoint():
    """Test the health endpoint"""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Health endpoint OK: {data}")
                    return True
                else:
                    logger.error(f"❌ Health endpoint failed: {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Health endpoint error: {e}")
        return False

async def test_agents_status():
    """Test the agents status endpoint"""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/agents/status') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Agents status OK: {data}")
                    
                    # Check if agents are running
                    if data.get('running') and data.get('total_agents', 0) > 0:
                        logger.info(f"✅ {data['total_agents']} agents are running")
                        for agent in data.get('agents', []):
                            status = "🟢 RUNNING" if agent.get('is_running') else "🔴 STOPPED"
                            logger.info(f"  - {agent.get('agent_id')} ({agent.get('agent_type')}): {status}")
                    else:
                        logger.warning("⚠️  No agents are running")
                    
                    return True
                else:
                    logger.error(f"❌ Agents status failed: {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Agents status error: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🧪 Starting backend tests...")
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Agents Status", test_agents_status),
        ("WebSocket Connection", test_websocket_connection),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Testing {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n📊 Test Results:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Backend is working correctly.")
    else:
        logger.warning("⚠️  Some tests failed. Check the backend setup.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")


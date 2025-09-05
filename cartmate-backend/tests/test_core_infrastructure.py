import pytest
import asyncio
from main import app
from services.storage.redis_client import redis_client
from services.storage.session_manager import session_manager

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def initialize_storage():
    """Initialize storage for testing."""
    await redis_client.initialize()
    yield
    await redis_client.close()

@pytest.mark.asyncio
async def test_storage_connection():
    """Test storage connection."""
    # Test set/get
    await redis_client.set("test_key", "test_value")
    value = await redis_client.get("test_key")
    assert value == "test_value"
    
    # Test delete
    deleted = await redis_client.delete("test_key")
    assert deleted == 1

@pytest.mark.asyncio
async def test_session_manager():
    """Test session manager functionality."""
    # Test create session
    user_id = "test_user"
    session_id = "test_session"
    session = await session_manager.create_session(user_id, session_id)
    
    assert session.id == session_id
    assert session.user_id == user_id
    
    # Test get session
    retrieved_session = await session_manager.get_session(session_id)
    assert retrieved_session is not None
    assert retrieved_session.id == session_id
    assert retrieved_session.user_id == user_id
    
    # Test update context
    context = {"test": "value"}
    result = await session_manager.update_context(session_id, context)
    assert result == True
    
    # Verify context was updated
    updated_session = await session_manager.get_session(session_id)
    assert updated_session.context.get("test") == "value"
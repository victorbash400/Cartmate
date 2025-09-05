import logging
import json
from typing import Optional, Any, Dict
from config.settings import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class InMemoryStorage:
    """In-memory storage implementation for development."""
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
        
    def _cleanup_expired(self):
        """Remove expired keys."""
        now = datetime.utcnow()
        expired_keys = [key for key, expiry in self.expiry.items() if now > expiry]
        for key in expired_keys:
            del self.data[key]
            del self.expiry[key]
    
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        self._cleanup_expired()
        return self.data.get(key)
    
    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        self._cleanup_expired()
        self.data[key] = value
        if expire:
            self.expiry[key] = datetime.utcnow() + timedelta(seconds=expire)
        return True
    
    def delete(self, key: str) -> int:
        """Delete a key."""
        self._cleanup_expired()
        if key in self.data:
            del self.data[key]
            if key in self.expiry:
                del self.expiry[key]
            return 1
        return 0
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        self._cleanup_expired()
        return key in self.data

class RedisClient:
    def __init__(self):
        self.storage = InMemoryStorage()

    async def initialize(self):
        """Initialize the in-memory storage."""
        logger.info("In-memory storage initialized successfully")

    async def close(self):
        """Close the storage (no-op for in-memory)."""
        logger.info("In-memory storage closed")

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        return self.storage.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        return self.storage.set(key, value, expire)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        return self.storage.delete(key)

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message (no-op for in-memory)."""
        logger.debug(f"Publishing to {channel}: {message}")
        return 1

    async def subscribe(self, channel: str):
        """Create a subscription (no-op for in-memory)."""
        logger.debug(f"Subscribing to {channel}")
        return None

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return self.storage.exists(key)


# Global Redis client instance
redis_client = RedisClient()
"""Database connections for MongoDB and Redis."""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as redis
from typing import Optional
from config.settings import settings


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.mongodb_client: Optional[AsyncIOMotorClient] = None
        self.mongodb_database: Optional[AsyncIOMotorDatabase] = None
        self.redis_client: Optional[redis.Redis] = None

    async def connect_to_mongodb(self):
        """Connect to MongoDB."""
        try:
            self.mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
            self.mongodb_database = self.mongodb_client[settings.mongodb_database]
            
            # Test the connection
            await self.mongodb_client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {settings.mongodb_database}")
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def connect_to_redis(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                decode_responses=True
            )
            
            # Test the connection
            await self.redis_client.ping()
            print(f"✅ Connected to Redis: {settings.redis_url}")
            
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            raise

    async def close_mongodb_connection(self):
        """Close MongoDB connection."""
        if self.mongodb_client:
            self.mongodb_client.close()
            print("🔌 MongoDB connection closed")

    async def close_redis_connection(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            print("🔌 Redis connection closed")

    async def get_mongodb_collection(self, collection_name: str):
        """Get a MongoDB collection."""
        if self.mongodb_database is None:
            raise RuntimeError("MongoDB not connected")
        return self.mongodb_database[collection_name]

    async def get_redis_client(self):
        """Get Redis client."""
        if self.redis_client is None:
            raise RuntimeError("Redis not connected")
        return self.redis_client


# Global database instance
database = Database()

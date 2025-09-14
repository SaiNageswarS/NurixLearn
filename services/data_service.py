"""Service layer for business logic."""

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import json

from models.data_models import (
    User, Product, ErrorLog, UserCreate, UserUpdate, 
    ProductCreate, ProductUpdate, ErrorSeverity, ErrorStatus
)
from utils.database import database


class UserService:
    """Service for user operations."""
    
    def __init__(self):
        self.collection_name = "users"

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(**user_data.dict())
        collection = await database.get_mongodb_collection(self.collection_name)
        
        result = await collection.insert_one(user.dict(by_alias=True))
        user.id = result.inserted_id
        
        # Cache in Redis
        await self._cache_user(user)
        
        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        # Try Redis cache first
        cached_user = await self._get_cached_user(user_id)
        if cached_user:
            return cached_user
        
        # Get from MongoDB
        collection = await database.get_mongodb_collection(self.collection_name)
        user_data = await collection.find_one({"_id": ObjectId(user_id)})
        
        if user_data:
            user = User(**user_data)
            # Cache in Redis
            await self._cache_user(user)
            return user
        
        return None

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        collection = await database.get_mongodb_collection(self.collection_name)
        cursor = collection.find().skip(skip).limit(limit)
        users = []
        
        async for user_data in cursor:
            users.append(User(**user_data))
        
        return users

    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update a user."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        # Add updated_at timestamp
        update_data = user_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count:
            # Invalidate cache
            await self._invalidate_user_cache(user_id)
            # Return updated user
            return await self.get_user(user_id)
        
        return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        collection = await database.get_mongodb_collection(self.collection_name)
        result = await collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count:
            # Invalidate cache
            await self._invalidate_user_cache(user_id)
            return True
        
        return False

    async def _cache_user(self, user: User):
        """Cache user in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"user:{user.id}"
        await redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            user.json()
        )

    async def _get_cached_user(self, user_id: str) -> Optional[User]:
        """Get user from Redis cache."""
        redis_client = await database.get_redis_client()
        cache_key = f"user:{user_id}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            return User.parse_raw(cached_data)
        
        return None

    async def _invalidate_user_cache(self, user_id: str):
        """Invalidate user cache in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"user:{user_id}"
        await redis_client.delete(cache_key)


class ProductService:
    """Service for product operations."""
    
    def __init__(self):
        self.collection_name = "products"

    async def create_product(self, product_data: ProductCreate) -> Product:
        """Create a new product."""
        product = Product(**product_data.dict())
        collection = await database.get_mongodb_collection(self.collection_name)
        
        result = await collection.insert_one(product.dict(by_alias=True))
        product.id = result.inserted_id
        
        # Cache in Redis
        await self._cache_product(product)
        
        return product

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID."""
        # Try Redis cache first
        cached_product = await self._get_cached_product(product_id)
        if cached_product:
            return cached_product
        
        # Get from MongoDB
        collection = await database.get_mongodb_collection(self.collection_name)
        product_data = await collection.find_one({"_id": ObjectId(product_id)})
        
        if product_data:
            product = Product(**product_data)
            # Cache in Redis
            await self._cache_product(product)
            return product
        
        return None

    async def get_products(self, skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[Product]:
        """Get products with optional category filter."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        filter_dict = {}
        if category:
            filter_dict["category"] = category
        
        cursor = collection.find(filter_dict).skip(skip).limit(limit)
        products = []
        
        async for product_data in cursor:
            products.append(Product(**product_data))
        
        return products

    async def update_product(self, product_id: str, product_data: ProductUpdate) -> Optional[Product]:
        """Update a product."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        # Add updated_at timestamp
        update_data = product_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        
        if result.modified_count:
            # Invalidate cache
            await self._invalidate_product_cache(product_id)
            # Return updated product
            return await self.get_product(product_id)
        
        return None

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product."""
        collection = await database.get_mongodb_collection(self.collection_name)
        result = await collection.delete_one({"_id": ObjectId(product_id)})
        
        if result.deleted_count:
            # Invalidate cache
            await self._invalidate_product_cache(product_id)
            return True
        
        return False

    async def _cache_product(self, product: Product):
        """Cache product in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"product:{product.id}"
        await redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            product.json()
        )

    async def _get_cached_product(self, product_id: str) -> Optional[Product]:
        """Get product from Redis cache."""
        redis_client = await database.get_redis_client()
        cache_key = f"product:{product_id}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            return Product.parse_raw(cached_data)
        
        return None

    async def _invalidate_product_cache(self, product_id: str):
        """Invalidate product cache in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"product:{product_id}"
        await redis_client.delete(cache_key)


class ErrorLogService:
    """Service for error log operations."""
    
    def __init__(self):
        self.collection_name = "error_logs"

    async def create_error_log(self, error_log: ErrorLog) -> ErrorLog:
        """Create a new error log."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        result = await collection.insert_one(error_log.dict(by_alias=True))
        error_log.id = result.inserted_id
        
        # Cache in Redis
        await self._cache_error_log(error_log)
        
        return error_log

    async def get_error_log(self, error_log_id: str) -> Optional[ErrorLog]:
        """Get an error log by ID."""
        # Try Redis cache first
        cached_error = await self._get_cached_error_log(error_log_id)
        if cached_error:
            return cached_error
        
        # Get from MongoDB
        collection = await database.get_mongodb_collection(self.collection_name)
        error_data = await collection.find_one({"_id": ObjectId(error_log_id)})
        
        if error_data:
            error_log = ErrorLog(**error_data)
            # Cache in Redis
            await self._cache_error_log(error_log)
            return error_log
        
        return None

    async def get_error_logs(
        self, 
        skip: int = 0, 
        limit: int = 100,
        severity: Optional[ErrorSeverity] = None,
        status: Optional[ErrorStatus] = None,
        source: Optional[str] = None
    ) -> List[ErrorLog]:
        """Get error logs with filters."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        filter_dict = {}
        if severity:
            filter_dict["severity"] = severity
        if status:
            filter_dict["status"] = status
        if source:
            filter_dict["source"] = source
        
        cursor = collection.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
        error_logs = []
        
        async for error_data in cursor:
            error_logs.append(ErrorLog(**error_data))
        
        return error_logs

    async def update_error_log_status(
        self, 
        error_log_id: str, 
        status: ErrorStatus
    ) -> Optional[ErrorLog]:
        """Update error log status."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if status == ErrorStatus.RESOLVED:
            update_data["resolved_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(error_log_id)},
            {"$set": update_data}
        )
        
        if result.modified_count:
            # Invalidate cache
            await self._invalidate_error_log_cache(error_log_id)
            # Return updated error log
            return await self.get_error_log(error_log_id)
        
        return None

    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        collection = await database.get_mongodb_collection(self.collection_name)
        
        # Aggregate statistics
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_errors": {"$sum": 1},
                    "by_severity": {
                        "$push": "$severity"
                    },
                    "by_status": {
                        "$push": "$status"
                    },
                    "by_source": {
                        "$push": "$source"
                    }
                }
            }
        ]
        
        result = await collection.aggregate(pipeline).to_list(1)
        if not result:
            return {
                "total_errors": 0,
                "by_severity": {},
                "by_status": {},
                "by_source": {}
            }
        
        stats = result[0]
        
        # Count by severity
        severity_counts = {}
        for severity in stats["by_severity"]:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by status
        status_counts = {}
        for status in stats["by_status"]:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by source
        source_counts = {}
        for source in stats["by_source"]:
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            "total_errors": stats["total_errors"],
            "by_severity": severity_counts,
            "by_status": status_counts,
            "by_source": source_counts
        }

    async def _cache_error_log(self, error_log: ErrorLog):
        """Cache error log in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"error_log:{error_log.id}"
        await redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            error_log.json()
        )

    async def _get_cached_error_log(self, error_log_id: str) -> Optional[ErrorLog]:
        """Get error log from Redis cache."""
        redis_client = await database.get_redis_client()
        cache_key = f"error_log:{error_log_id}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            return ErrorLog.parse_raw(cached_data)
        
        return None

    async def _invalidate_error_log_cache(self, error_log_id: str):
        """Invalidate error log cache in Redis."""
        redis_client = await database.get_redis_client()
        cache_key = f"error_log:{error_log_id}"
        await redis_client.delete(cache_key)

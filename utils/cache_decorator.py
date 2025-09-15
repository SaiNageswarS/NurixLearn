"""Simple request/response caching decorator for API endpoints."""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta


class SimpleCache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from function arguments."""
        # Create a string representation of the arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry['expires_at']:
            # Expired, remove from cache
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get the number of cache entries."""
        return len(self.cache)


# Global cache instance
api_cache = SimpleCache(default_ttl=3600)  # 1 hour TTL


def cache_response(ttl: int = 3600, key_func: Optional[Callable] = None):
    """
    Decorator to cache API responses.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        key_func: Optional function to generate custom cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = api_cache._generate_key(*args, **kwargs)
            
            # Check cache first
            cached_result = api_cache.get(cache_key)
            if cached_result is not None:
                print(f"🎯 Cache hit for key: {cache_key[:16]}...")
                return cached_result
            
            # Execute function and cache result
            print(f"🔄 Cache miss for key: {cache_key[:16]}...")
            result = await func(*args, **kwargs)
            
            # Cache the result
            api_cache.set(cache_key, result, ttl)
            print(f"💾 Cached result for key: {cache_key[:16]}...")
            
            return result
        
        return wrapper
    return decorator


def generate_request_cache_key(*args, **kwargs) -> str:
    """Generate a cache key based on request data for math evaluation."""
    # Extract request data from kwargs (assuming the request is in kwargs)
    request = None
    for arg in args:
        if hasattr(arg, 'question_url') and hasattr(arg, 'solution_url'):
            request = arg
            break
    
    if not request:
        # Fallback to default key generation
        return api_cache._generate_key(*args, **kwargs)
    
    # Create a key based on question and solution URLs
    key_data = {
        'question_url': request.question_url,
        'solution_url': request.solution_url,
        'bounding_box': request.bounding_box,
        'user_id': request.user_id,
        'question_attempt_id': request.question_attempt_id
    }
    
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

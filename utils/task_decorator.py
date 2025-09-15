"""Task decorator with retry logic."""

import asyncio
import functools
import logging
from typing import Callable, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def task(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    timeout: Optional[float] = None
):
    """
    Decorator for async tasks with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        timeout: Timeout for the entire task in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            task_name = func.__name__
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"🔄 Executing task: {task_name} (attempt {attempt + 1})")
                    
                    if timeout:
                        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    else:
                        result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"✅ Task succeeded after {attempt + 1} attempts: {task_name}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"❌ Task failed (attempt {attempt + 1}): {task_name} - {e}")
                    
                    if attempt < max_retries:
                        delay = retry_delay * (backoff_factor ** attempt)
                        logger.info(f"⏳ Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"💥 Task failed after {max_retries + 1} attempts: {task_name}")
                        raise last_exception
            
        return wrapper
    return decorator

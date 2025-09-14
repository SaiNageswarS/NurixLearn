"""Main entry point for the Temporal worker."""

import asyncio
import signal
import sys
from temporalio.worker import Worker

from config.settings import settings
from utils.database import database
from utils.temporal_client import temporal_manager
from jobs.workflows import DetectErrorWorkflow
from jobs.activities import MathEvaluationActivities


async def main():
    """Main worker function."""
    print("🚀 Starting Temporal worker for math evaluation...")
    
    try:
        # Connect to databases
        await database.connect_to_mongodb()
        await database.connect_to_redis()
        
        # Connect to Temporal
        await temporal_manager.connect()
        
        # Create activities instance
        activities = MathEvaluationActivities()
        
        # Start worker
        await temporal_manager.start_worker(
            activities=[activities],
            workflows=[DetectErrorWorkflow]
        )
        
    except KeyboardInterrupt:
        print("🛑 Worker interrupted by user")
    except Exception as e:
        print(f"❌ Worker failed: {e}")
        raise
    finally:
        # Cleanup
        await database.close_mongodb_connection()
        await database.close_redis_connection()
        await temporal_manager.disconnect()
        print("✅ Worker shut down successfully")


if __name__ == "__main__":   
    # Run the worker
    asyncio.run(main())


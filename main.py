"""Main entry point for the FastAPI server."""

import asyncio
import signal
import sys
import uvicorn

from config.settings import settings
from utils.database import database
from services.detect_error_service import api_service


async def initialize_services():
    """Initialize required services."""
    print("🚀 Initializing services...")
    
    try:
        # Connect to databases
        await database.connect_to_mongodb()
        await database.connect_to_redis()
        print("✅ Services initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise


def run_fastapi_server():
    """Run the FastAPI server."""
    print("🌐 Starting FastAPI server...")
    
    app = api_service.get_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


async def main():
    """Main function to run the FastAPI server."""
    print("🚀 Starting Math Evaluation Service...")
    
    try:
        # Initialize services
        await initialize_services()
        
        # Run the FastAPI server
        run_fastapi_server()
        
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Service failed: {e}")
        raise
    finally:
        # Cleanup
        await database.close_mongodb_connection()
        await database.close_redis_connection()
        print("✅ Service shut down successfully")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the service
    asyncio.run(main())
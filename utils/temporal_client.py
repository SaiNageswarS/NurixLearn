"""Temporal client configuration and utilities."""

import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from typing import Optional
from config.settings import settings


class TemporalManager:
    """Temporal client manager."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None

    async def connect(self):
        """Connect to Temporal server."""
        try:
            self.client = await Client.connect(
                settings.temporal_host,
                namespace=settings.temporal_namespace
            )
            print(f"Connected to Temporal: {settings.temporal_host}")
            
        except Exception as e:
            print(f"Failed to connect to Temporal: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Temporal server."""
        if self.worker:
            self.worker.shutdown()
            print("Temporal worker shut down")
        
        if self.client:
            print("Temporal client disconnected")

    def get_client(self) -> Client:
        """Get Temporal client."""
        if not self.client:
            raise RuntimeError("Temporal client not connected")
        return self.client

    async def start_worker(self, activities: list, workflows: list):
        """Start Temporal worker."""
        if not self.client:
            raise RuntimeError("Temporal client not connected")
        
        try:
            self.worker = Worker(
                self.client,
                task_queue=settings.temporal_task_queue,
                activities=activities,
                workflows=workflows
            )
            
            print(f"Started Temporal worker on queue: {settings.temporal_task_queue}")
            await self.worker.run()
            
        except Exception as e:
            print(f"Failed to start Temporal worker: {e}")
            raise


# Global Temporal manager instance
temporal_manager = TemporalManager()

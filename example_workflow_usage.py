"""Example usage of the error detection workflow."""

import asyncio
from datetime import datetime

from config.settings import settings
from utils.database import database
from utils.temporal_client import temporal_manager
from models.data_models import ErrorDetectionInput, ErrorSeverity
from services.workflow_service import workflow_service


async def main():
    """Example usage of the error detection workflow."""
    print("🚀 Starting error detection workflow example...")
    
    # Connect to databases and Temporal
    await database.connect_to_mongodb()
    await database.connect_to_redis()
    await temporal_manager.connect()
    await workflow_service.initialize()
    
    try:
        # Example 1: Start a one-time error detection workflow
        print("\n📝 Starting one-time error detection workflow...")
        input_data = ErrorDetectionInput(
            source="web-application",
            error_patterns=[
                "Exception",
                "Error",
                "Critical error",
                "Database connection failed",
                "Timeout"
            ],
            severity_threshold=ErrorSeverity.MEDIUM,
            user_id="admin",
            metadata={
                "environment": "production",
                "version": "1.0.0"
            }
        )
        
        workflow_id = await workflow_service.start_error_detection_workflow(input_data)
        print(f"✅ Started workflow: {workflow_id}")
        
        # Wait a bit for the workflow to process
        await asyncio.sleep(5)
        
        # Check workflow status
        status = await workflow_service.get_workflow_status(workflow_id)
        print(f"📊 Workflow status: {status}")
        
        # Example 2: Start a continuous monitoring workflow
        print("\n🔄 Starting continuous error monitoring workflow...")
        monitoring_input = ErrorDetectionInput(
            source="api-service",
            error_patterns=[
                "500 Internal Server Error",
                "Database timeout",
                "Memory leak",
                "Connection pool exhausted"
            ],
            severity_threshold=ErrorSeverity.HIGH,
            user_id="admin",
            metadata={
                "environment": "production",
                "service": "api-gateway"
            }
        )
        
        monitoring_workflow_id = await workflow_service.start_monitoring_workflow(monitoring_input)
        print(f"✅ Started monitoring workflow: {monitoring_workflow_id}")
        
        # Let it run for a bit
        await asyncio.sleep(10)
        
        # List active workflows
        active_workflows = await workflow_service.list_active_workflows()
        print(f"📋 Active workflows: {len(active_workflows)}")
        for workflow in active_workflows:
            print(f"  - {workflow['id']}: {workflow['status']}")
        
        # Example 3: Simulate resolving an error
        print("\n🔧 Simulating error resolution...")
        # In a real scenario, you would get the actual error ID from the workflow result
        sample_error_id = "sample_error_123"
        success = await workflow_service.signal_resolve_error(workflow_id, sample_error_id)
        print(f"✅ Resolve signal sent: {success}")
        
        # Example 4: Stop the monitoring workflow
        print("\n🛑 Stopping monitoring workflow...")
        stop_success = await workflow_service.stop_monitoring_workflow(monitoring_workflow_id)
        print(f"✅ Stop signal sent: {stop_success}")
        
        # Wait for workflows to complete
        await asyncio.sleep(5)
        
        # Get final workflow result
        result = await workflow_service.get_workflow_result(workflow_id)
        if result:
            print(f"\n📊 Final workflow result:")
            print(f"  - Errors detected: {result.errors_detected}")
            print(f"  - Errors resolved: {result.errors_resolved}")
            print(f"  - Status: {result.status}")
            print(f"  - Completed at: {result.completed_at}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Close connections
        await database.close_mongodb_connection()
        await database.close_redis_connection()
        await temporal_manager.disconnect()
        print("\n✅ Example completed!")


if __name__ == "__main__":
    asyncio.run(main())

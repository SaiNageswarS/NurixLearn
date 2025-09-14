"""Example usage of the math evaluation workflow."""

import asyncio
from datetime import datetime

from config.settings import settings
from utils.database import database
from utils.temporal_client import temporal_manager
from utils.azure_storage import azure_storage
from models.data_models import MathEvaluationInput, BoundingBox
from services.workflow_service import workflow_service


async def main():
    """Example usage of the math evaluation workflow."""
    print("🚀 Starting math evaluation workflow example...")
    
    # Connect to databases and Temporal
    await database.connect_to_mongodb()
    await database.connect_to_redis()
    await temporal_manager.connect()
    await workflow_service.initialize()
    
    try:
        # Example 0: Test Azure storage directly
        print("\n🔍 Testing Azure storage functionality...")
        try:
            # Test image metadata retrieval
            question_url = "https://your-storage-account.blob.core.windows.net/math-images/question_001.jpg"
            working_note_url = "https://your-storage-account.blob.core.windows.net/math-images/working_note_001.jpg"
            
            # Get metadata for both images
            metadata = await azure_storage.get_both_images_metadata(question_url, working_note_url)
            print(f"📊 Image metadata:")
            print(f"  - Question image size: {metadata['question_image']['size']} bytes")
            print(f"  - Working note size: {metadata['working_note_image']['size']} bytes")
            print(f"  - Total size: {metadata['total_size']} bytes")
            
        except Exception as e:
            print(f"⚠️ Azure storage test failed (expected if URLs don't exist): {e}")
        
        # Example 1: Single math evaluation with bounding box
        print("\n📝 Starting single math evaluation workflow...")
        input_data = MathEvaluationInput(
            question_image_url="https://your-storage-account.blob.core.windows.net/math-images/question_001.jpg",
            working_note_url="https://your-storage-account.blob.core.windows.net/math-images/working_note_001.jpg",
            bounding_box=BoundingBox(
                x=100,  # X coordinate of top-left corner
                y=150,  # Y coordinate of top-left corner
                width=400,  # Width of the bounding box
                height=300  # Height of the bounding box
            ),
            student_id="student_123",
            assignment_id="assignment_001",
            evaluation_criteria={
                "check_calculations": True,
                "check_method": True,
                "check_final_answer": True,
                "provide_feedback": True
            },
            metadata={
                "subject": "algebra",
                "difficulty": "intermediate",
                "time_limit": 30
            }
        )
        
        workflow_id = await workflow_service.start_math_evaluation_workflow(input_data)
        print(f"✅ Started workflow: {workflow_id}")
        
        # Wait for the workflow to process
        await asyncio.sleep(10)
        
        # Check workflow status
        status = await workflow_service.get_workflow_status(workflow_id)
        print(f"📊 Workflow status: {status}")
        
        # Check workflow progress
        progress = await workflow_service.get_workflow_progress(workflow_id)
        print(f"📈 Workflow progress: {progress}")
        print(f"  - Steps completed: {progress.get('steps_completed', [])}")
        print(f"  - Steps remaining: {progress.get('steps_remaining', [])}")
        
        # Example 2: Math evaluation without bounding box
        print("\n📝 Starting math evaluation without bounding box...")
        input_data_no_crop = MathEvaluationInput(
            question_image_url="https://your-storage-account.blob.core.windows.net/math-images/question_002.jpg",
            working_note_url="https://your-storage-account.blob.core.windows.net/math-images/working_note_002.jpg",
            # No bounding_box provided - will use full image
            student_id="student_124",
            assignment_id="assignment_001"
        )
        
        workflow_id_2 = await workflow_service.start_math_evaluation_workflow(input_data_no_crop)
        print(f"✅ Started workflow without cropping: {workflow_id_2}")
        
        # Let it run for a bit
        await asyncio.sleep(15)
        
        # List active workflows
        active_workflows = await workflow_service.list_active_workflows()
        print(f"📋 Active workflows: {len(active_workflows)}")
        for workflow in active_workflows:
            print(f"  - {workflow['id']}: {workflow['status']}")
        
        # Example 3: Send signals to workflow
        print("\n📡 Sending signals to workflow...")
        
        # Update evaluation criteria
        new_criteria = {
            "check_calculations": True,
            "check_method": True,
            "check_final_answer": True,
            "provide_feedback": True,
            "detailed_explanation": True
        }
        success = await workflow_service.signal_update_criteria(workflow_id, new_criteria)
        print(f"✅ Update criteria signal sent: {success}")
        
        # Request manual review
        review_reason = "Complex mathematical concept requires human verification"
        success = await workflow_service.signal_request_manual_review(workflow_id, review_reason)
        print(f"✅ Manual review request sent: {success}")
        
        # Wait for workflows to complete
        await asyncio.sleep(10)
        
        # Get final workflow result
        result = await workflow_service.get_workflow_result(workflow_id)
        if result:
            print(f"\n📊 Final workflow result:")
            print(f"  - Correctness Score: {result.correctness_score}")
            print(f"  - Errors Found: {len(result.errors_found)}")
            print(f"  - Status: {result.status}")
            print(f"  - Feedback: {result.feedback[:100]}...")
            print(f"  - Completed at: {result.completed_at}")
        
        # Get second workflow result
        result_2 = await workflow_service.get_workflow_result(workflow_id_2)
        if result_2:
            print(f"\n📊 Second workflow result:")
            print(f"  - Correctness Score: {result_2.correctness_score}")
            print(f"  - Errors Found: {len(result_2.errors_found)}")
            print(f"  - Status: {result_2.status}")
            print(f"  - Completed at: {result_2.completed_at}")
        
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

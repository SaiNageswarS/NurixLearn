"""Main entry point for the FastAPI server or direct workflow execution."""

import argparse
import asyncio
import signal
import sys
import uvicorn
from typing import Optional

from config.settings import settings
from utils.database import database
from services.detect_error_service import api_service
from jobs.workflow import DetectErrorWorkflow
from models.data_models import MathEvaluationInput, BoundingBox


async def initialize_services():
    """Initialize required services."""
    print("🚀 Initializing services...")
    
    try:
        # Connect to databases
        # await database.connect_to_mongodb()
        # await database.connect_to_redis()
        print("✅ Services initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise


async def run_fastapi_server():
    """Run the FastAPI server."""
    print("🌐 Starting FastAPI server...")
    
    app = api_service.get_app()
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_workflow_directly(args):
    """Run the DetectErrorWorkflow directly with provided inputs."""
    print("🔧 Running DetectErrorWorkflow directly...")
    
    try:
        # Create bounding box if provided
        bounding_box = None
        if args.bbox_x is not None and args.bbox_y is not None and args.bbox_width is not None and args.bbox_height is not None:
            bounding_box = BoundingBox(
                x=args.bbox_x,
                y=args.bbox_y,
                width=args.bbox_width,
                height=args.bbox_height
            )
        
        # Create input data
        input_data = MathEvaluationInput(
            container_name=args.container_name,
            question_image=args.question_image,
            working_note_image=args.working_note_image,
            bounding_box=bounding_box,
            student_id=args.student_id,
            assignment_id=args.assignment_id
        )
        
        print(f"📋 Input data:")
        print(f"   Container: {input_data.container_name}")
        print(f"   Question Image: {input_data.question_image}")
        print(f"   Working Note Image: {input_data.working_note_image}")
        if bounding_box:
            print(f"   Bounding Box: x={bounding_box.x}, y={bounding_box.y}, w={bounding_box.width}, h={bounding_box.height}")
        if args.student_id:
            print(f"   Student ID: {args.student_id}")
        if args.assignment_id:
            print(f"   Assignment ID: {args.assignment_id}")
        
        # Initialize and run workflow
        workflow = DetectErrorWorkflow()
        result = await workflow.run(input_data)
        
        print(f"\n🎉 Workflow completed successfully!")
        print(f"📊 Result:")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Status: {result.status}")
        print(f"   Correctness Score: {result.correctness_score}")
        print(f"   Errors Found: {len(result.errors_found)}")
        if result.feedback:
            print(f"   Feedback: {result.feedback}")
        if result.evaluation_id:
            print(f"   Evaluation ID: {result.evaluation_id}")
        
        return result
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        raise


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Math Evaluation Service - Run FastAPI server or execute workflow directly",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run FastAPI server
  python main.py --mode server
  
  # Run workflow directly
  python main.py --mode workflow --container my-container --question-image question.jpg --working-note-image working.jpg
  
  # Run workflow with bounding box
  python main.py --mode workflow --container my-container --question-image question.jpg --working-note-image working.jpg --bbox-x 100 --bbox-y 50 --bbox-width 200 --bbox-height 150
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["server", "workflow"], 
        default="server",
        help="Mode to run: 'server' for FastAPI server, 'workflow' for direct workflow execution (default: server)"
    )
    
    # Workflow-specific arguments
    parser.add_argument("--container-name", help="Container name for the images")
    parser.add_argument("--question-image", help="Image name for the printed question")
    parser.add_argument("--working-note-image", help="Image name for the handwritten working note")
    
    # Optional workflow arguments
    parser.add_argument("--student-id", help="Student identifier")
    parser.add_argument("--assignment-id", help="Assignment identifier")
    
    # Bounding box arguments
    parser.add_argument("--bbox-x", type=int, help="X coordinate of bounding box top-left corner")
    parser.add_argument("--bbox-y", type=int, help="Y coordinate of bounding box top-left corner")
    parser.add_argument("--bbox-width", type=int, help="Width of the bounding box")
    parser.add_argument("--bbox-height", type=int, help="Height of the bounding box")
    
    return parser.parse_args()


async def main():
    """Main function to run either FastAPI server or workflow directly."""
    args = parse_arguments()
    
    if args.mode == "server":
        print("🚀 Starting Math Evaluation Service (FastAPI Server Mode)...")
        
        try:
            # Initialize services
            await initialize_services()
            
            # Run the FastAPI server
            await run_fastapi_server()
            
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
    
    elif args.mode == "workflow":
        print("🚀 Starting Math Evaluation Service (Direct Workflow Mode)...")
        
        # Validate required arguments for workflow mode
        if not args.container_name or not args.question_image or not args.working_note_image:
            print("❌ Error: --container-name, --question-image, and --working-note-image are required for workflow mode")
            sys.exit(1)
        
        try:
            # Initialize services
            await initialize_services()
            
            # Run workflow directly
            await run_workflow_directly(args)
            
        except KeyboardInterrupt:
            print("🛑 Workflow interrupted...")
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            raise
        finally:
            # Cleanup
            await database.close_mongodb_connection()
            await database.close_redis_connection()
            print("✅ Workflow completed and services shut down")


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
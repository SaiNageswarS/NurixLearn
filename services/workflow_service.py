"""Service for managing Temporal workflows."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from temporalio.client import WorkflowHandle

from models.data_models import MathEvaluationInput, MathEvaluationResult, MathEvaluationLog
from utils.temporal_client import temporal_manager
from jobs.workflows import DetectErrorWorkflow


class WorkflowService:
    """Service for managing math evaluation workflows."""
    
    def __init__(self):
        self.client = None

    async def initialize(self):
        """Initialize the workflow service."""
        await temporal_manager.connect()
        self.client = temporal_manager.get_client()

    async def start_math_evaluation_workflow(
        self, 
        input_data: MathEvaluationInput,
        workflow_id: Optional[str] = None
    ) -> str:
        """Start a new math evaluation workflow."""
        if not self.client:
            await self.initialize()
        
        # Generate workflow ID if not provided
        if not workflow_id:
            workflow_id = f"math-eval-{input_data.student_id or 'unknown'}-{int(datetime.now().timestamp())}"
        
        # Start the workflow
        handle = await self.client.start_workflow(
            DetectErrorWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue="math-evaluation-queue"
        )
        
        print(f"🚀 Started math evaluation workflow: {workflow_id}")
        return workflow_id


    async def get_workflow_result(self, workflow_id: str) -> Optional[MathEvaluationResult]:
        """Get the result of a completed workflow."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            result = await handle.result()
            return result
        except Exception as e:
            print(f"❌ Failed to get workflow result: {e}")
            return None

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            status = await handle.query(DetectErrorWorkflow.get_evaluation_status)
            return status
        except Exception as e:
            print(f"❌ Failed to get workflow status: {e}")
            return None

    async def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the detailed progress of a workflow."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            progress = await handle.query(DetectErrorWorkflow.get_evaluation_progress)
            return progress
        except Exception as e:
            print(f"❌ Failed to get workflow progress: {e}")
            return None

    async def signal_update_criteria(self, workflow_id: str, criteria: Dict[str, Any]) -> bool:
        """Send a signal to update evaluation criteria."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            await handle.signal(DetectErrorWorkflow.update_evaluation_criteria, criteria)
            print(f"✅ Sent update criteria signal: {criteria}")
            return True
        except Exception as e:
            print(f"❌ Failed to send update criteria signal: {e}")
            return False

    async def signal_request_manual_review(self, workflow_id: str, reason: str) -> bool:
        """Send a signal to request manual review."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            await handle.signal(DetectErrorWorkflow.request_manual_review, reason)
            print(f"✅ Sent manual review request: {reason}")
            return True
        except Exception as e:
            print(f"❌ Failed to send manual review request: {e}")
            return False


    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows."""
        if not self.client:
            await self.initialize()
        
        try:
            workflows = []
            async for workflow in self.client.list_workflows():
                if workflow.status.name == "RUNNING":
                    workflows.append({
                        "id": workflow.id,
                        "type": workflow.type,
                        "status": workflow.status.name,
                        "start_time": workflow.start_time.isoformat() if workflow.start_time else None
                    })
            return workflows
        except Exception as e:
            print(f"❌ Failed to list workflows: {e}")
            return []

    async def get_workflow_history(self, workflow_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get the history of a workflow."""
        if not self.client:
            await self.initialize()
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            history = []
            
            async for event in handle.fetch_history_events():
                history.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type.name,
                    "timestamp": event.event_time.isoformat() if event.event_time else None,
                    "details": str(event)
                })
            
            return history
        except Exception as e:
            print(f"❌ Failed to get workflow history: {e}")
            return None


# Global workflow service instance
workflow_service = WorkflowService()

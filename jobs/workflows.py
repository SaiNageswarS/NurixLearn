"""Temporal workflows for math evaluation."""

import asyncio
from datetime import timedelta
from typing import Dict, Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from models.data_models import MathEvaluationInput, MathEvaluationResult
from jobs.activities import MathEvaluationActivities


@workflow.defn
class DetectErrorWorkflow:
    """Workflow for evaluating handwritten mathematical calculations."""

    def __init__(self):
        self.activities = MathEvaluationActivities()

    @workflow.run
    async def run(self, input_data: MathEvaluationInput) -> MathEvaluationResult:
        """Main workflow execution for math evaluation."""
        
        workflow_id = workflow.info().workflow_id
        print(f"🚀 Starting math evaluation workflow: {workflow_id}")
        
        result = MathEvaluationResult(
            workflow_id=workflow_id,
            status="started"
        )
        
        temp_files = []  # Track temporary files for cleanup
        
        try:
            # Step 1: Download both images
            question_image_path, working_note_path = await workflow.execute_activity(
                self.activities.download_problem_images,
                args=[input_data.question_image_url, input_data.working_note_url],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=3
                )
            )
            temp_files.extend([question_image_path, working_note_path])
            
            # Step 2: Crop working note image if bounding box is provided
            if input_data.bounding_box:
                working_note_path = await workflow.execute_activity(
                    self.activities.crop_working_note_image,
                    args=[working_note_path, input_data.bounding_box],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=5),
                        maximum_attempts=2
                    )
                )
                temp_files.append(working_note_path)
            
            # Step 3: Preprocess images
            processed_question_path, processed_working_note_path = await workflow.execute_activity(
                self.activities.preprocess_images,
                args=[question_image_path, working_note_path],
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2
                )
            )
            temp_files.extend([processed_question_path, processed_working_note_path])
            
            # Step 4: Analyze with LLM
            analysis_result = await workflow.execute_activity(
                self.activities.analyze_with_llm,
                args=[processed_question_path, processed_working_note_path],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3
                )
            )
            
            # Step 5: Validate result
            validated_result = await workflow.execute_activity(
                self.activities.validate_result,
                args=[analysis_result],
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            # Step 6: Save evaluation result
            evaluation_id = await workflow.execute_activity(
                self.activities.save_evaluation_result,
                args=[
                    validated_result,
                    workflow_id,
                    input_data.student_id,
                    input_data.assignment_id,
                    input_data.question_image_url,
                    input_data.working_note_url
                ],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=3
                )
            )
            
            # Update result with analysis data
            result.question_analysis = validated_result.get('question_analysis', {})
            result.working_note_analysis = validated_result.get('working_note_analysis', {})
            result.correctness_score = validated_result.get('correctness_score', 0.0)
            result.errors_found = validated_result.get('errors_found', [])
            result.feedback = validated_result.get('feedback', '')
            result.evaluation_id = evaluation_id
            result.status = "completed"
            result.completed_at = workflow.now()
            
            print(f"✅ Math evaluation workflow completed successfully")
            print(f"📊 Correctness Score: {result.correctness_score}")
            print(f"🔍 Errors Found: {len(result.errors_found)}")
            
        except Exception as e:
            print(f"❌ Math evaluation workflow failed: {e}")
            result.status = "failed"
            result.completed_at = workflow.now()
            result.feedback = f"Evaluation failed: {str(e)}"
            raise
        
        finally:
            # Step 7: Cleanup temporary files
            if temp_files:
                await workflow.execute_activity(
                    self.activities.cleanup_temp_files,
                    args=temp_files,
                    start_to_close_timeout=timedelta(minutes=1)
                )
        
        return result

    @workflow.query
    def get_evaluation_status(self) -> Dict[str, Any]:
        """Query to get current evaluation status."""
        return {
            "workflow_id": workflow.info().workflow_id,
            "status": "running",
            "started_at": workflow.now().isoformat(),
            "current_step": "processing"
        }

    @workflow.query
    def get_evaluation_progress(self) -> Dict[str, Any]:
        """Query to get detailed evaluation progress."""
        return {
            "workflow_id": workflow.info().workflow_id,
            "progress_percentage": 60,  # This would be calculated based on completed steps
            "current_step": "llm_analysis",
            "steps_completed": [
                "download_problem_images",
                "crop_working_note_image",
                "preprocess_images"
            ],
            "steps_remaining": [
                "analyze_with_llm",
                "validate_result",
                "save_evaluation_result"
            ]
        }

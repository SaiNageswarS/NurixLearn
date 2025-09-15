"""Simple workflow orchestrator for math evaluation."""

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Dict, Any
import uuid

from models.data_models import MathEvaluationInput, MathEvaluationResult
from jobs.activities import (
    download_problem_images,
    crop_working_note_image,
    preprocess_images,
    analyze_with_llm,
    validate_result,
    cleanup_temp_files
)


class DetectErrorWorkflow:
    """Simple workflow orchestrator for math evaluation."""

    async def run(self, input_data: MathEvaluationInput) -> MathEvaluationResult:
        """Execute the math evaluation workflow."""
        
        workflow_id = f"detect_error_{int(datetime.now().timestamp())}"
        print(f"Starting math evaluation workflow: {workflow_id}")
        
        result = MathEvaluationResult(
            workflow_id=workflow_id,
            status="started"
        )
        
        temp_files = []
        
        try:
            # Step 1: Download both images
            print("📥 Step 1: Downloading images...")
            question_image_path, working_note_path = await download_problem_images(
                input_data.container_name,
                input_data.question_image,
                input_data.working_note_image
            )
            temp_files.extend([question_image_path, working_note_path])
            
            # Step 2: Crop working note image if bounding box is provided
            if input_data.bounding_box:
                print("✂️ Step 2: Cropping working note image...")
                working_note_path = await crop_working_note_image(
                    working_note_path, 
                    input_data.bounding_box
                )
                temp_files.append(working_note_path)
            
            # Step 3: Preprocess images
            print("🖼️ Step 3: Preprocessing images...")
            processed_question_path, processed_working_note_path = await preprocess_images(
                question_image_path, 
                working_note_path
            )
            temp_files.extend([processed_question_path, processed_working_note_path])
            
            # Step 4: Analyze with LLM
            print("🤖 Step 4: Analyzing with LLM...")
            analysis_result = await analyze_with_llm(
                processed_question_path, 
                processed_working_note_path
            )
            
            # Step 5: Validate result
            print("✅ Step 5: Validating result...")
            validated_result = await validate_result(analysis_result)
            
            # Update result with analysis data
            result.question_analysis = validated_result.get('question_analysis', {})
            result.working_note_analysis = validated_result.get('working_note_analysis', {})
            result.correctness_score = validated_result.get('correctness_score', 0.0)
            result.errors_found = validated_result.get('errors_found', [])
            result.feedback = validated_result.get('feedback', '')
            result.evaluation_id = uuid.uuid4()
            result.status = "completed"
            result.completed_at = datetime.utcnow()
            
            print(f"✅ Math evaluation workflow completed successfully")
            print(f"📊 Correctness Score: {result.correctness_score}")
            print(f"🔍 Errors Found: {len(result.errors_found)}")
            
        except Exception as e:
            print(f"Math evaluation workflow failed: {e}")
            result.status = "failed"
            result.completed_at = datetime.utcnow()
            result.feedback = f"Evaluation failed: {str(e)}"
            raise
        
        finally:
            # Cleanup temporary files
            if temp_files:
                print("Cleaning up temporary files...")
                await cleanup_temp_files(*temp_files)
        
        return result


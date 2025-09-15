"""Async tasks for math evaluation."""

import asyncio
import os
import tempfile
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import openai
from anthropic import Anthropic

from main import main
from models.data_models import MathEvaluationLog, MathEvaluationResult, BoundingBox
from utils.database import database
from utils.storage import StorageManager, azure_storage
from config.settings import settings
from utils.task_decorator import task


@task(max_retries=3, retry_delay=1.0, timeout=300)
async def download_problem_images(
    container_name: str,
    question_image: str,
    working_note_image: str,
    storage_manager: StorageManager = None
) -> Tuple[str, str]:
    """Download both question and working note images using the provided storage manager."""
    if storage_manager is None:
        storage_manager = azure_storage  # Default to Azure storage for backward compatibility
    
    print(f"📥 Downloading both images using {storage_manager.__class__.__name__}")
    
    # Use the provided storage manager to download both images
    question_image_path = await storage_manager.download_image(container_name, question_image)
    working_note_path = await storage_manager.download_image(container_name, working_note_image)
    
    print(f"Downloaded both images successfully")
    print(f"  - Question image: {question_image_path}")
    print(f"  - Working note image: {working_note_path}")
    
    return question_image_path, working_note_path


@task(max_retries=2, retry_delay=0.5, timeout=120)
async def crop_working_note_image(working_note_path: str, bounding_box: BoundingBox) -> str:
    """Crop the working note image using the provided bounding box."""
    print(f"Cropping working note image with bounding box: {bounding_box}")
    
    # Read the image
    image = cv2.imread(working_note_path)
    if image is None:
        raise ValueError(f"Could not read image: {working_note_path}")
    
    # Get image dimensions
    height, width = image.shape[:2]
    print(f"📏 Original image dimensions: {width}x{height}")
    
    # Validate bounding box coordinates
    if (bounding_box.x + bounding_box.width > width or 
        bounding_box.y + bounding_box.height > height):
        print(f"⚠️ Bounding box exceeds image dimensions, adjusting...")
        # Adjust bounding box to fit within image
        x = max(0, min(bounding_box.x, width - 1))
        y = max(0, min(bounding_box.y, height - 1))
        w = min(bounding_box.width, width - x)
        h = min(bounding_box.height, height - y)
        print(f"📐 Adjusted bounding box: x={x}, y={y}, w={w}, h={h}")
    else:
        x, y, w, h = bounding_box.x, bounding_box.y, bounding_box.width, bounding_box.height
    
    # Crop the image
    cropped_image = image[y:y+h, x:x+w]
    
    # Create output path
    base_name = os.path.splitext(working_note_path)[0]
    cropped_path = f"{base_name}_cropped.jpg"
    
    # Save cropped image
    cv2.imwrite(cropped_path, cropped_image)
    
    # Verify the cropped image
    cropped_height, cropped_width = cropped_image.shape[:2]
    print(f"✅ Cropped image saved: {cropped_path}")
    print(f"📏 Cropped image dimensions: {cropped_width}x{cropped_height}")
    
    return cropped_path


@task(max_retries=2, retry_delay=0.5, timeout=180)
async def preprocess_images(question_image_path: str, working_note_path: str) -> Tuple[str, str]:
    """Preprocess both images for better LLM analysis."""
    print("🖼️ Preprocessing images for LLM analysis")
    
    # Process question image
    processed_question_path = await _preprocess_single_image(question_image_path, "question")
    
    # Process working note image
    processed_working_note_path = await _preprocess_single_image(working_note_path, "working_note")
    
    print("✅ Images preprocessed successfully")
    return processed_question_path, processed_working_note_path


async def _preprocess_single_image(image_path: str, image_type: str) -> str:
    """Preprocess a single image."""
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Enhance contrast
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
    
    # Create output path
    output_path = image_path.replace('.jpg', f'_processed_{image_type}.jpg')
    
    # Save processed image
    cv2.imwrite(output_path, cv2.cvtColor(denoised, cv2.COLOR_RGB2BGR))
    
    return output_path


@task(max_retries=3, retry_delay=2.0, timeout=600)
async def analyze_with_llm(question_image_path: str, working_note_path: str) -> Dict[str, Any]:
    """Analyze both images using LLM vision capabilities."""
    print("🤖 Analyzing images with LLM")
    
    # Encode images to base64
    question_image_b64 = await _encode_image_to_base64(question_image_path)
    working_note_b64 = await _encode_image_to_base64(working_note_path)
    
    # Try different LLM providers
    analysis_result = None
    
    # Try OpenAI first
    if settings.openai_api_key:
        try:
            analysis_result = await _analyze_with_openai(question_image_b64, working_note_b64)
        except Exception as e:
            print(f"⚠️ OpenAI analysis failed: {e}")
    
    # Try Azure OpenAI if OpenAI failed
    if not analysis_result and settings.azure_openai_api_key:
        try:
            analysis_result = await _analyze_with_azure_openai(question_image_b64, working_note_b64)
        except Exception as e:
            print(f"⚠️ Azure OpenAI analysis failed: {e}")
    
    # Try Anthropic if others failed
    if not analysis_result and settings.anthropic_api_key:
        try:
            analysis_result = await _analyze_with_anthropic(question_image_b64, working_note_b64)
        except Exception as e:
            print(f"⚠️ Anthropic analysis failed: {e}")
    
    if not analysis_result:
        raise Exception("All LLM providers failed")
    
    print("✅ LLM analysis completed successfully")
    return analysis_result


async def _encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


async def _analyze_with_openai(question_b64: str, working_note_b64: str) -> Dict[str, Any]:
    """Analyze images using OpenAI GPT-4V."""
    client = openai.OpenAI(api_key=settings.openai_api_key)
    
    prompt = """
    Analyze these two images:

    1. QUESTION IMAGE: A printed mathematical problem
    2. WORKING NOTE IMAGE: Student's handwritten solution

    Please provide a comprehensive analysis in the following JSON format:
    {
        "question_analysis": {
            "problem_text": "Extracted problem text",
            "problem_type": "Type of mathematical problem",
            "expected_solution_method": "Expected approach to solve"
        },
        "working_note_analysis": {
            "solution_steps": ["Step 1", "Step 2", ...],
            "mathematical_operations": ["Operation 1", "Operation 2", ...],
            "final_answer": "Student's final answer"
        },
        "correctness_score": 85.5,
        "errors_found": [
            {
                "step": "Step number or description",
                "error_type": "Type of error",
                "description": "Description of the error",
                "severity": "high/medium/low"
            }
        ],
        "feedback": "Detailed feedback for the student"
    }
    """
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{question_b64}"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{working_note_b64}"}
                    }
                ]
            }
        ],
        max_tokens=2000
    )
    
    # Parse response
    import json
    analysis_text = response.choices[0].message.content
    return json.loads(analysis_text)


async def _analyze_with_azure_openai(question_b64: str, working_note_b64: str) -> Dict[str, Any]:
    """Analyze images using Azure OpenAI."""
    from openai import AzureOpenAI
    
    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )
    
    # Similar implementation to OpenAI but with Azure client
    # Implementation would be similar to _analyze_with_openai
    raise NotImplementedError("Azure OpenAI implementation needed")


async def _analyze_with_anthropic(question_b64: str, working_note_b64: str) -> Dict[str, Any]:
    """Analyze images using Anthropic Claude."""
    client = Anthropic(api_key=settings.anthropic_api_key)
    
    # Anthropic implementation
    # Note: Anthropic's vision API has different format
    raise NotImplementedError("Anthropic implementation needed")


@task(max_retries=2, retry_delay=1.0, timeout=120)
async def validate_result(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the LLM analysis result."""
    print("✅ Validating analysis result")
    
    # Basic validation
    required_fields = ['question_analysis', 'working_note_analysis', 'correctness_score', 'errors_found', 'feedback']
    
    for field in required_fields:
        if field not in analysis_result:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate correctness score
    score = analysis_result.get('correctness_score', 0)
    if not isinstance(score, (int, float)) or score < 0 or score > 100:
        analysis_result['correctness_score'] = 0.0
    
    # Validate errors_found is a list
    if not isinstance(analysis_result.get('errors_found', []), list):
        analysis_result['errors_found'] = []
    
    # Add validation metadata
    analysis_result['validation'] = {
        'validated_at': datetime.utcnow().isoformat(),
        'validation_status': 'passed'
    }
    
    print("✅ Analysis result validated successfully")
    return analysis_result


@task(max_retries=3, retry_delay=1.0, timeout=120)
async def save_evaluation_result(
    analysis_result: Dict[str, Any], 
    workflow_id: str,
    student_id: Optional[str] = None,
    assignment_id: Optional[str] = None,
    question_image_url: str = "",
    working_note_url: str = ""
) -> str:
    """Save evaluation result to database."""
    print("💾 Saving evaluation result to database")
    
    # Generate evaluation ID
    evaluation_id = f"eval_{workflow_id}_{int(datetime.now().timestamp())}"
    
    # Create evaluation log
    evaluation_log = MathEvaluationLog(
        evaluation_id=evaluation_id,
        student_id=student_id,
        assignment_id=assignment_id,
        question_image_url=question_image_url,
        working_note_url=working_note_url,
        correctness_score=analysis_result.get('correctness_score', 0.0),
        errors_found=analysis_result.get('errors_found', []),
        feedback=analysis_result.get('feedback', ''),
        workflow_id=workflow_id,
        metadata=analysis_result
    )
    
    # Save to MongoDB
    collection = await database.get_mongodb_collection("math_evaluations")
    result = await collection.insert_one(evaluation_log.dict(by_alias=True))
    evaluation_log.id = result.inserted_id
    
    # Cache in Redis
    await _cache_evaluation_result(evaluation_log)
    
    print(f"✅ Saved evaluation result with ID: {evaluation_id}")
    return evaluation_id


async def _cache_evaluation_result(evaluation_log: MathEvaluationLog):
    """Cache evaluation result in Redis."""
    redis_client = await database.get_redis_client()
    cache_key = f"math_evaluation:{evaluation_log.evaluation_id}"
    await redis_client.setex(
        cache_key,
        3600,  # 1 hour TTL
        evaluation_log.json()
    )


@task(max_retries=1, retry_delay=0.5, timeout=60)
async def cleanup_temp_files(*file_paths: str):
    """Clean up temporary files."""
    print("🧹 Cleaning up temporary files")
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"✅ Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to clean up {file_path}: {e}")

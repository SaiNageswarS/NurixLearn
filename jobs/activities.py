"""Async tasks for math evaluation."""

import asyncio
import os
import tempfile
import base64
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import openai
from anthropic import Anthropic

from models.data_models import MathEvaluationLog, MathEvaluationResult, BoundingBox
from utils.database import database
from utils.storage import LocalStorageManager, StorageManager
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
        storage_manager = LocalStorageManager()  # Default to Azure storage for backward compatibility
    
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
    
    print(f"✅ Images preprocessed successfully {processed_question_path} {processed_working_note_path}")
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
    import json
    
    client = openai.OpenAI(api_key=settings.openai_api_key)
    
    prompt = """
    You are a helpful math tutor analyzing a student's handwritten solution to a mathematical problem. Your role is to:

    1. Identify any errors in the student's work
    2. Provide clear, encouraging feedback
    3. Guide the student on how to correct mistakes and proceed

    Analyze these two images:
    1. QUESTION IMAGE: A printed mathematical problem
    2. WORKING NOTE IMAGE: Student's handwritten solution

    Provide your analysis in the following JSON format:
    {
        "question_analysis": {
            "problem_text": "Extracted problem text from the question image",
            "problem_type": "Type of mathematical problem (e.g., algebra, geometry, calculus)",
            "expected_solution_method": "Expected approach to solve this problem"
        },
        "working_note_analysis": {
            "solution_steps": ["Step 1: Description", "Step 2: Description", ...],
            "mathematical_operations": ["Operation 1", "Operation 2", ...],
            "final_answer": "Student's final answer"
        },
        "correctness_score": 85.5,
        "errors_found": [
            {
                "step": "Step number or description where error occurs",
                "error_type": "Type of error (e.g., calculation error, method error, conceptual error)",
                "description": "Clear description of what went wrong",
                "severity": "high/medium/low",
                "correction_hint": "Specific hint on how to fix this error",
                "next_steps": "What the student should do next"
            }
        ],
        "feedback": "Encouraging, instructional feedback that: 1) Acknowledges what the student did well, 2) Clearly explains any errors, 3) Provides specific guidance on how to proceed, 4) Encourages the student to continue learning"
    }

    Guidelines for feedback:
    - Be encouraging and supportive
    - Focus on learning and improvement, not just pointing out mistakes
    - Provide specific, actionable advice
    - Use clear, student-friendly language
    - If there are errors, explain WHY they occurred and HOW to fix them
    - If the solution is correct, acknowledge the good work and suggest extensions or related problems

    IMPORTANT: Respond ONLY with valid JSON. Do not include any text before or after the JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use correct vision model
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
            max_tokens=2000,
            temperature=0.1  # Lower temperature for more consistent JSON output
        )
        
        # Get response content
        analysis_text = response.choices[0].message.content
        
        if not analysis_text:
            raise ValueError("Empty response from OpenAI")
        
        print(f"🔍 Raw LLM response: {analysis_text[:200]}...")  # Debug logging
        
        # Clean the response - remove any markdown formatting
        analysis_text = analysis_text.strip()
        if analysis_text.startswith("```json"):
            analysis_text = analysis_text[7:]
        if analysis_text.endswith("```"):
            analysis_text = analysis_text[:-3]
        analysis_text = analysis_text.strip()
        
        # Parse JSON
        try:
            result = json.loads(analysis_text)
            print("✅ Successfully parsed LLM response as JSON")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"🔍 Cleaned response: {analysis_text}")
            
            # Return a fallback response with instructional structure
            return {
                "question_analysis": {
                    "problem_text": "Unable to extract problem text",
                    "problem_type": "Unknown",
                    "expected_solution_method": "Unable to determine"
                },
                "working_note_analysis": {
                    "solution_steps": ["Unable to analyze steps"],
                    "mathematical_operations": ["Unable to identify operations"],
                    "final_answer": "Unable to extract final answer"
                },
                "correctness_score": 0.0,
                "errors_found": [
                    {
                        "step": "Analysis failed",
                        "error_type": "Technical error",
                        "description": f"Unable to analyze the solution due to technical issues: {str(e)}",
                        "severity": "high",
                        "correction_hint": "Please try submitting your solution again. If the problem persists, contact support.",
                        "next_steps": "Resubmit your solution or try a different approach to the problem."
                    }
                ],
                "feedback": "I'm sorry, but I encountered a technical issue while analyzing your solution. Please try submitting your work again, and I'll be happy to help you identify any errors and guide you through the correct approach."
            }
            
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
        raise


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

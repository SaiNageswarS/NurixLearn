"""API service for handling math evaluation requests."""

import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from models.data_models import MathEvaluationInput, BoundingBox, MathEvaluationResult
from jobs.workflow import DetectErrorWorkflow
from utils.database import database
from utils.cache_decorator import cache_response, generate_request_cache_key, api_cache


class DetectErrorRequest(BaseModel):
    """Request model for detect-error API."""
    socket_id: str = Field(..., description="Unique session identifier")
    question_url: str = Field(..., description="URL of the question image")
    solution_url: str = Field(..., description="URL of the solution image")
    bounding_box: Dict[str, float] = Field(..., description="Bounding box coordinates")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    question_attempt_id: Optional[str] = Field(None, description="Optional question attempt identifier")


class DetectErrorResponse(BaseModel):
    """Response model for detect-error API."""
    job_id: str = Field(..., description="Unique job identifier")
    y: float = Field(..., description="Y coordinate for error location")
    error: str = Field(..., description="Error description")
    correction: str = Field(..., description="Correction suggestion")
    hint: str = Field(..., description="Hint for the student")
    solution_complete: bool = Field(..., description="Whether solution is complete")
    contains_diagram: bool = Field(..., description="Whether solution contains diagram")
    question_has_diagram: bool = Field(..., description="Whether question has diagram")
    solution_has_diagram: bool = Field(..., description="Whether solution has diagram")
    llm_used: bool = Field(..., description="Whether LLM was used for analysis")
    solution_lines: list = Field(default_factory=list, description="Solution lines")
    llm_ocr_lines: list = Field(default_factory=list, description="LLM OCR lines")


class DetectErrorService:
    """Service for handling API requests and workflow orchestration."""
    
    def __init__(self):
        self.app = FastAPI(
            title="Math Evaluation API",
            description="API for evaluating handwritten mathematical solutions",
            version="1.0.0"
        )
        self.workflow = DetectErrorWorkflow()
        self._setup_routes()
        self._initialized = False

    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.post("/detect-error", response_model=DetectErrorResponse)
        @cache_response(ttl=3600, key_func=generate_request_cache_key)  # 1 hour cache
        async def detect_error(request: DetectErrorRequest):
            """Detect errors in handwritten mathematical solutions."""
            try:
                # Initialize services if not already done
                if not self._initialized:
                    await self._initialize_services()
                
                # Extract image names from URLs
                question_image = self._extract_image_name_from_url(request.question_url)
                answer_image = self._extract_image_name_from_url(request.solution_url)
                
                # Convert bounding box format
                bounding_box = self._convert_bounding_box(request.bounding_box)
                
                # Create workflow input
                workflow_input = MathEvaluationInput(
                    container_name="default",  # We'll need to extract this from URL or use default
                    question_image=question_image,
                    working_note_image=answer_image,
                    bounding_box=bounding_box,
                    student_id=request.user_id,
                    assignment_id=request.question_attempt_id,
                    metadata={
                        "socket_id": request.socket_id,
                        "session_id": request.session_id,
                        "question_attempt_id": request.question_attempt_id
                    }
                )
                
                # Execute workflow directly (synchronous within the request)
                result = await self.workflow.run(workflow_input)
                
                # Convert result to API response format
                response = self._convert_workflow_result_to_response(result, request)
                
                return response
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "mongodb_connected": database.mongodb_client is not None,
                "redis_connected": database.redis_client is not None,
                "workflow_type": "local_asyncio",
                "cache_size": api_cache.size()
            }

        @self.app.get("/cache/stats")
        async def cache_stats():
            """Get cache statistics."""
            return {
                "cache_size": api_cache.size(),
                "cache_entries": list(api_cache.cache.keys())[:10]  # Show first 10 keys
            }

        @self.app.post("/cache/clear")
        async def clear_cache():
            """Clear the API cache."""
            api_cache.clear()
            return {"message": "Cache cleared successfully", "cache_size": api_cache.size()}

    async def _initialize_services(self):
        """Initialize required services."""
        try:
            await database.connect_to_mongodb()
            await database.connect_to_redis()
            self._initialized = True
            print("✅ API services initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize API services: {e}")
            raise

    def _extract_image_name_from_url(self, url: str) -> str:
        """Extract image name from URL."""
        # Handle different URL formats
        if "/" in url:
            return url.split("/")[-1]  # Get the last part after the last slash
        return url
    
    def _convert_bounding_box(self, bbox_dict: Dict[str, float]) -> BoundingBox:
        """Convert API bounding box format to internal format."""
        # Convert from minX, maxX, minY, maxY to x, y, width, height
        x = int(bbox_dict["minX"])
        y = int(bbox_dict["minY"])
        width = int(bbox_dict["maxX"] - bbox_dict["minX"])
        height = int(bbox_dict["maxY"] - bbox_dict["minY"])
        
        return BoundingBox(x=x, y=y, width=width, height=height)

    def _convert_workflow_result_to_response(self, result: MathEvaluationResult, request: DetectErrorRequest) -> DetectErrorResponse:
        """Convert workflow result to API response format."""
        
        # Extract error information from the result
        errors_found = result.errors_found or []
        primary_error = errors_found[0] if errors_found else {}
        
        # Calculate Y coordinate (middle of bounding box)
        y_coordinate = (request.bounding_box["minY"] + request.bounding_box["maxY"]) / 2
        
        # Determine if solution is complete (based on correctness score)
        solution_complete = result.correctness_score >= 80.0
        
        # Extract solution lines from working note analysis
        working_note_analysis = result.working_note_analysis or {}
        solution_steps = working_note_analysis.get("solution_steps", [])
        
        # Extract LLM OCR lines (same as solution lines for now)
        llm_ocr_lines = solution_steps.copy()
        
        # Determine diagram presence (simplified logic)
        question_analysis = result.question_analysis or {}
        contains_diagram = "diagram" in result.feedback.lower() or "graph" in result.feedback.lower()
        question_has_diagram = "diagram" in question_analysis.get("problem_text", "").lower()
        solution_has_diagram = "diagram" in " ".join(solution_steps).lower()
        
        return DetectErrorResponse(
            job_id=result.workflow_id,
            y=y_coordinate,
            error=primary_error.get("description", "No specific error identified"),
            correction=primary_error.get("correction_hint", primary_error.get("correction", result.feedback)),
            hint=primary_error.get("next_steps", primary_error.get("hint", "Review your calculations step by step")),
            solution_complete=solution_complete,
            contains_diagram=contains_diagram,
            question_has_diagram=question_has_diagram,
            solution_has_diagram=solution_has_diagram,
            llm_used=True,  # Always true since we use LLM for analysis
            solution_lines=solution_steps,
            llm_ocr_lines=llm_ocr_lines
        )

    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app


# Global API service instance
api_service = DetectErrorService()

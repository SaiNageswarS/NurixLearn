"""Pydantic models for the application."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# Math Evaluation Models
class BoundingBox(BaseModel):
    """Bounding box coordinates for cropping."""
    x: int = Field(..., ge=0, description="X coordinate of top-left corner")
    y: int = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: int = Field(..., gt=0, description="Width of the bounding box")
    height: int = Field(..., gt=0, description="Height of the bounding box")


class MathEvaluationInput(BaseModel):
    """Input for math evaluation workflow."""
    # Question image details
    container_name: str = Field(..., description="Container name for the images")
    
    question_image: str = Field(..., description="Image name for the printed question") 
    working_note_image: str = Field(..., description="Image name for the handwritten working note")
    # Optional fields
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box to crop the working note")
    student_id: Optional[str] = Field(None, description="Student identifier")
    assignment_id: Optional[str] = Field(None, description="Assignment identifier")
    evaluation_criteria: Dict[str, Any] = Field(default_factory=dict, description="Custom evaluation criteria")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Backward compatibility properties
    @property
    def question_image_url(self) -> str:
        """Backward compatibility: return question image as URL-like string."""
        return f"{self.container_name}/{self.question_image}"
    
    @property
    def working_note_url(self) -> str:
        """Backward compatibility: return working note image as URL-like string."""
        return f"{self.container_name}/{self.working_note_image}"


class MathEvaluationResult(BaseModel):
    """Result of math evaluation workflow."""
    workflow_id: str = Field(..., description="Temporal workflow ID")
    question_analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis of the question")
    working_note_analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis of the working note")
    correctness_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall correctness score (0-100)")
    errors_found: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors identified")
    feedback: str = Field(default="", description="Detailed feedback for the student")
    status: str = Field(..., description="Workflow status")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    evaluation_id: Optional[str] = Field(None, description="Saved evaluation ID")


class MathEvaluationLog(BaseModel):
    """Math evaluation log model for tracking evaluations."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    student_id: Optional[str] = Field(None, description="Student identifier")
    assignment_id: Optional[str] = Field(None, description="Assignment identifier")
    question_image_url: str = Field(..., description="URL of the question image")
    working_note_url: str = Field(..., description="URL of the working note image")
    correctness_score: float = Field(..., ge=0.0, le=100.0, description="Correctness score")
    errors_found: List[Dict[str, Any]] = Field(default_factory=list, description="Errors identified")
    feedback: str = Field(..., description="Student feedback")
    workflow_id: str = Field(..., description="Temporal workflow ID")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


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
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorStatus(str, Enum):
    """Error status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class User(BaseModel):
    """User model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Product(BaseModel):
    """Product model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=50)
    in_stock: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ErrorLog(BaseModel):
    """Error log model for tracking errors."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    error_id: str = Field(..., description="Unique error identifier")
    message: str = Field(..., description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM)
    status: ErrorStatus = Field(default=ErrorStatus.DETECTED)
    source: str = Field(..., description="Source of the error")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = Field(None, description="Associated user ID")
    workflow_id: Optional[str] = Field(None, description="Temporal workflow ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Math Evaluation Models
class BoundingBox(BaseModel):
    """Bounding box coordinates for cropping."""
    x: int = Field(..., ge=0, description="X coordinate of top-left corner")
    y: int = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: int = Field(..., gt=0, description="Width of the bounding box")
    height: int = Field(..., gt=0, description="Height of the bounding box")


class MathEvaluationInput(BaseModel):
    """Input for math evaluation workflow."""
    question_image_url: str = Field(..., description="URL of the printed question image")
    working_note_url: str = Field(..., description="URL of the handwritten working note image")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box to crop the working note")
    student_id: Optional[str] = Field(None, description="Student identifier")
    assignment_id: Optional[str] = Field(None, description="Assignment identifier")
    evaluation_criteria: Dict[str, Any] = Field(default_factory=dict, description="Custom evaluation criteria")
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ErrorNotification(BaseModel):
    """Error notification model."""
    error_id: str = Field(..., description="Error log ID")
    user_id: str = Field(..., description="User to notify")
    message: str = Field(..., description="Notification message")
    severity: ErrorSeverity = Field(..., description="Error severity")
    sent_at: Optional[datetime] = None


# Request/Response Models
class UserCreate(BaseModel):
    """Model for creating a new user."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)


class UserUpdate(BaseModel):
    """Model for updating a user."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)
    is_active: Optional[bool] = None


class ProductCreate(BaseModel):
    """Model for creating a new product."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=50)
    tags: List[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Model for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    in_stock: Optional[bool] = None
    tags: Optional[List[str]] = None

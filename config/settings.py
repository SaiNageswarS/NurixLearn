"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_database: str = Field(default="myapp", env="MONGODB_DATABASE")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Temporal Configuration
    temporal_host: str = Field(default="localhost:7233", env="TEMPORAL_HOST")
    temporal_namespace: str = Field(default="default", env="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(default="math-evaluation-queue", env="TEMPORAL_TASK_QUEUE")
    
    # Azure Configuration
    azure_storage_connection_string: str = Field(default="", env="AZURE_STORAGE_CONNECTION_STRING")
    azure_storage_container: str = Field(default="math-images", env="AZURE_STORAGE_CONTAINER")
    
    # LLM Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", env="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", env="AZURE_OPENAI_API_VERSION")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # Application Configuration
    app_name: str = Field(default="MathEvaluationApp", env="APP_NAME")
    debug: bool = Field(default=True, env="DEBUG")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

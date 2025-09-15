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
        
    # Azure Configuration
    azure_storage_container: str = Field(default="math-images", env="AZURE_STORAGE_CONTAINER")
    azure_client_id: str = Field(default="", env="AZURE_CLIENT_ID")
    azure_tenant_id: str = Field(default="", env="AZURE_TENANT_ID")
    azure_client_secret: str = Field(default="", env="AZURE_CLIENT_SECRET")
    azure_storage_account_name: str = Field(default="", env="AZURE_STORAGE_ACCOUNT_NAME")
    
    # LLM Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Application Configuration
    app_name: str = Field(default="MathEvaluationApp", env="APP_NAME")
    debug: bool = Field(default=True, env="DEBUG")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

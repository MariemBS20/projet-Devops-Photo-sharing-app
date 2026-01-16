#!/usr/bin/env python3
"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongo_host: str = "mongo"
    mongo_port: int = 27017
    mongo_user: str = ""
    mongo_password: str = ""
    database_name: str = "photos"
    auth_database_name: str = "photos"
    
    # Photographer Service Configuration
    photographer_host: str = "photographer-api"
    photographer_port: int = 80
    photographer_timeout: int = 5
    
    # Tags Service Configuration (gRPC)
    tags_host: str = "tags-service"
    tags_port: int = 50051
    # Photo of day Service Configuration (gRPC)

    photo_of_day_grpc_host: str = "photo-of-day-service"  # ou localhost si test local
    photo_of_day_grpc_port: int = 50052

    # API Configuration
    api_title: str = "Photo Service"
    api_version: str = "1.0.0"
    
    # Image Configuration
    max_image_size_mb: int = 10
    allowed_image_types: list[str] = ["image/jpeg", "image/jpg", "image/png"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def mongodb_url(self) -> str:
        """Construct MongoDB connection URL."""
        conn = "mongodb://"
        if self.mongo_user:
            conn += f"{self.mongo_user}:{self.mongo_password}@"
        conn += f"{self.mongo_host}:{self.mongo_port}"
        conn += f"/{self.database_name}?authSource={self.auth_database_name}"
        return conn
    
    @property
    def photographer_service_url(self) -> str:
        """Construct photographer service base URL."""
        return f"http://{self.photographer_host}:{self.photographer_port}"
    
    @property
    def tags_service_address(self) -> str:
        """Construct tags service gRPC address."""
        return f"{self.tags_host}:{self.tags_port}"
    
    @property
    def max_image_size_bytes(self) -> int:
        """Max image size in bytes."""
        return self.max_image_size_mb * 1024 * 1024


settings = Settings()

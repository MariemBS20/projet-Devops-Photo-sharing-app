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
    database_name: str = "reactions"
    auth_database_name: str = "reactions"

    # Photographer Service Configuration
    photographer_host: str = "photographer-dev"
    photographer_port: int = 8000
    photographer_timeout: int = 5

    # Photo Service Configuration
    photo_host: str = "photo-dev"
    photo_port: int = 8000
    photo_timeout: int = 5

    # Photo of Day gRPC Service Configuration
    PHOTO_OF_DAY_HOST: str = "photo-of-day-dev"
    PHOTO_OF_DAY_PORT: int = 50052
    photo_of_day_timeout: int = 5
    photo_of_day_address: str = "photo-of-day-dev:50052"
    # API Configuration
    api_title: str = "Reaction Service"
    api_version: str = "1.0.0"

    # Reaction Configuration
    allowed_reactions: list[str] = ["coeur", "pouce", "love", "fire", "wow", "sad", "sourire"]

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
    def photo_service_url(self) -> str:
        """Construct photo service base URL."""
        return f"http://{self.photo_host}:{self.photo_port}"
    
    @property
    def photo_of_day_grpc_address(self) -> str:
        """Construct Photo of Day gRPC address."""
        return f"{self.PHOTO_OF_DAY_HOST}:{self.PHOTO_OF_DAY_PORT}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

# Create singleton instance
settings = Settings()
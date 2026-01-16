#!/usr/bin/env python3
"""Configuration for Photo of Day gRPC service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB Configuration
    mongo_host: str = "mongo"
    mongo_port: int = 27017
    mongo_user: str = ""
    mongo_password: str = ""
    database_name: str = "photo_of_day"
    auth_database_name: str = "photo_of_day"

    # gRPC Configuration
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50052

    # Photo Service Configuration
    photo_host: str = "photo-service"
    photo_port: int = 80
    photo_timeout: int = 5

    # Service Configuration
    service_name: str = "Photo of Day Service"
    log_level: str = "INFO"

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
    def photo_service_url(self) -> str:
        """Construct photo service base URL."""
        return f"http://{self.photo_host}:{self.photo_port}"

    @property
    def grpc_address(self) -> str:
        """Construct gRPC server address."""
        return f"{self.grpc_host}:{self.grpc_port}"

    model_config = SettingsConfigDict(env_file=".env")


# Create singleton instance
settings = Settings()
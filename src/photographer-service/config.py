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
    database_name: str = "photographers"
    auth_database_name: str = "photographers"
    
    # API Configuration
    api_title: str = "Photographer Service"
    api_version: str = "1.0.0"
    
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


settings = Settings()

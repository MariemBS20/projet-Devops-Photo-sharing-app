#!/usr/bin/env python3
"""Data models for the Photographer Service."""

from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from beanie import Document


class PhotographerDesc(BaseModel):
    """Photographer description with all attributes."""
    
    display_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=16,
            description="The display name of the photographer",
            examples=["rdoisneau"]
        )
    ]
    first_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            description="The first name of the photographer",
            examples=["robert"]
        )
    ]
    last_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            description="The last name of the photographer",
            examples=["doisneau"]
        )
    ]
    interests: Annotated[
        list[str],
        Field(
            min_length=0,
            description="The interests of the photographer",
            examples=[["street", "portrait"]]
        )
    ]

    @field_validator('display_name', 'first_name', 'last_name')
    @classmethod
    def validate_no_whitespace(cls, v: str) -> str:
        """Ensure names don't contain only whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or contain only whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "display_name": "rdoisneau",
                    "first_name": "robert",
                    "last_name": "doisneau",
                    "interests": ["street", "portrait"],
                }
            ]
        }
    }


class PhotographerDigest(BaseModel):
    """Lightweight photographer representation for lists."""
    
    display_name: str
    link: str


class PhotographersResponse(BaseModel):
    """Paginated response for photographer lists."""
    
    items: list[PhotographerDigest]
    has_more: bool
    total_count: int | None = None


class Photographer(Document, PhotographerDesc):
    """MongoDB document model for photographers."""
    
    class Settings:
        name = "photographers"
        indexes = [
            "display_name",  # Index for faster lookups
        ]

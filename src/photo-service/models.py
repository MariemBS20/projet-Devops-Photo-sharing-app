#!/usr/bin/env python3
"""Data models for the Photo Service."""

from typing import Annotated
from pydantic import BaseModel, Field
from beanie import Document
from datetime import datetime, timezone


class PhotoMetadata(BaseModel):
    """Photo metadata (without the binary file)."""
    
    title: Annotated[
        str,
        Field(
            max_length=100,
            description="Photo title",
            examples=["Sunset over Paris"]
        )
    ] = "untitled"
    
    comment: Annotated[
        str,
        Field(
            max_length=200,
            description="Photo comment or description",
            examples=["Beautiful evening light"]
        )
    ] = ""
    
    location: Annotated[
        str,
        Field(
            max_length=100,
            description="Photo location",
            examples=["Paris, France"]
        )
    ] = ""
    
    author: Annotated[
        str,
        Field(
            max_length=120,
            description="Photo author",
            examples=["John Doe"]
        )
    ] = ""
    
    tags: Annotated[
        list[str],
        Field(
            description="Photo tags (auto-generated)",
            examples=[["landscape", "sunset", "nature"]]
        )
    ] = []


class Photo(Document, PhotoMetadata):
    """MongoDB document for a photo."""
    
    display_name: Annotated[
        str,
        Field(
            max_length=120,
            description="Photographer's display name"
        )
    ]
    
    photo_id: Annotated[
        int,
        Field(
            description="Unique photo ID for this photographer"
        )
    ]
    
    image_data: Annotated[
        bytes,
        Field(
            description="JPEG image binary data"
        )
    ]
    
    # ✅ CORRECTION: Utiliser datetime.now avec timezone UTC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "photos"
        indexes = [
            "display_name",
            "photo_id",
            [("display_name", 1), ("photo_id", 1)],  # Compound index
        ]


class PhotoIdCounter(Document):
    """Counter for generating sequential photo IDs per photographer."""
    
    display_name: str
    next_photo_id: int = 0
    
    class Settings:
        name = "photo_id_counters"
        indexes = ["display_name"]


class PhotoDigest(BaseModel):
    """Lightweight photo representation for lists."""
    
    photo_id: int
    link: str


class PhotosResponse(BaseModel):
    """Paginated response for photo lists."""
    
    items: list[PhotoDigest]
    has_more: bool
    total_count: int | None = None


class PhotoAttributesUpdate(BaseModel):
    """Attributes that can be updated (no tags, no image)."""
    
    title: str | None = None
    comment: str | None = None
    location: str | None = None
    author: str | None = None


class PhotoAttributesResponse(PhotoMetadata):
    """Full photo attributes response (includes tags)."""
    
    photo_id: int
    display_name: str
    created_at: datetime
    updated_at: datetime
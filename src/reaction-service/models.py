#!/usr/bin/env python3
"""Data models for reaction service."""

from typing import Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import Document


class ReactionCreate(BaseModel):
    """Model for creating a new reaction."""
    
    reaction: Annotated[
        str,
        Field(
            description="Emoji reaction (e.g., 'coeur', 'pouce', 'love')",
            examples=["coeur", "pouce", "love"]
        )
    ]
    reactor_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=16,
            description="Display name of the reactor (photographer)",
            examples=["hcartier"]
        )
    ]


class ReactionUpdate(BaseModel):
    """Model for updating an existing reaction."""
    
    reaction: Annotated[
        str,
        Field(
            description="New emoji reaction",
            examples=["fire", "wow"]
        )
    ]


class Reaction(Document):
    """MongoDB document representing a reaction."""
    
    # Photo identification - SANS Annotated pour Beanie
    display_name: str = Field(min_length=1, max_length=16, description="Display name of photo owner")
    photo_id: int = Field(ge=0, description="Photo ID")
    
    # Reactor identification
    reactor_name: str = Field(min_length=1, max_length=16, description="Display name of reactor")
    
    # Reaction data
    reaction: str = Field(description="Emoji reaction")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reactions"  # MongoDB collection name
        indexes = [
            "display_name",
            "photo_id",
            "reactor_name",
            [("display_name", 1), ("photo_id", 1)],  # Compound index for photo queries
            [("display_name", 1), ("photo_id", 1), ("reactor_name", 1)],  # Unique reaction
        ]


class ReactionResponse(BaseModel):
    """Response model for a single reaction."""
    
    display_name: str
    photo_id: int
    reactor_name: str
    reaction: str
    created_at: datetime
    updated_at: datetime


class PhotoReactionsResponse(BaseModel):
    """Response model for all reactions on a photo."""
    
    display_name: str
    photo_id: int
    total_reactions: int
    reactions: list[ReactionResponse]


class PhotographerReactionsResponse(BaseModel):
    """Response model for all reactions by a photographer."""
    
    reactor_name: str
    total_reactions: int
    reactions: list[ReactionResponse]
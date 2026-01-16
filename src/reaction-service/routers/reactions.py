#!/usr/bin/env python3
"""Reaction route handlers."""
import logging
from typing import Annotated
import asyncio

from datetime import datetime
from fastapi import APIRouter, Path, Body, status, Response
from models import (
    Reaction,
    ReactionCreate,
    ReactionUpdate,
    ReactionResponse,
    PhotoReactionsResponse,
    PhotographerReactionsResponse
)


from config import settings
from clients import PhotographerClient, PhotoClient,photo_of_day_client
from exceptions import (
    ReactionNotFoundError,
    ReactionAlreadyExistsError,
    InvalidReactionError,
    
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/reactions", tags=["reactions"])

# Type aliases for common path parameters
DisplayNamePath = Annotated[str, Path(min_length=1, max_length=16, description="Photographer display name")]
PhotoIdPath = Annotated[int, Path(ge=0, description="Photo ID")]
ReactorNamePath = Annotated[str, Path(min_length=1, max_length=16, description="Reactor display name")]
@router.post(
    "/{display_name}/{photo_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add a reaction to a photo",
    description="""
Add a new reaction (emoji) to a photo.

The reaction will be associated with the reactor's photographer profile.
Each reactor can only have one reaction per photo - use PUT to update.
    """,
    response_model=ReactionResponse,
    responses={
        201: {"description": "Reaction added successfully"},
        404: {"description": "Photo or reactor not found"},
        409: {"description": "Reaction already exists"},
        400: {"description": "Invalid reaction emoji"}
    }
)
async def add_reaction(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath,
    reaction_data: Annotated[ReactionCreate, Body(...)],
    response: Response
) -> ReactionResponse:
    """Add a new reaction to a photo."""
    logger.info(f"Adding reaction by '{reaction_data.reactor_name}' to photo {photo_id} of '{display_name}'")

    # Step 1: Validate reaction emoji
    if reaction_data.reaction not in settings.allowed_reactions:
        raise InvalidReactionError(reaction_data.reaction, settings.allowed_reactions)

    # Step 2: Verify photo exists
    await PhotoClient.check_photo_exists(display_name, photo_id)

    # Step 3: Verify reactor exists
    #await PhotographerClient.check_photographer_exists(reaction_data.reactor_name)

    # Step 4: Check if reaction already exists
    existing_reaction = await Reaction.find_one(
        Reaction.display_name == display_name,
        Reaction.photo_id == photo_id,
        Reaction.reactor_name == reaction_data.reactor_name
    )

    if existing_reaction:
        raise ReactionAlreadyExistsError(display_name, photo_id, reaction_data.reactor_name)

    # Step 5: Create and save reaction
    reaction = Reaction(
        display_name=display_name,
        photo_id=photo_id,
        reactor_name=reaction_data.reactor_name,
        reaction=reaction_data.reaction,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await reaction.save()
    
  
        
    await photo_of_day_client.increment_reaction(
        display_name=display_name,
        photo_id=photo_id,
        reaction_type=reaction_data.reaction)
    # Step 6: Set Location header
    response.headers["Location"] = f"/reactions/{display_name}/{photo_id}/{reaction_data.reactor_name}"

    logger.info(f"Reaction added successfully")

    return ReactionResponse(
        display_name=reaction.display_name,
        photo_id=reaction.photo_id,
        reactor_name=reaction.reactor_name,
        reaction=reaction.reaction,
        created_at=reaction.created_at,
        updated_at=reaction.updated_at
    )
@router.get(
    "/{display_name}/{photo_id}",
    status_code=status.HTTP_200_OK,
    summary="Get all reactions for a photo",
    description="""
Retrieve all reactions (emojis) that have been added to a specific photo.

Returns a summary including total count and list of all reactions.
    """,
    response_model=PhotoReactionsResponse,
    responses={
        200: {"description": "Reactions retrieved successfully"},
        404: {"description": "Photo not found"}
    }
)
async def get_photo_reactions(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath
) -> PhotoReactionsResponse:
    """Get all reactions for a specific photo."""
    logger.info(f"Getting reactions for photo {photo_id} of '{display_name}'")

    # Step 1: Verify photo exists
    await PhotoClient.check_photo_exists(display_name, photo_id)

    # Step 2: Query all reactions for this photo
    reactions = await Reaction.find(
        Reaction.display_name == display_name,
        Reaction.photo_id == photo_id
    ).sort("created_at").to_list()

    # Step 3: Build response
    reaction_responses = [
        ReactionResponse(
            display_name=r.display_name,
            photo_id=r.photo_id,
            reactor_name=r.reactor_name,
            reaction=r.reaction,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in reactions
    ]

    logger.info(f"Found {len(reactions)} reactions")

    return PhotoReactionsResponse(
        display_name=display_name,
        photo_id=photo_id,
        total_reactions=len(reactions),
        reactions=reaction_responses
    )
@router.put(
    "/{display_name}/{photo_id}/{reactor_name}",
    status_code=status.HTTP_200_OK,
    summary="Update an existing reaction",
    description="""
Change the emoji of an existing reaction.

Only the reactor who created the reaction can update it.
    """,
    response_model=ReactionResponse,
    responses={
        200: {"description": "Reaction updated successfully"},
        404: {"description": "Photo or reaction not found"},
        400: {"description": "Invalid reaction emoji"}
    }
)
async def update_reaction(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath,
    reactor_name: ReactorNamePath,
    reaction_update: Annotated[ReactionUpdate, Body(...)]
) -> ReactionResponse:
    """Update an existing reaction."""
    logger.info(f"Updating reaction by '{reactor_name}' on photo {photo_id} of '{display_name}'")

    # Step 1: Validate new reaction emoji
    if reaction_update.reaction not in settings.allowed_reactions:
        raise InvalidReactionError(reaction_update.reaction, settings.allowed_reactions)

    # Step 2: Verify photo exists
    await PhotoClient.check_photo_exists(display_name, photo_id)

    # Step 3: Find existing reaction
    reaction = await Reaction.find_one(
        Reaction.display_name == display_name,
        Reaction.photo_id == photo_id,
        Reaction.reactor_name == reactor_name
    )

    if not reaction:
        raise ReactionNotFoundError(display_name, photo_id, reactor_name)

    # Step 4: Update reaction
    reaction.reaction = reaction_update.reaction
    reaction.updated_at = datetime.utcnow()
    await reaction.save()
    await photo_of_day_client.update_reaction(
        display_name=display_name,
        photo_id=photo_id,
        old_reaction_type=reaction.reaction,
        new_reaction_type=reaction_update.reaction
    )
    logger.info(f"Reaction updated to '{reaction_update.reaction}'")

    return ReactionResponse(
        display_name=reaction.display_name,
        photo_id=reaction.photo_id,
        reactor_name=reaction.reactor_name,
        reaction=reaction.reaction,
        created_at=reaction.created_at,
        updated_at=reaction.updated_at
    )
@router.delete(
    "/{display_name}/{photo_id}/{reactor_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reaction",
    description="""
Remove a reaction from a photo.

Only the reactor who created the reaction can delete it.
    """,
    responses={
        204: {"description": "Reaction deleted successfully"},
        404: {"description": "Photo or reaction not found"}
    }
)
async def delete_reaction(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath,
    reactor_name: ReactorNamePath
) -> None:
    """Delete an existing reaction."""
    logger.info(f"Deleting reaction by '{reactor_name}' from photo {photo_id} of '{display_name}'")

    # Step 1: Verify photo exists
    await PhotoClient.check_photo_exists(display_name, photo_id)

    # Step 2: Find existing reaction
    reaction = await Reaction.find_one(
        Reaction.display_name == display_name,
        Reaction.photo_id == photo_id,
        Reaction.reactor_name == reactor_name
    )

    if not reaction:
        raise ReactionNotFoundError(display_name, photo_id, reactor_name)

    # Step 3: Delete reaction
    await reaction.delete()
    await photo_of_day_client.decrement_reaction(
        display_name=display_name,
        photo_id=photo_id,
        reaction_type=reaction.reaction
    )


    logger.info(f"Reaction deleted successfully")
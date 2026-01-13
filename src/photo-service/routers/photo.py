#!/usr/bin/env python3
"""Router for individual photo endpoints."""

from typing import Annotated
import logging

from fastapi import APIRouter, Path, Body, status
from fastapi.responses import Response
import pymongo

from models import Photo, PhotoAttributesUpdate, PhotoAttributesResponse
from exceptions import PhotoNotFoundError, DatabaseUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photo", tags=["photo"])


# Path parameters
DisplayNamePath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=16,
        description="Photographer's display name"
    )
]

PhotoIdPath = Annotated[
    int,
    Path(
        ge=0,
        description="Photo ID"
    )
]


@router.get(
    "/{display_name}/{photo_id}",
    status_code=status.HTTP_200_OK,
    summary="Get photo image",
    description="""
Retrieve the actual image file (JPEG).

Returns the image as binary data with appropriate content-type header.
""",
    responses={
        200: {
            "content": {"image/jpeg": {}},
            "description": "JPEG image"
        }
    }
)
async def get_photo_image(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath
):
    """Get photo image data."""
    try:
        photo = await Photo.find_one(
            Photo.display_name == display_name,
            Photo.photo_id == photo_id
        )
        
        if photo is None:
            raise PhotoNotFoundError(display_name, photo_id)
        
        return Response(
            content=photo.image_data,
            media_type="image/jpeg"
        )
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.get(
    "/{display_name}/{photo_id}/attributes",
    status_code=status.HTTP_200_OK,
    summary="Get photo attributes",
    description="""
Get photo metadata (title, comment, location, author, tags).

Does not include the image binary data.
""",
)
async def get_photo_attributes(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath
) -> PhotoAttributesResponse:
    """Get photo metadata."""
    try:
        photo = await Photo.find_one(
            Photo.display_name == display_name,
            Photo.photo_id == photo_id
        )
        
        if photo is None:
            raise PhotoNotFoundError(display_name, photo_id)
        
        return PhotoAttributesResponse(
            photo_id=photo.photo_id,
            display_name=photo.display_name,
            title=photo.title,
            comment=photo.comment,
            location=photo.location,
            author=photo.author,
            tags=photo.tags,
            created_at=photo.created_at,
            updated_at=photo.updated_at
        )
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.put(
    "/{display_name}/{photo_id}/attributes",
    status_code=status.HTTP_200_OK,
    summary="Update photo attributes",
    description="""
Update photo metadata (title, comment, location, author).

Tags cannot be updated (they are auto-generated).
Only provided fields will be updated.
""",
)
async def update_photo_attributes(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath,
    attributes: Annotated[PhotoAttributesUpdate, Body()]
) -> dict[str, str]:
    """Update photo metadata."""
    try:
        photo = await Photo.find_one(
            Photo.display_name == display_name,
            Photo.photo_id == photo_id
        )
        
        if photo is None:
            raise PhotoNotFoundError(display_name, photo_id)
        
        # Update only provided fields
        update_data = attributes.model_dump(exclude_none=True)
        
        if update_data:
            await photo.set(update_data)
            logger.info(f"Updated photo {photo_id} for {display_name}: {update_data.keys()}")
        
        return {"message": "Photo attributes updated successfully"}
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.delete(
    "/{display_name}/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete photo",
    description="""
Delete a photo and its metadata.

This operation cannot be undone.
""",
)
async def delete_photo(
    display_name: DisplayNamePath,
    photo_id: PhotoIdPath
) -> None:
    """Delete a photo."""
    try:
        photo = await Photo.find_one(
            Photo.display_name == display_name,
            Photo.photo_id == photo_id
        )
        
        if photo is None:
            raise PhotoNotFoundError(display_name, photo_id)
        
        await photo.delete()
        
        logger.info(f"Deleted photo {photo_id} for {display_name}")
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()

#!/usr/bin/env python3
"""Router for gallery endpoints (upload, list photos)."""

from typing import Annotated
import logging
from io import BytesIO

from fastapi import APIRouter, File, UploadFile, Response, Query, Path, status
from PIL import Image
import pymongo

from models import PhotosResponse, PhotoDigest, Photo, PhotoIdCounter
from config import settings
from exceptions import (
    InvalidImageError,
    ImageTooLargeError,
    DatabaseUnavailableError,
)
from clients import PhotographerClient, tags_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gallery", tags=["gallery"])


# Path parameter
DisplayNamePath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=16,
        description="Photographer's display name",
        examples=["rdoisneau"]
    )
]


async def allocate_photo_id(display_name: str) -> int:
    """Allocate next photo ID for a photographer."""
    counter = await PhotoIdCounter.find_one(
        PhotoIdCounter.display_name == display_name
    )
    
    if counter is None:
        # First photo for this photographer
        counter = PhotoIdCounter(display_name=display_name, next_photo_id=1)
        await counter.save()
        return 0
    else:
        photo_id = counter.next_photo_id
        counter.next_photo_id += 1
        await counter.save()
        return photo_id


async def validate_and_process_image(file: UploadFile) -> tuple[bytes, str]:
    """
    Validate and process uploaded image.
    
    Returns:
        (image_data, content_type)
    """
    # Check content type
    if file.content_type not in settings.allowed_image_types:
        raise InvalidImageError(
            f"Invalid image type. Allowed: {', '.join(settings.allowed_image_types)}"
        )
    
    # Read image data
    image_data = await file.read()
    
    # Check size
    if len(image_data) > settings.max_image_size_bytes:
        raise ImageTooLargeError(settings.max_image_size_mb)
    
    # Validate it's a valid image
    try:
        img = Image.open(BytesIO(image_data))
        img.verify()
    except Exception as e:
        raise InvalidImageError(f"Corrupted or invalid image: {str(e)}")
    
    return image_data, file.content_type or "image/jpeg"


@router.post(
    "/{display_name}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo",
    description="""
Upload a photo to a photographer's gallery.

The photo will be automatically tagged using the tags service.
Returns a Location header pointing to the uploaded photo.
""",
)
async def upload_photo(
    response: Response,
    display_name: DisplayNamePath,
    file: Annotated[UploadFile, File(description="JPEG or PNG image")]
):
    """Upload a new photo."""
    try:
        # 1. Check photographer exists
        await PhotographerClient.check_photographer_exists(display_name)
        
        # 2. Validate and process image
        image_data, content_type = await validate_and_process_image(file)
        
        # 3. Get tags from tags service
        tags = await tags_client.get_tags(image_data)
        logger.info(f"Received tags: {tags}")
        
        # 4. Allocate photo ID
        photo_id = await allocate_photo_id(display_name)
        
        # 5. Save photo to MongoDB
        photo = Photo(
            display_name=display_name,
            photo_id=photo_id,
            image_data=image_data,
            tags=tags
        )
        await photo.save()
        
        # 6. Set Location header
        response.headers["Location"] = f"/photo/{display_name}/{photo_id}"
        
        logger.info(f"Photo {photo_id} uploaded for {display_name}")
        
        return {"message": "Photo uploaded successfully", "photo_id": photo_id}
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.get(
    "/{display_name}",
    status_code=status.HTTP_200_OK,
    summary="List photos",
    description="""
Get a paginated list of photos for a photographer.

Returns photo IDs and links. Use the links to retrieve full photos.
""",
)
async def list_photos(
    display_name: DisplayNamePath,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PhotosResponse:
    """List photos for a photographer."""
    try:
        # Check photographer exists
        await PhotographerClient.check_photographer_exists(display_name)
        
        # Get total count
        total_count = await Photo.find(
            Photo.display_name == display_name
        ).count()
        
        if total_count == 0:
            return PhotosResponse(
                items=[],
                has_more=False,
                total_count=0
            )
        
        # Fetch photos with pagination
        photos = await Photo.find(
            Photo.display_name == display_name
        ).sort("photo_id").skip(offset).limit(limit + 1).to_list()
        
        # Check if there are more
        has_more = len(photos) > limit
        if has_more:
            photos = photos[:limit]
        
        # Build response
        items = [
            PhotoDigest(
                photo_id=photo.photo_id,
                link=f"/photo/{display_name}/{photo.photo_id}"
            )
            for photo in photos
        ]
        
        return PhotosResponse(
            items=items,
            has_more=has_more,
            total_count=total_count
        )
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()

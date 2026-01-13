#!/usr/bin/env python3
"""Router for individual photographer endpoints."""

from typing import Annotated
import logging

from fastapi import APIRouter, Path, Body, status ,Response
import pymongo 


from models import Photographer, PhotographerDesc
from exceptions import PhotographerNotFoundError, DatabaseUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photographers", tags=["photographers"])


# Path parameter annotation
DisplayNamePath = Annotated[
    str,
    Path(
        min_length=1,
        max_length=16,
        description="The display name of the photographer",
        examples=["rdoisneau"]
    )
]


@router.get(
    "/{display_name}",
    status_code=status.HTTP_200_OK,
    summary="Get photographer details",
    description="""
Retrieve the complete details of a photographer by their display name.

Returns a JSON object with all photographer attributes:
- `display_name`: The unique identifier
- `first_name`: First name
- `last_name`: Last name
- `interests`: List of photography interests

Returns 404 if the photographer does not exist.
""",
)
async def get_photographer(display_name: DisplayNamePath) -> PhotographerDesc:
    """Get photographer by display name."""
    try:
        photographer = await Photographer.find_one(
            Photographer.display_name == display_name
        )
        
        if photographer is None:
            raise PhotographerNotFoundError(display_name)
        
        return PhotographerDesc(**photographer.model_dump())
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.put(
    "/{display_name}",
    status_code=status.HTTP_200_OK,
    summary="Update photographer",
    description="""
Update an existing photographer with new attributes.

In accordance with PUT semantics, all attributes must be provided.
They will completely replace the existing attributes.

**Important**: The `display_name` in the path must match the `display_name`
in the request body. This prevents accidental renaming.

Returns:
- 200: Successfully updated
- 404: Photographer not found
- 422: Display names don't match
""",
)
async def update_photographer(
    display_name: DisplayNamePath,
    photographer: Annotated[PhotographerDesc, Body()]
) -> dict[str, str]:
    """Update photographer attributes."""
    try:
        # Validate display_name consistency
        if display_name != photographer.display_name:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Path parameter and body display_name must be identical"
            )
        
        # Find existing photographer
        found = await Photographer.find_one(
            Photographer.display_name == display_name
        )
        
        if found is None:
            raise PhotographerNotFoundError(display_name)
        
        # Update all fields
        await found.set(photographer.model_dump())
        
        logger.info(f"Updated photographer: {display_name}")
        return {"message": "Photographer updated successfully"}
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()

@router.delete(
    "/{display_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete photographer",
    description="""
Delete a photographer by their display name.

This operation is idempotent at the REST level but returns different status codes:
- First deletion: 204 No Content (success)
- Subsequent deletions: 404 Not Found

Returns:
- 204: Successfully deleted (no response body)
- 404: Photographer does not exist
""",
)
async def delete_photographer(display_name: DisplayNamePath) -> Response:
    """Delete photographer by display name."""
    try:
        # Find existing photographer
        photographer = await Photographer.find_one(
            Photographer.display_name == display_name
        )
        
        if photographer is None:
            raise PhotographerNotFoundError(display_name)
        
        # Delete the photographer
        await photographer.delete()
        
        logger.info(f"Deleted photographer: {display_name}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()

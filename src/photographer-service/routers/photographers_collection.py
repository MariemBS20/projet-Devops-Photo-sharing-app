#!/usr/bin/env python3
"""Router for photographers collection endpoints."""

from typing import Annotated
import logging

from fastapi import APIRouter, Response, Query, status
import pymongo

from models import Photographer, PhotographerDesc, PhotographersResponse, PhotographerDigest
from exceptions import PhotographerAlreadyExistsError, DatabaseUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photographers", tags=["photographers"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Photographer",
    description="""
Create a new photographer with the provided attributes.

The photographer's `display_name` must be unique. If a photographer with the same
`display_name` already exists, a 409 Conflict error will be returned.

Returns a 201 Created status with a Location header pointing to the new resource.
""",
)
async def create_photographer(
    response: Response,
    photographer_desc: PhotographerDesc
) -> dict[str, str]:
    """Create a new photographer."""
    try:
        # Check if photographer already exists
        existing = await Photographer.find_one(
            Photographer.display_name == photographer_desc.display_name
        )
        
        if existing is not None:
            raise PhotographerAlreadyExistsError(photographer_desc.display_name)
        
        # Create new photographer
        photographer = Photographer(**photographer_desc.model_dump())
        await photographer.insert()
        
        # Set Location header
        response.headers["Location"] = f"/photographers/{photographer_desc.display_name}"
        
        logger.info(f"Created photographer: {photographer_desc.display_name}")
        return {"message": "Photographer created successfully"}
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.head(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get photographer count",
    description="""
Retrieve the total count of photographers.

The count is returned in the `X-Total-Count` header of the response.
This is useful for pagination calculations without fetching the actual data.
""",
)
async def head_photographers(response: Response) -> None:
    """Get total count of photographers."""
    try:
        count = await Photographer.count()
        response.headers["X-Total-Count"] = str(count)
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List photographers",
    description="""
Retrieve a paginated list of photographers.

Use `offset` and `limit` query parameters to control pagination:
- `offset`: Number of items to skip (default: 0)
- `limit`: Maximum number of items to return (default: 10, max: 100)

The response includes:
- `items`: Array of photographer digests with `display_name` and `link`
- `has_more`: Boolean indicating if more items are available
- `total_count`: Total number of photographers

The total count is also available in the `X-Total-Count` response header.
""",
)
async def get_photographers(
    response: Response,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PhotographersResponse:
    """List photographers with pagination."""
    try:
        # Get total count
        total_count = await Photographer.count()
        response.headers["X-Total-Count"] = str(total_count)
        
        # Fetch one extra item to determine if there are more
        photographers = await Photographer.find() \
            .sort("_id") \
            .skip(offset) \
            .limit(limit + 1) \
            .to_list()
        
        # Check if there are more items
        has_more = len(photographers) > limit
        
        # Trim to requested limit
        if has_more:
            photographers = photographers[:limit]
        
        # Build response
        items = [
            PhotographerDigest(
                display_name=p.display_name,
                link=f"/photographers/{p.display_name}"
            )
            for p in photographers
        ]
        
        return PhotographersResponse(
            items=items,
            has_more=has_more,
            total_count=total_count
        )
        
    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()

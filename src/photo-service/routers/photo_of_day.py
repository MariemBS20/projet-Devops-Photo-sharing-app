#!/usr/bin/env python3
"""Endpoint REST pour la photo du jour."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
import pymongo

from fastapi import APIRouter, Query, status
from fastapi.responses import Response, JSONResponse

from models import Photo
from exceptions import PhotoNotFoundError, DatabaseUnavailableError
from clients import PhotoOfDayClient
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photo-of-day", tags=["photo-of-day"])

# Initialiser le client gRPC
photo_of_day_client = PhotoOfDayClient(
    grpc_host=settings.photo_of_day_grpc_host,
    grpc_port=settings.photo_of_day_grpc_port
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get photo of the day",
    description="Get the most reacted photo in a time period.",
)
async def get_photo_of_day(
    days: Annotated[int, Query(ge=1, le=365, description="Number of days to look back")] = 1,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
    format: Annotated[str, Query(pattern="^(image|json)$")] = "image"
):
    """Get the most reacted photo in a time period."""
    try:
        # 1️⃣ Déterminer la période
        if start_date and end_date:
            try:
                # Parser les dates EN SUPPOSANT QU'ELLES SONT EN HEURE LOCALE
                start_dt = datetime.fromisoformat(
                    start_date.replace('Z', '') if 'T' in start_date else f"{start_date}T00:00:00"
                )
                end_dt = datetime.fromisoformat(
                    end_date.replace('Z', '') if 'T' in end_date else f"{end_date}T23:59:59"
                )
                
                # ✅ Si pas de timezone, convertir l'heure locale en UTC
                if start_dt.tzinfo is None:
                    start_dt = start_dt.astimezone(timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.astimezone(timezone.utc)
                
                if start_dt >= end_dt:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": "start_date must be before end_date"}
                    )
                period_desc = f"from {start_date} to {end_date}"
            except ValueError as e:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": f"Invalid date format: {e}"}
                )
        else:
            # ✅ Utiliser l'heure locale actuelle, puis convertir en UTC
            end_dt = datetime.now().astimezone(timezone.utc)
            start_dt = (datetime.now() - timedelta(days=days)).astimezone(timezone.utc)
            period_desc = f"last {days} day(s)"

        # ✅ Convertir en timestamps UTC
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())

        logger.info(f"📸 Getting photo of day for {period_desc}")
        logger.info(f"   Timestamps UTC: {start_ts} -> {end_ts}")
        logger.info(f"   Dates UTC: {start_dt.isoformat()} -> {end_dt.isoformat()}")

        # 2️⃣ Appeler le service gRPC
        grpc_response = await photo_of_day_client.get_photo_of_day(start_ts, end_ts)

        if not grpc_response:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "found": False,
                    "message": f"No photo found for {period_desc}"
                }
            )

        # 3️⃣ Récupérer la photo dans la DB
        photo = await Photo.find_one(
            Photo.display_name == grpc_response.display_name,
            Photo.photo_id == grpc_response.photo_id
        )
        if not photo:
            logger.error(f"❌ Photo not found in DB: {grpc_response.display_name}/{grpc_response.photo_id}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Photo found in stats but not in database"}
            )

        # 4️⃣ Préparer les métadonnées (AVEC CONVERSION EN HEURE LOCALE POUR L'AFFICHAGE)
        # Convertir created_at en heure locale pour l'affichage
        created_at_local = photo.created_at.astimezone() if photo.created_at.tzinfo else photo.created_at
        
        metadata = {
            "display_name": photo.display_name,
            "photo_id": photo.photo_id,
            "title": photo.title,
            "comment": photo.comment,
            "location": photo.location,
            "author": photo.author,
            "tags": photo.tags,
            "created_at": created_at_local.isoformat(),  # ✅ Heure locale
            "photo_url": grpc_response.photo_url,
            "reactions": {
                "total": grpc_response.total_reactions,
                "breakdown": dict(grpc_response.reaction_breakdown)
            }
        }

        # 5️⃣ Retourner la réponse
        if format == "json":
            return JSONResponse(
                content={
                    "found": True,
                    "photo": metadata,
                    "period": {
                        "start": start_dt.astimezone().isoformat(),  # ✅ Heure locale pour affichage
                        "end": end_dt.astimezone().isoformat(),      # ✅ Heure locale pour affichage
                        "description": period_desc
                    }
                }
            )
        else:
            return Response(
                content=photo.image_data,
                media_type="image/jpeg",
                headers={
                    "X-Photo-Display-Name": photo.display_name,
                    "X-Photo-ID": str(photo.photo_id),
                    "X-Photo-Title": photo.title,
                    "X-Photo-Author": photo.author or "Unknown",
                    "X-Photo-Location": photo.location or "Unknown",
                    "X-Total-Reactions": str(grpc_response.total_reactions),
                    "X-Reaction-Breakdown": str(dict(grpc_response.reaction_breakdown)),
                    "X-Period-Start": start_dt.astimezone().isoformat(),  # ✅ Heure locale
                    "X-Period-End": end_dt.astimezone().isoformat(),      # ✅ Heure locale
                }
            )

    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()
    except Exception as e:
        logger.error(f"❌ Error getting photo of day: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get photo of day statistics",
    description="Get statistics about the most reacted photo without downloading the image."
)
async def get_photo_of_day_stats(
    days: Annotated[int, Query(ge=1, le=365)] = 1,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None
):
    """Get stats without downloading the image."""
    try:
        # Reuse the same period calculation logic
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            # ✅ Si pas de timezone, convertir l'heure locale en UTC
            if start_dt.tzinfo is None:
                start_dt = start_dt.astimezone(timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.astimezone(timezone.utc)
        else:
            # ✅ Utiliser l'heure locale, puis convertir en UTC
            end_dt = datetime.now().astimezone(timezone.utc)
            start_dt = (datetime.now() - timedelta(days=days)).astimezone(timezone.utc)

        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())

        grpc_response = await photo_of_day_client.get_photo_of_day(start_ts, end_ts)
        if not grpc_response:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"found": False, "message": "No photo found"}
            )

        photo = await Photo.find_one(
            Photo.display_name == grpc_response.display_name,
            Photo.photo_id == grpc_response.photo_id
        )
        if not photo:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Photo found in stats but not in database"}
            )

        # ✅ Convertir created_at en heure locale pour l'affichage
        created_at_local = photo.created_at.astimezone() if photo.created_at.tzinfo else photo.created_at

        return {
            "found": True,
            "photo": {
                "display_name": photo.display_name,
                "photo_id": photo.photo_id,
                "title": photo.title,
                "comment": photo.comment,
                "location": photo.location,
                "author": photo.author,
                "tags": photo.tags,
                "created_at": created_at_local.isoformat(),  # ✅ Heure locale
                "photo_url": grpc_response.photo_url
            },
            "reactions": {
                "total": grpc_response.total_reactions,
                "breakdown": dict(grpc_response.reaction_breakdown)
            },
            "period": {
                "start": start_dt.astimezone().isoformat(),  # ✅ Heure locale
                "end": end_dt.astimezone().isoformat()       # ✅ Heure locale
            }
        }

    except pymongo.errors.ServerSelectionTimeoutError:
        raise DatabaseUnavailableError()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )
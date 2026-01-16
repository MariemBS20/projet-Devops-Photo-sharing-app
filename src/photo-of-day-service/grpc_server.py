#!/usr/bin/env python3
"""gRPC server for Photo of Day service."""

import asyncio
import logging
from datetime import datetime
import grpc
from motor.motor_asyncio import AsyncIOMotorClient

import photo_of_day_pb2
import photo_of_day_pb2_grpc
from config import settings
from clients import PhotoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PhotoOfDayServicer(photo_of_day_pb2_grpc.PhotoOfDayServiceServicer):
    """Implementation of Photo of Day gRPC service."""

    def __init__(self):
        """Initialize servicer with database connection."""
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.database_name]
        self.collection = self.db.photo_stats
        self.photo_client = PhotoClient()
        logger.info("PhotoOfDayServicer initialized")

   
    async def IncrementReaction(self, request, context):
        display_name = request.display_name
        photo_id = request.photo_id
        reaction_type = request.reaction_type

        logger.info(f"Increment reaction: {display_name}/{photo_id} - {reaction_type}")

        # Récupérer la photo depuis la DB
        photo = await self.collection.find_one({"display_name": display_name, "photo_id": photo_id})
        if not photo:
            return photo_of_day_pb2.IncrementReactionResponse(
                success=False,
                message="Photo not found",
                total_reactions=0
            )

        # Incrémenter le compteur pour la réaction
        reactions = photo.get("reaction_breakdown", {})  # {"coeur": 3, "fire": 1, ...}
        reactions[reaction_type] = reactions.get(reaction_type, 0) + 1

        # Mettre à jour la DB
        await self.collection.update_one(
            {"display_name": display_name, "photo_id": photo_id},
            {
                "$set": {"reaction_breakdown": reactions},
                "$setOnInsert": {"first_reaction_date": datetime.utcnow().isoformat()},
                "$currentDate": {"last_reaction_date": True}  # met la date actuelle
            },
            upsert=True
        )

        # Calculer le total des réactions
        total_reactions = sum(reactions.values())
        

        logger.info(f"Reaction incremented successfully: total_reactions={total_reactions}")

        # Retourner la réponse gRPC
        return photo_of_day_pb2.IncrementReactionResponse(
            success=True,
            message="Reaction incremented",
            total_reactions=total_reactions
        )

    async def GetPhotoOfDay(
        self, 
        request: photo_of_day_pb2.GetPhotoOfDayRequest, 
        context: grpc.aio.ServicerContext
    ) -> photo_of_day_pb2.GetPhotoOfDayResponse:
        """Return the most reacted photo of the day."""
        try:
            # Aggregate reactions
            photo = await self.collection.find_one(
                {"date": {"$gte": request.start_date, "$lte": request.end_date}},
                sort=[("total_reactions", -1)]
            )

            if not photo:
                return photo_of_day_pb2.GetPhotoOfDayResponse(found=False)

            photo_url = await self.photo_client.get_photo_url(
                photo["display_name"], photo["photo_id"]
            )

            return photo_of_day_pb2.GetPhotoOfDayResponse(
                found=True,
                display_name=photo["display_name"],
                photo_id=photo["photo_id"],
                total_reactions=photo["total_reactions"],
                reaction_breakdown=photo.get("reaction_breakdown", {}),
                photo_url=photo_url
            )

        except Exception as e:
            logger.error(f"Error in GetPhotoOfDay: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return photo_of_day_pb2.GetPhotoOfDayResponse(found=False)

    async def GetPhotoStats(
        self, 
        request: photo_of_day_pb2.GetPhotoStatsRequest, 
        context: grpc.aio.ServicerContext
    ) -> photo_of_day_pb2.GetPhotoStatsResponse:
        """Return statistics for a specific photo."""
        try:
            doc = await self.collection.find_one({
                "display_name": request.display_name,
                "photo_id": request.photo_id
            })

            if not doc:
                return photo_of_day_pb2.GetPhotoStatsResponse(found=False)

            return photo_of_day_pb2.GetPhotoStatsResponse(
                found=True,
                display_name=doc["display_name"],
                photo_id=doc["photo_id"],
                total_reactions=doc.get("total_reactions", 0),
                reaction_breakdown=doc.get("reaction_breakdown", {}),
                first_reaction_date=doc.get("first_reaction_date", ""),
                last_reaction_date=doc.get("last_reaction_date", "")
            )

        except Exception as e:
            logger.error(f"Error in GetPhotoStats: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return photo_of_day_pb2.GetPhotoStatsResponse(found=False)


async def serve():
    """Start gRPC server."""
    server = grpc.aio.server()
    photo_of_day_pb2_grpc.add_PhotoOfDayServiceServicer_to_server(
        PhotoOfDayServicer(), server
    )
    
    listen_addr = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(listen_addr)
    
    logger.info(f"🚀 Starting gRPC server on {listen_addr}")
    await server.start()
    logger.info("✅ gRPC server started successfully")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())

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

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PhotoOfDayServicer(photo_of_day_pb2_grpc.PhotoOfDayServiceServicer):

    def __init__(self):
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.database_name]
        self.collection = self.db.photo_stats
        self.photo_client = PhotoClient()
        logger.info("PhotoOfDayServicer initialized")

    # ===================== 🔄 SYNCHRONISATION =====================
    async def sync_existing_reactions(self):
        logger.info("🔄 Synchronizing with reactions database...")

        reactions_client = AsyncIOMotorClient(settings.mongodb_url)
        reactions_db = reactions_client["reactions"]
        reactions_collection = reactions_db["reactions"]

        cursor = reactions_collection.find({})
        reactions = await cursor.to_list(length=None)

        photos = {}

        for r in reactions:
            key = (r["display_name"], r["photo_id"])
            photos.setdefault(key, []).append(r)

        for (display_name, photo_id), reactions in photos.items():
            breakdown = {}
            dates = []

            for r in reactions:
                breakdown[r["reaction"]] = breakdown.get(r["reaction"], 0) + 1
                dates.append(r["created_at"])

            await self.collection.update_one(
                {
                    "display_name": display_name,
                    "photo_id": photo_id
                },
                {
                    "$set": {
                        "reaction_breakdown": breakdown,
                        "total_reactions": sum(breakdown.values()),
                        "first_reaction_date": min(dates).isoformat(),
                        "last_reaction_date": max(dates).isoformat()
                    }
                },
                upsert=True
            )

            logger.info(
                f"✅ Synced {display_name}/{photo_id} → {breakdown}"
            )

        reactions_client.close()
        logger.info("✅ Synchronization finished")

    # ===================== ➕ INCREMENT =====================
    async def IncrementReaction(self, request, context):
        try:
            doc = await self.collection.find_one({
                "display_name": request.display_name,
                "photo_id": request.photo_id
            })

            breakdown = doc.get("reaction_breakdown", {}) if doc else {}
            breakdown[request.reaction_type] = breakdown.get(request.reaction_type, 0) + 1

            total = sum(breakdown.values())
            logger.info(
                    f"📥 IncrementReaction called → "
                    f"{request.display_name}/{request.photo_id} | "
                    f"reaction={request.reaction_type} | "
                    f"TOTAL={total}"
                )
            await self.collection.update_one(
                {
                    "display_name": request.display_name,
                    "photo_id": request.photo_id
                },
                {
                    "$set": {
                        "reaction_breakdown": breakdown,
                        "total_reactions": total,
                        "last_reaction_date": datetime.utcnow().isoformat()
                    },
                    "$setOnInsert": {
                        "first_reaction_date": datetime.utcnow().isoformat()
                    }
                },
                upsert=True
            )

            return photo_of_day_pb2.IncrementReactionResponse(
                success=True,
                message="Reaction incremented",
                total_reactions=total
            )

        except Exception as e:
            logger.error(e, exc_info=True)
            return photo_of_day_pb2.IncrementReactionResponse(
                success=False,
                message=str(e),
                total_reactions=0
            )

    # ===================== 📊 STATS =====================
    async def GetPhotoStats(self, request, context):
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
            total_reactions=doc["total_reactions"],
            reaction_breakdown=doc["reaction_breakdown"],
            first_reaction_date=doc["first_reaction_date"],
            last_reaction_date=doc["last_reaction_date"]
        )


# ===================== 🚀 SERVER =====================
async def serve():
    server = grpc.aio.server()

    servicer = PhotoOfDayServicer()
    photo_of_day_pb2_grpc.add_PhotoOfDayServiceServicer_to_server(
        servicer, server
    )

    # 🔥 SYNCHRONISATION AU DÉMARRAGE
    await servicer.sync_existing_reactions()

    listen_addr = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"🚀 gRPC server running on {listen_addr}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())

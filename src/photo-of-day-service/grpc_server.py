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

    async def sync_existing_reactions(self):
        """
        🔄 Synchroniser avec les réactions existantes du Reaction Service.
        À appeler au démarrage pour rattraper les réactions manquées.
        """
        try:
            logger.info("🔄 Starting synchronization with Reaction Service...")
            
            # Se connecter à la base reactions
            reactions_client = AsyncIOMotorClient(settings.mongodb_url.replace(
                settings.database_name, 
                "reactions"
            ))
            reactions_db = reactions_client["reactions"]
            reactions_collection = reactions_db["reactions"]
            
            # Récupérer toutes les réactions
            cursor = reactions_collection.find({})
            reactions_list = await cursor.to_list(length=None)
            
            logger.info(f"Found {len(reactions_list)} reactions to sync")
            
            # Grouper par photo
            photos_reactions = {}
            
            for reaction in reactions_list:
                key = (reaction["display_name"], reaction["photo_id"])
                
                if key not in photos_reactions:
                    photos_reactions[key] = {
                        "display_name": reaction["display_name"],
                        "photo_id": reaction["photo_id"],
                        "reactions": []
                    }
                
                photos_reactions[key]["reactions"].append({
                    "type": reaction["reaction"],
                    "reactor": reaction["reactor_name"],
                    "created_at": reaction["created_at"]
                })
            
            # Mettre à jour chaque photo
            sync_count = 0
            for (display_name, photo_id), data in photos_reactions.items():
                # Calculer le breakdown
                breakdown = {}
                for r in data["reactions"]:
                    reaction_type = r["type"]
                    breakdown[reaction_type] = breakdown.get(reaction_type, 0) + 1
                
                total = sum(breakdown.values())
                
                # Trouver les dates
                dates = [r["created_at"] for r in data["reactions"]]
                first_date = min(dates).isoformat() if dates else datetime.utcnow().isoformat()
                last_date = max(dates).isoformat() if dates else datetime.utcnow().isoformat()
                
                # Mettre à jour dans photo_stats
                await self.collection.update_one(
                    {
                        "display_name": display_name,
                        "photo_id": photo_id
                    },
                    {
                        "$set": {
                            "total_reactions": total,
                            "reaction_breakdown": breakdown,
                            "first_reaction_date": first_date,
                            "last_reaction_date": last_date
                        }
                    },
                    upsert=True
                )
                
                sync_count += 1
                logger.info(
                    f"✅ Synced {display_name}/{photo_id}: "
                    f"{total} reactions, breakdown: {breakdown}"
                )
            
            # ✨ NOUVEAU: Supprimer les photos qui n'ont plus de réactions
            existing_photos_in_stats = await self.collection.find(
                {}, 
                {"display_name": 1, "photo_id": 1}
            ).to_list(length=None)
            
            for photo_stat in existing_photos_in_stats:
                key = (photo_stat["display_name"], photo_stat["photo_id"])
                if key not in photos_reactions:
                    # Cette photo n'a plus de réactions, la supprimer
                    await self.collection.delete_one({
                        "display_name": photo_stat["display_name"],
                        "photo_id": photo_stat["photo_id"]
                    })
                    logger.info(
                        f"🗑️  Removed {photo_stat['display_name']}/{photo_stat['photo_id']}: "
                        f"no reactions found"
                    )
            
            logger.info(f"✅ Synchronization complete: {sync_count} photos updated")
            
            # Fermer la connexion
            reactions_client.close()
            
        except Exception as e:
            logger.error(f"❌ Error during synchronization: {e}", exc_info=True)

    async def recalculate_stats(self, display_name: str, photo_id: int):
        """
        🔄 Recalculer les stats d'une photo depuis la base reactions.
        Utilisé après toute modification (ajout, suppression, modification).
        
        Returns:
            int: Nombre total de réactions après recalcul
        """
        try:
            logger.info(f"🔄 Recalculating stats for {display_name}/{photo_id}")
            
            # Se connecter à la base reactions
            reactions_client = AsyncIOMotorClient(settings.mongodb_url.replace(
                settings.database_name, 
                "reactions"
            ))
            reactions_db = reactions_client["reactions"]
            reactions_collection = reactions_db["reactions"]
            
            # Récupérer toutes les réactions pour cette photo
            cursor = reactions_collection.find({
                "display_name": display_name,
                "photo_id": photo_id
            })
            reactions_list = await cursor.to_list(length=None)
            
            # Si aucune réaction, supprimer l'entrée dans photo_stats
            if not reactions_list:
                result = await self.collection.delete_one({
                    "display_name": display_name,
                    "photo_id": photo_id
                })
                if result.deleted_count > 0:
                    logger.info(f"🗑️  Deleted stats for {display_name}/{photo_id}: no reactions")
                reactions_client.close()
                return 0
            
            # Calculer le breakdown
            breakdown = {}
            for reaction in reactions_list:
                reaction_type = reaction["reaction"]
                breakdown[reaction_type] = breakdown.get(reaction_type, 0) + 1
            
            total = sum(breakdown.values())
            
            # Trouver les dates
            dates = [r["created_at"] for r in reactions_list]
            first_date = min(dates).isoformat() if dates else datetime.utcnow().isoformat()
            last_date = max(dates).isoformat() if dates else datetime.utcnow().isoformat()
            
            # Mettre à jour dans photo_stats
            await self.collection.update_one(
                {
                    "display_name": display_name,
                    "photo_id": photo_id
                },
                {
                    "$set": {
                        "total_reactions": total,
                        "reaction_breakdown": breakdown,
                        "first_reaction_date": first_date,
                        "last_reaction_date": last_date
                    }
                },
                upsert=True
            )
            
            logger.info(
                f"✅ Recalculated {display_name}/{photo_id}: "
                f"{total} reactions, breakdown: {breakdown}"
            )
            
            reactions_client.close()
            return total
            
        except Exception as e:
            logger.error(f"❌ Error recalculating stats: {e}", exc_info=True)
            return 0

    async def IncrementReaction(self, request, context):
        """
        Appelé quand une réaction est AJOUTÉE.
        Recalcule depuis la source de vérité (base reactions).
        """
        display_name = request.display_name
        photo_id = request.photo_id
        reaction_type = request.reaction_type

        logger.info(f"📥 IncrementReaction: {display_name}/{photo_id} - {reaction_type}")

        try:
            # ✅ Recalculer depuis la base reactions (source de vérité)
            total_reactions = await self.recalculate_stats(display_name, photo_id)

            logger.info(
                f"✅ Reaction added: {display_name}/{photo_id} - {reaction_type} "
                f"(new total: {total_reactions})"
            )

            return photo_of_day_pb2.IncrementReactionResponse(
                success=True,
                message="Reaction incremented successfully",
                total_reactions=total_reactions
            )

        except Exception as e:
            logger.error(f"❌ Error incrementing reaction: {e}", exc_info=True)
            return photo_of_day_pb2.IncrementReactionResponse(
                success=False,
                message=f"Error: {str(e)}",
                total_reactions=0
            )

    async def DecrementReaction(self, request, context):
        """
        Appelé quand une réaction est SUPPRIMÉE.
        Recalcule depuis la source de vérité (base reactions).
        """
        display_name = request.display_name
        photo_id = request.photo_id
        reaction_type = request.reaction_type

        logger.info(f"📤 DecrementReaction: {display_name}/{photo_id} - {reaction_type}")

        try:
            # ✅ Recalculer depuis la base reactions (source de vérité)
            total_reactions = await self.recalculate_stats(display_name, photo_id)

            logger.info(
                f"✅ Reaction removed: {display_name}/{photo_id} - {reaction_type} "
                f"(new total: {total_reactions})"
            )

            return photo_of_day_pb2.IncrementReactionResponse(
                success=True,
                message="Reaction decremented successfully",
                total_reactions=total_reactions
            )

        except Exception as e:
            logger.error(f"❌ Error decrementing reaction: {e}", exc_info=True)
            return photo_of_day_pb2.IncrementReactionResponse(
                success=False,
                message=f"Error: {str(e)}",
                total_reactions=0
            )

    async def UpdateReaction(self, request, context):
        """
        Appelé quand une réaction est MODIFIÉE.
        Recalcule depuis la source de vérité (base reactions).
        """
        display_name = request.display_name
        photo_id = request.photo_id
        old_reaction_type = request.old_reaction_type
        new_reaction_type = request.new_reaction_type

        logger.info(
            f"🔄 UpdateReaction: {display_name}/{photo_id} - "
            f"{old_reaction_type} → {new_reaction_type}"
        )

        try:
            # ✅ Recalculer depuis la base reactions (source de vérité)
            total_reactions = await self.recalculate_stats(display_name, photo_id)

            logger.info(
                f"✅ Reaction updated: {display_name}/{photo_id} "
                f"(total: {total_reactions})"
            )

            return photo_of_day_pb2.IncrementReactionResponse(
                success=True,
                message="Reaction updated successfully",
                total_reactions=total_reactions
            )

        except Exception as e:
            logger.error(f"❌ Error updating reaction: {e}", exc_info=True)
            return photo_of_day_pb2.IncrementReactionResponse(
                success=False,
                message=f"Error: {str(e)}",
                total_reactions=0
            )

    async def GetPhotoOfDay(
        self, 
        request: photo_of_day_pb2.GetPhotoOfDayRequest, 
        context: grpc.aio.ServicerContext
    ) -> photo_of_day_pb2.GetPhotoOfDayResponse:
        """Return the most reacted photo of the day."""
        try:
            # Convertir les timestamps en datetime
            start_date = datetime.fromtimestamp(request.start_timestamp)
            end_date = datetime.fromtimestamp(request.end_timestamp)

            logger.info(f"📊 GetPhotoOfDay: {start_date} to {end_date}")

            # Utiliser les timestamps ISO pour la requête
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()

            # Trouver la photo avec le plus de réactions dans la période
            photo = await self.collection.find_one(
                {
                    "last_reaction_date": {
                        "$gte": start_iso, 
                        "$lte": end_iso
                    },
                    "total_reactions": {"$gt": 0}
                },
                sort=[("total_reactions", -1)]
            )

            if not photo:
                logger.info("No photo found in the specified date range")
                return photo_of_day_pb2.GetPhotoOfDayResponse(found=False)

            # Récupérer l'URL de la photo
            photo_url = await self.photo_client.get_photo_url(
                photo["display_name"], 
                photo["photo_id"]
            )

            if not photo_url:
                photo_url = f"/photo/{photo['display_name']}/{photo['photo_id']}"

            logger.info(
                f"✅ Photo of day found: {photo['display_name']}/{photo['photo_id']} "
                f"with {photo['total_reactions']} reactions"
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
            logger.error(f"❌ Error in GetPhotoOfDay: {e}", exc_info=True)
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
            logger.info(f"📊 GetPhotoStats: {request.display_name}/{request.photo_id}")

            doc = await self.collection.find_one({
                "display_name": request.display_name,
                "photo_id": request.photo_id
            })

            if not doc:
                logger.info(f"No stats found for {request.display_name}/{request.photo_id}")
                return photo_of_day_pb2.GetPhotoStatsResponse(found=False)

            logger.info(f"✅ Stats found: {doc['total_reactions']} total reactions")

            # Convertir les dates ISO en timestamps
            first_timestamp = 0
            last_timestamp = 0

            if doc.get("first_reaction_date"):
                try:
                    first_dt = datetime.fromisoformat(doc["first_reaction_date"].replace('Z', ''))
                    first_timestamp = int(first_dt.timestamp())
                except:
                    pass

            if doc.get("last_reaction_date"):
                try:
                    last_dt = datetime.fromisoformat(doc["last_reaction_date"].replace('Z', ''))
                    last_timestamp = int(last_dt.timestamp())
                except:
                    pass

            return photo_of_day_pb2.GetPhotoStatsResponse(
                found=True,
                display_name=doc["display_name"],
                photo_id=doc["photo_id"],
                total_reactions=doc.get("total_reactions", 0),
                reaction_breakdown=doc.get("reaction_breakdown", {}),
                first_reaction_timestamp=first_timestamp,
                last_reaction_timestamp=last_timestamp
            )

        except Exception as e:
            logger.error(f"❌ Error in GetPhotoStats: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return photo_of_day_pb2.GetPhotoStatsResponse(found=False)


async def serve():
    """Start gRPC server."""
    # Créer le servicer
    servicer = PhotoOfDayServicer()
    
    # 🔄 Synchroniser les réactions existantes au démarrage
    await servicer.sync_existing_reactions()
    
    # Créer et configurer le serveur
    server = grpc.aio.server()
    photo_of_day_pb2_grpc.add_PhotoOfDayServiceServicer_to_server(servicer, server)
    
    listen_addr = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(listen_addr)
    
    logger.info(f"🚀 Starting gRPC server on {listen_addr}")
    await server.start()
    logger.info("✅ gRPC server started successfully")
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down gRPC server...")
        await server.stop(grace=5)


if __name__ == "__main__":
    asyncio.run(serve())
"""Acesso ao MongoDB."""

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from src.config import MongoSettings

RAW_COLLECTION = "carteira_raw"


def get_client(settings: MongoSettings) -> MongoClient:
    # Usuário e senha separados da URL: dispensa escapar caracteres especiais.
    return MongoClient(
        host=settings.host,
        port=settings.port,
        username=settings.user,
        password=settings.password,
        authSource="admin",
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )


def ensure_indexes(collection: Collection) -> None:
    collection.create_index("content_hash", unique=True, name="uniq_content_hash")
    collection.create_index(
        [("index", ASCENDING), ("collected_at", ASCENDING)], name="index_collected_at"
    )


def save_raw(collection: Collection, document: dict) -> bool:
    """Grava o documento; se o mesmo conteúdo já existir, só atualiza last_seen_at.

    Retorna True quando um documento novo foi inserido.
    """
    result = collection.update_one(
        {"content_hash": document["content_hash"]},
        {"$setOnInsert": document, "$set": {"last_seen_at": document["collected_at"]}},
        upsert=True,
    )
    return result.upserted_id is not None

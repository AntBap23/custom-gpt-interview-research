import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.settings import settings

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - optional until installed/configured
    Client = Any
    create_client = None


def utc_now() -> datetime:
    return datetime.now(UTC)


class StorageAdapter(ABC):
    @abstractmethod
    def list_items(self, collection: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_item(self, collection: str, item_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_item(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LocalJsonStorage(StorageAdapter):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _collection_path(self, collection: str) -> Path:
        path = self.root / f"{collection}.json"
        if not path.exists():
            path.write_text("[]", encoding="utf-8")
        return path

    def _read(self, collection: str) -> list[dict[str, Any]]:
        return json.loads(self._collection_path(collection).read_text(encoding="utf-8"))

    def _write(self, collection: str, items: list[dict[str, Any]]) -> None:
        self._collection_path(collection).write_text(json.dumps(items, indent=2), encoding="utf-8")

    def list_items(self, collection: str) -> list[dict[str, Any]]:
        return self._read(collection)

    def get_item(self, collection: str, item_id: str) -> dict[str, Any] | None:
        for item in self._read(collection):
            if item.get("id") == item_id:
                return item
        return None

    def upsert_item(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        items = self._read(collection)
        timestamp = utc_now().isoformat()
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())
            item["created_at"] = timestamp
        item["updated_at"] = timestamp

        replaced = False
        for index, existing in enumerate(items):
            if existing.get("id") == item["id"]:
                item["created_at"] = existing.get("created_at", timestamp)
                items[index] = item
                replaced = True
                break
        if not replaced:
            items.append(item)
        self._write(collection, items)
        return item


class SupabaseStorage(StorageAdapter):
    def __init__(self, url: str, key: str):
        if create_client is None:
            raise RuntimeError("Supabase client is not installed.")
        self.client: Client = create_client(url, key)

    def list_items(self, collection: str) -> list[dict[str, Any]]:
        response = self.client.table(collection).select("*").execute()
        return response.data or []

    def get_item(self, collection: str, item_id: str) -> dict[str, Any] | None:
        response = self.client.table(collection).select("*").eq("id", item_id).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    def upsert_item(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        timestamp = utc_now().isoformat()
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())
            item["created_at"] = timestamp
        item["updated_at"] = timestamp
        response = self.client.table(collection).upsert(item).execute()
        rows = response.data or []
        return rows[0] if rows else item


def get_storage() -> StorageAdapter:
    if settings.storage_backend.lower() == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "STORAGE_BACKEND is set to supabase, but SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing."
            )
        return SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    return LocalJsonStorage(settings.local_storage_root)

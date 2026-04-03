import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.errors import SupabaseOperationError
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
    def __init__(self, client: Client):
        if create_client is None:
            raise RuntimeError("Supabase client is not installed.")
        self.client: Client = client

    @staticmethod
    def _safe_execute(fn, operation: str):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - depends on network/runtime state
            raise SupabaseOperationError(f"Supabase {operation} failed.") from exc

    def list_items(self, collection: str) -> list[dict[str, Any]]:
        response = self._safe_execute(
            lambda: self.client.table(collection).select("*").execute(),
            f"list_items({collection})",
        )
        return response.data or []

    def get_item(self, collection: str, item_id: str) -> dict[str, Any] | None:
        response = self._safe_execute(
            lambda: self.client.table(collection).select("*").eq("id", item_id).limit(1).execute(),
            f"get_item({collection})",
        )
        rows = response.data or []
        return rows[0] if rows else None

    def upsert_item(self, collection: str, item: dict[str, Any]) -> dict[str, Any]:
        timestamp = utc_now().isoformat()
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())
            item["created_at"] = timestamp
        item["updated_at"] = timestamp
        response = self._safe_execute(
            lambda: self.client.table(collection).upsert(item).execute(),
            f"upsert_item({collection})",
        )
        rows = response.data or []
        return rows[0] if rows else item


_supabase_client_singleton: Client | None = None
_storage_singleton: StorageAdapter | None = None


def get_supabase_client() -> Client:
    global _supabase_client_singleton
    if _supabase_client_singleton is not None:
        return _supabase_client_singleton

    if create_client is None:
        raise RuntimeError("Supabase client is not installed.")
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase integration.")

    _supabase_client_singleton = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase_client_singleton


def get_storage() -> StorageAdapter:
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    if settings.storage_backend.lower() == "supabase":
        _storage_singleton = SupabaseStorage(get_supabase_client())
        return _storage_singleton

    _storage_singleton = LocalJsonStorage(settings.local_storage_root)
    return _storage_singleton

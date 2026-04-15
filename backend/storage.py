import json
import logging
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

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class StorageAdapter(ABC):
    @abstractmethod
    def list_items(self, collection: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_item(self, collection: str, item_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any] | None:
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

    def list_items(self, collection: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items = self._read(collection)
        if not filters:
            return items
        return [item for item in items if all(item.get(key) == value for key, value in filters.items())]

    def get_item(self, collection: str, item_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for item in self.list_items(collection, filters=filters):
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
            logger.exception("Supabase %s failed", operation)
            raise SupabaseOperationError(f"Supabase {operation} failed.") from exc

    def list_items(self, collection: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        def run_query():
            query = self.client.table(collection).select("*")
            for key, value in (filters or {}).items():
                query = query.eq(key, value)
            return query.execute()

        response = self._safe_execute(
            run_query,
            f"list_items({collection})",
        )
        return response.data or []

    def get_item(self, collection: str, item_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        def run_query():
            query = self.client.table(collection).select("*").eq("id", item_id)
            for key, value in (filters or {}).items():
                query = query.eq(key, value)
            return query.limit(1).execute()

        response = self._safe_execute(
            run_query,
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


_supabase_admin_client_singleton: Client | None = None
_supabase_auth_client_singleton: Client | None = None
_storage_singleton: StorageAdapter | None = None


def _require_supabase_client() -> None:
    if create_client is None:
        raise RuntimeError("Supabase client is not installed.")
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase integration.")


def get_supabase_admin_client() -> Client:
    global _supabase_admin_client_singleton
    if _supabase_admin_client_singleton is not None:
        return _supabase_admin_client_singleton

    _require_supabase_client()
    _supabase_admin_client_singleton = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase_admin_client_singleton


def get_supabase_auth_client() -> Client:
    global _supabase_auth_client_singleton
    if _supabase_auth_client_singleton is not None:
        return _supabase_auth_client_singleton

    _require_supabase_client()
    auth_key = settings.supabase_anon_key or settings.supabase_service_role_key
    if not auth_key:
        raise RuntimeError("SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY is required for auth integration.")

    _supabase_auth_client_singleton = create_client(settings.supabase_url, auth_key)
    return _supabase_auth_client_singleton


def get_storage() -> StorageAdapter:
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    if settings.storage_backend.lower() == "supabase":
        _storage_singleton = SupabaseStorage(get_supabase_admin_client())
        return _storage_singleton

    _storage_singleton = LocalJsonStorage(settings.local_storage_root)
    return _storage_singleton

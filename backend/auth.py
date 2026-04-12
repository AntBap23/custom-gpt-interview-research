from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status

from backend.errors import AuthenticationError, SupabaseOperationError
from backend.settings import settings
from backend.storage import get_supabase_admin_client, get_supabase_auth_client


@dataclass
class AuthContext:
    user_id: str
    email: str | None
    role: str | None
    access_token: str


def _extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip() or None


def _extract_access_token(request: Request) -> str | None:
    bearer = _extract_bearer_token(request)
    if bearer:
        return bearer
    return request.cookies.get(settings.auth_access_cookie_name)


def _extract_refresh_token(request: Request) -> str | None:
    return request.cookies.get(settings.auth_refresh_cookie_name)


def _read_user_role(user: Any) -> str | None:
    metadata = getattr(user, "user_metadata", None)
    if isinstance(metadata, dict) and metadata.get("role"):
        return str(metadata["role"])
    app_metadata = getattr(user, "app_metadata", None)
    if isinstance(app_metadata, dict) and app_metadata.get("role"):
        return str(app_metadata["role"])
    return None


def _profile_role_for_user(user_id: str) -> str | None:
    client = get_supabase_admin_client()
    try:
        response = client.table("profiles").select("role").eq("id", user_id).limit(1).execute()
    except Exception:
        return None
    rows = response.data or []
    if not rows:
        return None
    role = rows[0].get("role")
    return str(role) if role else None


def _resolve_auth_context_from_token(access_token: str) -> AuthContext:
    client = get_supabase_auth_client()
    try:
        user_response = client.auth.get_user(access_token)
    except Exception as exc:  # pragma: no cover - external call
        raise AuthenticationError("Unable to validate Supabase access token.") from exc

    user = getattr(user_response, "user", None)
    if not user:
        raise AuthenticationError("Supabase session is invalid.")

    user_id = str(getattr(user, "id", "") or "")
    if not user_id:
        raise AuthenticationError("Supabase user id is missing.")

    role = _profile_role_for_user(user_id) or _read_user_role(user)
    return AuthContext(
        user_id=user_id,
        email=getattr(user, "email", None),
        role=role,
        access_token=access_token,
    )


def get_auth_context_from_access_token(access_token: str) -> AuthContext:
    return _resolve_auth_context_from_token(access_token)


def get_optional_auth_context(request: Request) -> AuthContext | None:
    access_token = _extract_access_token(request)
    if not access_token:
        return None
    try:
        context = _resolve_auth_context_from_token(access_token)
    except AuthenticationError:
        refresh_token = _extract_refresh_token(request)
        if not refresh_token:
            return None
        # Refresh once, then re-validate the new access token.
        try:
            session_response = get_supabase_auth_client().auth.refresh_session(refresh_token)
            refreshed_access = getattr(session_response.session, "access_token", None) if session_response else None
            refreshed_refresh = getattr(session_response.session, "refresh_token", None) if session_response else None
        except Exception:
            return None
        if not refreshed_access:
            return None
        if refreshed_refresh:
            request.state.refreshed_access_token = str(refreshed_access)
            request.state.refreshed_refresh_token = str(refreshed_refresh)
        context = _resolve_auth_context_from_token(refreshed_access)
    request.state.auth = context
    return context


def require_authenticated_user(request: Request) -> AuthContext:
    context = get_optional_auth_context(request)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return context


def sign_in_with_password(email: str, password: str) -> tuple[str, str]:
    client = get_supabase_auth_client()
    try:
        auth_response = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:  # pragma: no cover - external call
        raise AuthenticationError("Sign in failed. Check your credentials.") from exc

    session = getattr(auth_response, "session", None)
    if not session or not getattr(session, "access_token", None) or not getattr(session, "refresh_token", None):
        raise AuthenticationError("Sign in did not return a valid session.")
    return str(session.access_token), str(session.refresh_token)


def sign_up_with_password(email: str, password: str) -> tuple[str | None, str | None, Any]:
    client = get_supabase_auth_client()
    try:
        auth_response = client.auth.sign_up({"email": email, "password": password})
    except Exception as exc:  # pragma: no cover - external call
        raise AuthenticationError("Sign up failed. Please verify the email/password and try again.") from exc

    user = getattr(auth_response, "user", None)
    if not user:
        raise AuthenticationError("Sign up did not return a valid user.")

    session = getattr(auth_response, "session", None)
    access_token = str(session.access_token) if session and getattr(session, "access_token", None) else None
    refresh_token = str(session.refresh_token) if session and getattr(session, "refresh_token", None) else None
    return access_token, refresh_token, user


def sign_out_with_token(access_token: str | None) -> None:
    if not access_token:
        return
    try:
        get_supabase_admin_client().auth.admin.sign_out(access_token)
    except Exception as exc:  # pragma: no cover - external call
        raise SupabaseOperationError("Supabase sign out failed.") from exc

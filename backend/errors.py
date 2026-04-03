class BackendError(Exception):
    """Base class for backend-level operational errors."""


class SupabaseOperationError(BackendError):
    """Raised when a Supabase call fails and should be sanitized for API callers."""

    def __init__(self, message: str = "A Supabase operation failed."):
        super().__init__(message)


class AuthenticationError(BackendError):
    """Raised when authentication/session validation fails."""

    def __init__(self, message: str = "Authentication failed."):
        super().__init__(message)

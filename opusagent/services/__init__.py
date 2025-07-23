"""Services package for high-level application services.

This package provides service layer implementations for managing
application state, sessions, and other cross-cutting concerns.
"""

from .session_manager_service import SessionManagerService

__all__ = ["SessionManagerService"] 
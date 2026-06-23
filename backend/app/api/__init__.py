"""finscan API routers."""

from .auth import router as auth_router
from .watchlist import router as watchlist_router
from .announcement import router as announcement_router

__all__ = [
    "auth_router", "watchlist_router", "announcement_router",
]

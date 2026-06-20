"""finscan API routers."""

from .v1 import router as v1_router
from .auth import router as auth_router
from .watchlist import router as watchlist_router
from .risk import router as risk_router
from .compare import router as compare_router
from .announcement import router as announcement_router
from .ai import router as ai_router

__all__ = [
    "v1_router", "auth_router", "watchlist_router",
    "risk_router", "compare_router", "announcement_router", "ai_router",
]
